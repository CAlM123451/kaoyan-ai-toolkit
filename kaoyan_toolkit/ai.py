"""LLM 集成：考点分析、错题复盘、计划生成。带缓存+重试。

支持两种后端：
1. DeepSeek 直连（默认，零额外依赖）—— DEEPSEEK_API_KEY
2. litellm 统一接口（MIT, https://github.com/BerriAI/litellm）
   —— 100+ 模型商统一调用，设置 LLM_MODEL 即自动启用，
      如 "deepseek/deepseek-chat"、"openai/gpt-4o-mini"、
      "openai/qwen3.5-4b"（本地 vLLM/NewAPI 兼容端点）等。
"""
import hashlib
import json
import os
import re

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .cache import AICache
from .prompt import PLAN_PROMPT, SUBJECT_ANALYSIS_PROMPT, WRONG_QUESTION_PROMPT

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
MODEL = os.getenv("LLM_MODEL", DEFAULT_MODEL)


def get_api_key() -> str | None:
    return os.getenv("DEEPSEEK_API_KEY")


def _stable_hash(text: str) -> str:
    """确定性哈希（Python 内置 hash() 每次启动不同，不适合做缓存键）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _truncate(text: str, max_chars: int) -> str:
    """按句子边界截断文本，避免从句子中间切断导致语义丢失。"""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # 在最后一个句末标点/换行处截断（至少保留 60% 内容）
    for ch in ("。", "？", "！", "\n", ".", "?", "!"):
        pos = cut.rfind(ch)
        if pos > max_chars * 0.6:
            return cut[:pos + 1]
    return cut


# 网络类异常才重试（超时/连接失败/HTTP错误可恢复），业务错误（如 key 无效）直接抛出
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10),
       retry=retry_if_exception_type(
           (requests.Timeout, requests.ConnectionError, requests.HTTPError)
       ))
def _call_llm(prompt: str, system: str = "你是一位严谨的考研辅导专家。",
              max_tokens: int = 1500) -> str:
    if MODEL != DEFAULT_MODEL:
        return _call_llm_litellm(prompt, system, max_tokens)
    return _call_llm_direct(prompt, system, max_tokens)


def _call_llm_direct(prompt: str, system: str, max_tokens: int) -> str:
    """DeepSeek 直连后端（requests 实现，无额外依赖）。"""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "未设置 DEEPSEEK_API_KEY 环境变量。\n"
            "请先设置：$env:DEEPSEEK_API_KEY = 'sk-你的key'（PowerShell）"
        )

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )
    except requests.Timeout:
        raise RuntimeError("DeepSeek API 请求超时，请检查网络后重试")
    except requests.ConnectionError:
        raise RuntimeError("无法连接 DeepSeek API，请检查网络/代理设置")

    if resp.status_code == 401:
        raise RuntimeError("API Key 无效或已过期，请检查 DEEPSEEK_API_KEY")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_llm_litellm(prompt: str, system: str, max_tokens: int) -> str:
    """litellm 统一接口后端（MIT 许可证，https://github.com/BerriAI/litellm）。

    通过设置 LLM_MODEL 启用，例如：
      export LLM_MODEL="deepseek/deepseek-chat"   # DeepSeek
      export LLM_MODEL="openai/gpt-4o-mini"       # OpenAI
      export LLM_MODEL="openai/qwen3.5-4b"        # 本地 vLLM/NewAPI
    API Key 按模型商前缀从环境变量读取（OPENAI_API_KEY 等），
    也支持 LLM_API_KEY 统一覆盖。
    """
    try:
        import litellm
    except ImportError:
        raise RuntimeError(
            "检测到 LLM_MODEL 但未安装 litellm，请执行: pip install litellm"
        )

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    try:
        resp = litellm.completion(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
            api_key=api_key,
        )
    except Exception as e:
        raise RuntimeError(f"litellm 调用失败（{MODEL}）：{e}")
    return resp.choices[0].message.content.strip()


def _with_cache(cache: AICache | None, key: str,
                producer) -> dict:
    """统一的缓存读写流程：命中直接返回，未命中调用 producer 并写缓存。"""
    if cache:
        cached = cache.get(key)
        if cached:
            return _parse_json(cached)
    result = producer()
    if cache:
        cache.set(key, result)
    return _parse_json(result)


def _parse_json(text: str) -> dict:
    """从 LLM 输出中稳健提取 JSON（处理 ```json 包裹、前后多余文字等情况）。"""
    t = text.strip()
    # 去掉 ```json ... ``` 包裹
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    # 尝试直接解析
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # 提取第一个 { ... } 或 [ ... ]
    for start_ch, end_ch in [("{", "}"), ("[", "]")]:
        start = t.find(start_ch)
        end = t.rfind(end_ch)
        if start != -1 and end > start:
            try:
                return json.loads(t[start:end + 1])
            except json.JSONDecodeError:
                continue
    return {"raw": text}


def analyze_subjects(text: str, cache: AICache | None = None,
                     max_chars: int = 8000) -> dict:
    """AI 考点分析（文本超长时按句子边界截断）。"""
    truncated = _truncate(text, max_chars)
    key = "subj:" + _stable_hash(truncated)
    return _with_cache(cache, key, lambda: _call_llm(
        SUBJECT_ANALYSIS_PROMPT.format(text=truncated), max_tokens=2000))


def review_wrong_question(text: str, cache: AICache | None = None,
                          max_chars: int = 4000) -> dict:
    """AI 错题复盘。"""
    truncated = _truncate(text, max_chars)
    key = "review:" + _stable_hash(truncated)
    return _with_cache(cache, key, lambda: _call_llm(
        WRONG_QUESTION_PROMPT.format(text=truncated), max_tokens=1500))


def generate_plan(exam_date: str, daily_hours: float, priority: str,
                  cache: AICache | None = None) -> dict:
    """AI 复习计划生成。"""
    key = f"plan:{exam_date}:{daily_hours}:{_stable_hash(priority)}"
    return _with_cache(cache, key, lambda: _call_llm(
        PLAN_PROMPT.format(
            exam_date=exam_date, daily_hours=daily_hours, priority=priority
        ),
        max_tokens=2000,
    ))

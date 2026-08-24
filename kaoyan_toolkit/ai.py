"""DeepSeek 集成：考点分析、错题复盘、计划生成。带缓存+重试。"""
import hashlib
import json
import os
import re

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .cache import AICache
from .prompt import PLAN_PROMPT, SUBJECT_ANALYSIS_PROMPT, WRONG_QUESTION_PROMPT

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def get_api_key() -> str | None:
    return os.getenv("DEEPSEEK_API_KEY")


def _stable_hash(text: str) -> str:
    """确定性哈希（Python 内置 hash() 每次启动不同，不适合做缓存键）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def _call_llm(prompt: str, system: str = "你是一位严谨的考研辅导专家。",
              max_tokens: int = 1500) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "未设置 DEEPSEEK_API_KEY 环境变量。\n"
            "请先设置：$env:DEEPSEEK_API_KEY = 'sk-你的key'（PowerShell）"
        )

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
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


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
    """AI 考点分析（文本超长时截断）。"""
    truncated = text[:max_chars]
    key = "subj:" + _stable_hash(truncated)
    if cache:
        cached = cache.get(key)
        if cached:
            return _parse_json(cached)
    prompt = SUBJECT_ANALYSIS_PROMPT.format(text=truncated)
    result = _call_llm(prompt, max_tokens=2000)
    if cache:
        cache.set(key, result)
    return _parse_json(result)


def review_wrong_question(text: str, cache: AICache | None = None,
                          max_chars: int = 4000) -> dict:
    """AI 错题复盘。"""
    truncated = text[:max_chars]
    key = "review:" + _stable_hash(truncated)
    if cache:
        cached = cache.get(key)
        if cached:
            return _parse_json(cached)
    prompt = WRONG_QUESTION_PROMPT.format(text=truncated)
    result = _call_llm(prompt, max_tokens=1500)
    if cache:
        cache.set(key, result)
    return _parse_json(result)


def generate_plan(exam_date: str, daily_hours: float, priority: str,
                  cache: AICache | None = None) -> dict:
    """AI 复习计划生成。"""
    key = f"plan:{exam_date}:{daily_hours}:{_stable_hash(priority)}"
    if cache:
        cached = cache.get(key)
        if cached:
            return _parse_json(cached)
    prompt = PLAN_PROMPT.format(
        exam_date=exam_date, daily_hours=daily_hours, priority=priority
    )
    result = _call_llm(prompt, max_tokens=2000)
    if cache:
        cache.set(key, result)
    return _parse_json(result)

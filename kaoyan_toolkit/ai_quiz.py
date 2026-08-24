"""AI 阅读出题：基于真题风格生成同源阅读理解选择题（带缓存）。

输入一段阅读材料，DeepSeek 生成 N 道四选一选择题（含答案与解析）。
"""
from .ai import _with_cache, _stable_hash

QUIZ_PROMPT = """你是考研英语阅读命题老师。请基于下面的阅读材料，命制 {n} 道考研英语风格的四选一阅读理解题。

命题要求：
- 题型覆盖：细节题、主旨题、推理题、词义题、态度题
- 选项难度递进，干扰项要"像正确答案"（偷换概念/以偏概全/无中生有）
- 答案唯一，解析必须说明正确项依据与干扰项错因

输出 JSON（不要多余文字）：
{{
  "questions": [
    {{"stem": "题干", "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
     "answer": "A/B/C/D", "explanation": "解析（含正确项依据+错误项错因）",
     "type": "细节/主旨/推理/词义/态度"}}
  ]
}}

阅读材料：
---
{text}
"""


def generate_quiz(text: str, n: int = 3, cache=None, max_chars: int = 6000) -> dict:
    """生成阅读理解题，返回 {"questions": [...]}；失败返回空 dict。"""
    from .ai import _call_llm, _truncate
    truncated = _truncate(text[:max_chars], max_chars)
    key = f"quiz:{_stable_hash(truncated)}:{n}"
    result = _with_cache(
        cache, key, lambda: _call_llm(
            QUIZ_PROMPT.format(text=truncated, n=n), max_tokens=2500,
            system="你是资深的考研英语命题专家，熟悉历年真题风格。",
        )
    )
    if not isinstance(result, dict) or not result.get("questions"):
        return {}
    return result


def format_quiz_markdown(quiz: dict) -> str:
    """把题目 dict 格式化为练习用 Markdown。"""
    questions = quiz.get("questions", [])
    if not questions:
        return "AI 未能生成题目（请检查 API Key 或稍后重试）"
    out = ["# 阅读模拟练习", ""]
    for i, q in enumerate(questions, 1):
        out.append(f"### 第 {i} 题（{q.get('type', '阅读')}）")
        out.append(q.get("stem", ""))
        out.append("")
        for opt in q.get("options", []):
            out.append(f"- {opt}")
        out.append("")
        out.append(f"<details><summary>查看答案与解析</summary>")
        out.append("")
        out.append(f"**答案：{q.get('answer', '?')}**")
        out.append("")
        out.append(q.get("explanation", ""))
        out.append("</details>")
        out.append("")
    out.append("> 由 DeepSeek AI 基于你的资料生成，仅供参考练习。")
    return "\n".join(out)
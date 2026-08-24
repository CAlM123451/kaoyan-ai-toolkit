"""考频统计：确定性本地算法（不依赖 AI），输出科目分布与高频考点。"""

from .extract import detect_subjects, extract_keywords


def analyze_text(text: str, top_keywords: int = 30) -> dict:
    """对一段真题/资料文本做本地统计分析。

    返回:
    {
      "subject_distribution": {科目: 命中次数},
      "top_keywords": [(词, 次数)],
      "total_length": 字符数,
    }
    """
    subject_dist = detect_subjects(text)
    kw_pairs = extract_keywords(text, top=top_keywords)

    return {
        "subject_distribution": subject_dist,
        "top_keywords": kw_pairs,
        "total_length": len(text),
    }

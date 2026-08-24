"""考频统计：确定性本地算法（不依赖 AI），输出科目分布与高频考点。"""
from collections import Counter

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
    keywords = extract_keywords(text, top=top_keywords)

    # 转成 [(word, count)]
    kw_pairs = []
    try:
        import re
        from collections import Counter
        stop = {
            "的", "了", "是", "在", "和", "与", "及", "或", "对", "为", "中",
            "等", "并", "不", "一", "有", "可", "能", "而", "其", "于", "者",
        }
        import jieba
        counter = Counter(
            w for w in jieba.lcut(text)
            if len(w) >= 2 and w not in stop and not re.fullmatch(r"[\d\W]+", w)
        )
        kw_pairs = counter.most_common(top_keywords)
    except Exception:
        pass

    return {
        "subject_distribution": subject_dist,
        "top_keywords": kw_pairs,
        "total_length": len(text),
    }

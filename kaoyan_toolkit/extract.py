"""考点关键词提取：本地规则 + jieba 分词，把文本按西综科目归类。"""

# 西综六大科目及其关键词（可扩充）
SUBJECT_KEYWORDS = {
    "生理学": ["生理", "细胞", "神经", "血液", "循环", "呼吸", "消化", "泌尿",
               "体温", "内分泌", "感觉器官", "肾小球", "心肌", "肺泡"],
    "内科学": ["内科", "肺炎", "心衰", "冠心病", "高血压", "糖尿病", "肝硬化",
               "肾病", "贫血", "甲亢", "痛风", "COPD", "哮喘"],
    "病理学": ["病理", "炎症", "肿瘤", "坏死", "增生", "癌", "梗死", "纤维化",
               "水肿", "血栓"],
    "外科学": ["外科", "手术", "骨折", "感染", "休克", "烧伤", "麻醉", "阑尾炎",
               "胆道", "疝", "肿瘤切除"],
    "生物化学": ["生化", "酶", "糖代谢", "脂质", "蛋白质", "核酸", "ATP",
                "三羧酸", "糖酵解", "氧化磷酸化"],
    "医学人文": ["医患", "伦理", "知情同意", "医疗纠纷", "人文", "沟通",
                "执业医师", "法律法规"],
}

# 常见题型标记
QUESTION_MARKERS = ["A型", "B型", "X型", "单选", "多选", "病例分析"]


def detect_subjects(text: str) -> dict[str, int]:
    """统计文本中各科目关键词命中次数。"""
    scores = {}
    for subject, kws in SUBJECT_KEYWORDS.items():
        hit = sum(1 for kw in kws if kw in text)
        if hit:
            scores[subject] = hit
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def extract_keywords(text: str, top: int = 20) -> list[str]:
    """用 jieba 提取文本中的医学高频词。"""
    try:
        import jieba
    except ImportError:
        raise RuntimeError("需要安装 jieba: pip install jieba")

    import re
    from collections import Counter

    stop = {
        "的", "了", "是", "在", "和", "与", "及", "或", "对", "为", "中",
        "等", "并", "不", "一", "有", "可", "能", "而", "其", "于", "者",
        "问题", "下列", "关于", "正确", "错误", "哪项", "下列哪项", "最",
    }
    words = jieba.lcut(text)
    counter = Counter(
        w for w in words
        if len(w) >= 2 and w not in stop and not re.fullmatch(r"[\d\W]+", w)
    )
    return [w for w, _ in counter.most_common(top)]

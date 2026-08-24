"""考点关键词提取：本地规则 + 中文分词（jieba 默认 / pkuseg 可选增强）。

分词后端：
- jieba（默认，零额外依赖）
- pkuseg 医学领域模型（可选，MIT, https://github.com/lancopku/pkuseg-python）
  医学分词准确率更高，设置 USE_PKUSEG=1 启用
"""
import re
from collections import Counter

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

# 中文停用词
_STOP_WORDS = {
    "的", "了", "是", "在", "和", "与", "及", "或", "对", "为", "中",
    "等", "并", "不", "一", "有", "可", "能", "而", "其", "于", "者",
    "问题", "下列", "关于", "正确", "错误", "哪项", "下列哪项", "最",
    "以下", "属于", "不是", "主要", "常见", "相关", "可能",
}


def detect_subjects(text: str) -> dict[str, int]:
    """统计文本中各科目关键词命中次数。"""
    if not text:
        return {}
    scores = {}
    for subject, kws in SUBJECT_KEYWORDS.items():
        hit = sum(text.count(kw) for kw in kws)
        if hit:
            scores[subject] = hit
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def _segment(text: str) -> list[str]:
    """中文分词：默认 jieba；USE_PKUSEG=1 时用 pkuseg 医学领域模型。"""
    import os

    if os.getenv("USE_PKUSEG") == "1":
        try:
            import pkuseg
            # pkuseg 内置 medicine 领域模型（MIT 许可证）
            seg = pkuseg.pkuseg(model_name="medicine")
            return seg.cut(text)
        except ImportError:
            raise RuntimeError(
                "设置了 USE_PKUSEG=1 但未安装 pkuseg，请执行: pip install pkuseg"
            )

    try:
        import jieba
    except ImportError:
        raise RuntimeError("需要安装 jieba: pip install jieba")
    return jieba.lcut(text)


def extract_keywords(text: str, top: int = 20) -> list[tuple[str, int]]:
    """提取文本中的医学高频词（jieba 或 pkuseg），返回 [(词, 次数)]。"""
    words = _segment(text)
    counter = Counter(
        w for w in words
        if len(w) >= 2 and w not in _STOP_WORDS and not re.fullmatch(r"[\d\W]+", w)
    )
    return counter.most_common(top)

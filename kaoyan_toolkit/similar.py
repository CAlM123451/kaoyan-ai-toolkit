"""相似题检索：BM25 算法在本地真题语料中检索最相似题目。

rank_bm25（Apache 2.0, https://github.com/dorianbrown/rank_bm25）
将语料划分为"题目块"（按题号/选项标记切分），
输入任意题目/关键词即可离线检索 Top-N 相似题目。
"""
import re

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

# 题号切分标记：数字 + 点/顿号/右括号 + 空白（行内/行首均可）。
# 要求标点后必须是空白或行尾，避免把 "45岁"、"(16.8)"、"V1-V4" 等误判为题号。
_QUESTION_SPLIT = re.compile(
    r"(?<!\d)(\d{1,3})\s*[\.、．)）]\s+"
    r"|[（(]\d{1,3}[)）]\s*"
    r"|A型题|B型题|X型题|病例分析"
)


def split_questions(text: str, min_len: int = 20) -> list[str]:
    """把真题文本按题号切分为题目块列表。

    支持常见题号格式："1. "、"2、"、"3）"、"(4) "、"A型题" 等；
    按行优先，行内再按题号分割。
    """
    parts = []
    for line in text.splitlines():
        line = (line or "").strip()
        if not line:
            continue
        # 找出该行所有题号起点，切分行
        bounds = [0]
        for m in _QUESTION_SPLIT.finditer(line):
            if m.start() > 0:
                bounds.append(m.start())
        bounds.append(len(line))
        for i in range(len(bounds) - 1):
            seg = line[bounds[i]:bounds[i + 1]].strip()
            if seg:
                parts.append(seg)
    return [p for p in parts if len(p) >= min_len]


def _tokenize(questions: list[str]) -> list[list[str]]:
    """中文分词 + 英文小写分词（复用 jieba，保持与 extract 一致）。"""
    from .extract import _segment

    tokenized = []
    for q in questions:
        tokens = []
        for seg in _segment(q):
            tokens.append(seg.lower())
        # 补充英文单词切分
        tokens += [w.lower() for w in re.findall(r"[A-Za-z]{2,}", q)]
        tokens = [t for t in tokens if len(t) >= 2]
        tokenized.append(tokens)
    return tokenized


class SimilarSearcher:
    """基于 BM25 的本地相似题检索器。"""

    def __init__(self, corpus_text: str, min_len: int = 20):
        if BM25Okapi is None:
            raise RuntimeError(
                "相似题检索需要安装 rank_bm25: pip install rank_bm25"
            )
        self.questions = split_questions(corpus_text, min_len)
        if not self.questions:
            raise ValueError("语料中未识别到题目块（需要至少 20 字的内容）")
        self._tokenized = _tokenize(self.questions)
        self._bm25 = BM25Okapi(self._tokenized)

    def search(self, query: str, top: int = 5) -> list[dict]:
        """检索与 query 最相似的题目，返回 [{index, score, snippet}]。"""
        q_tokens = _tokenize([query])[0]
        if not q_tokens:
            return []
        scores = self._bm25.get_scores(q_tokens)
        ranked = sorted(
            ((i, float(s)) for i, s in enumerate(scores) if s > 0),
            key=lambda x: -x[1],
        )[:top]
        results = []
        for idx, score in ranked:
            snippet = self.questions[idx]
            results.append({
                "index": idx,
                "score": round(score, 2),
                "snippet": snippet[:120] + ("…" if len(snippet) > 120 else ""),
            })
        return results


def format_search_results(results: list[dict]) -> str:
    """检索结果 → Markdown 文本。"""
    if not results:
        return "未检索到相似题目。"
    lines = ["## 相似题检索（BM25 本地算法）", ""]
    for r in results:
        lines.append(f"- 相似度 {r['score']:.2f}：{r['snippet']}")
    lines.append("")
    lines.append("> 检索基于本地语料离线完成，无网络请求。")
    return "\n".join(lines)
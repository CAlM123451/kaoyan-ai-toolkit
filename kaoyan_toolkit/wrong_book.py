"""错题本：JSON 存储的错题 CRUD + AI 复盘 + 周期回顾。

每道错题字段:
    id, question(题干), my_answer, correct_answer, analysis,
    subject, source, tags [], created_at, reviewed_at, wrong_count
"""
import json
import os
import time


class WrongBook:
    """基于 JSON 文件的错题本。"""

    def __init__(self, path: str):
        self.path = path
        self._items: list[dict] = []

    def load(self) -> "WrongBook":
        if os.path.isfile(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                self._items = data if isinstance(data, list) else []
            except (OSError, json.JSONDecodeError):
                self._items = []
        return self

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)) or ".",
                    exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)

    # ---------- CRUD ----------
    def add(self, question: str, my_answer: str = "", correct_answer: str = "",
            analysis: str = "", subject: str = "", source: str = "",
            tags: list[str] | None = None) -> dict:
        """新增错题，返回记录。"""
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        it = {
            "id": (self._items[-1]["id"] + 1) if self._items else 1,
            "question": question.strip(),
            "my_answer": my_answer.strip(),
            "correct_answer": correct_answer.strip(),
            "analysis": analysis.strip(),
            "subject": subject.strip(),
            "source": source.strip(),
            "tags": tags or [],
            "created_at": now,
            "reviewed_at": None,
            "wrong_count": 1,
        }
        self._items.append(it)
        self.save()
        return it

    def remove(self, item_id: int) -> bool:
        before = len(self._items)
        self._items = [it for it in self._items if it["id"] != item_id]
        if len(self._items) != before:
            self.save()
            return True
        return False

    def update(self, item_id: int, **fields) -> dict | None:
        """更新字段（question/my_answer/.../wrong_count 等）。"""
        for it in self._items:
            if it["id"] == item_id:
                it.update({k: v for k, v in fields.items() if v is not None})
                self.save()
                return it
        return None

    def mark_reviewed(self, item_id: int) -> dict | None:
        """标记一次复习（用 AI 复盘后调用）。"""
        return self.update(
            item_id,
            reviewed_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def list_items(self, subject: str = "", keyword: str = "",
                   only_unreviewed: bool = False) -> list[dict]:
        """按条件筛选：科目 / 关键词 / 仅未复盘。"""
        out = []
        for it in self._items:
            if subject and it.get("subject") != subject:
                continue
            if keyword and keyword.lower() not in (
                    it.get("question", "") + it.get("analysis", "")).lower():
                continue
            if only_unreviewed and it.get("reviewed_at"):
                continue
            out.append(it)
        return out

    def stats(self) -> dict:
        """错题统计：总数/未复盘/按科目分布/反复错题（>2次）。"""
        total = len(self._items)
        unreviewed = sum(1 for it in self._items if not it.get("reviewed_at"))
        repeated = [it for it in self._items if it.get("wrong_count", 1) >= 3]
        subjects: dict[str, int] = {}
        for it in self._items:
            s = it.get("subject") or "未分类"
            subjects[s] = subjects.get(s, 0) + 1
        return {
            "total": total,
            "unreviewed": unreviewed,
            "repeated_count": len(repeated),
            "repeated": repeated,
            "subjects": dict(sorted(subjects.items(), key=lambda x: -x[1])),
        }


def format_wrong_book(items: list[dict]) -> str:
    """把错题列表格式化为 Markdown（供导出/回顾）。"""
    if not items:
        return "# 错题本\n\n暂无错题记录。\n"
    out = ["# 错题本", ""]
    for it in items:
        out.append(f"## {it['id']}. {it.get('question', '')[:100]}")
        meta = []
        if it.get("subject"):
            meta.append(it["subject"])
        if it.get("source"):
            meta.append(it["source"])
        if it.get("tags"):
            meta.append("、".join(it["tags"]))
        if it.get("wrong_count", 1) > 1:
            meta.append(f"错 {it['wrong_count']} 次")
        if meta:
            out.append(f"> {' · '.join(meta)}")
        out.append("")
        if it.get("my_answer"):
            out.append(f"- 我的答案: {it['my_answer']}")
        if it.get("correct_answer"):
            out.append(f"- 正确答案: {it['correct_answer']}")
        if it.get("analysis"):
            out.append(f"- 解析: {it['analysis']}")
        if it.get("reviewed_at"):
            out.append(f"- 已复盘: {it['reviewed_at']}")
        else:
            out.append("- ⚠️ 待 AI 复盘")
        out.append("")
    return "\n".join(out)
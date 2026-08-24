"""SQLite 缓存：避免重复调用 DeepSeek API（省钱关键）。"""
import os
import sqlite3


class AICache:
    """基于 SQLite 的 AI 调用结果缓存。"""

    def __init__(self, db_path: str = "cache.sqlite"):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS ai_cache (
                       key TEXT PRIMARY KEY, result TEXT,
                       created_at TEXT DEFAULT (datetime('now'))
                   )"""
            )

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def get(self, key: str) -> str | None:
        try:
            with self._conn() as c:
                row = c.execute(
                    "SELECT result FROM ai_cache WHERE key=?", (key,)
                ).fetchone()
            return row[0] if row else None
        except sqlite3.Error:
            return None

    def set(self, key: str, result: str):
        try:
            with self._conn() as c:
                c.execute(
                    "INSERT OR REPLACE INTO ai_cache (key, result) VALUES (?,?)",
                    (key, result),
                )
        except sqlite3.Error:
            pass

    def clear(self):
        """清空全部缓存。"""
        try:
            with self._conn() as c:
                c.execute("DELETE FROM ai_cache")
        except sqlite3.Error:
            pass

    @property
    def size(self) -> int:
        """返回缓存条目数。"""
        try:
            with self._conn() as c:
                return c.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0]
        except sqlite3.Error:
            return 0

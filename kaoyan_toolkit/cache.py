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

    def stats(self) -> dict:
        """返回缓存统计信息：条目数、最早/最新写入时间、库文件大小。"""
        info = {"entries": 0, "oldest": None, "newest": None, "db_size_kb": 0.0}
        try:
            with self._conn() as c:
                info["entries"] = c.execute(
                    "SELECT COUNT(*) FROM ai_cache"
                ).fetchone()[0]
                row = c.execute(
                    "SELECT MIN(created_at), MAX(created_at) FROM ai_cache"
                ).fetchone()
            info["oldest"], info["newest"] = row
        except sqlite3.Error:
            return info
        try:
            # 主库 + WAL 日志合计大小
            size = 0.0
            for suffix in ("", "-wal", "-shm"):
                p = self.db_path + suffix
                if os.path.isfile(p):
                    size += os.path.getsize(p)
            info["db_size_kb"] = round(size / 1024, 1)
        except OSError:
            pass
        return info

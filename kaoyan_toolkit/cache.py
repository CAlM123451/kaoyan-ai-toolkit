"""SQLite 缓存：避免重复调用 DeepSeek API（省钱关键）。"""
import os
import sqlite3


class AICache:
    def __init__(self, db_path: str = "cache.sqlite"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS ai_cache (
                       key TEXT PRIMARY KEY, result TEXT
                   )"""
            )

    def _conn(self):
        return sqlite3.connect(self.db_path)

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
                    "INSERT OR REPLACE INTO ai_cache VALUES (?,?)",
                    (key, result),
                )
        except sqlite3.Error:
            pass

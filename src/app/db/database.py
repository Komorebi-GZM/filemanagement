from __future__ import annotations

import sqlite3


class DbError(RuntimeError):
    pass


class Database:
    def __init__(self, path: str):
        self._path = path

    def connect(self):
        # 暂时跳过创建目录的步骤，直接尝试连接数据库
        try:
            conn = sqlite3.connect(self._path)
        except sqlite3.Error as e:
            raise DbError(f"无法打开数据库: {self._path}: {e}") from e

        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def count_all_files(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM files WHERE is_deleted = 0").fetchone()
            return row[0] if row else 0

    def count_files_by_tag(self, tag_id: int) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM file_tag_relation ftr
                JOIN files f ON f.id = ftr.file_id
                WHERE ftr.tag_id = ? AND f.is_deleted = 0
                """,
                (tag_id,),
            ).fetchone()
            return row[0] if row else 0



def apply_schema(conn: sqlite3.Connection, schema_sql: str) -> None:
    try:
        conn.executescript(schema_sql)
    except sqlite3.Error as e:
        raise DbError(f"初始化数据库 schema 失败: {e}") from e


def load_schema_text(schema_file):
    try:
        return schema_file.read_text(encoding="utf-8")
    except OSError as e:
        raise DbError(f"无法读取 schema 文件: {schema_file}: {e}") from e

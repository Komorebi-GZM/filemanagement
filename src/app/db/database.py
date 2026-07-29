from __future__ import annotations

import sqlite3
import time
from typing import Optional


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

    def find_by_hash(self, file_hash: str) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, file_name, full_path FROM files
                WHERE file_hash = ? AND is_deleted = 0
                """,
                (file_hash,),
            ).fetchone()
        return dict(row) if row else None

    def find_by_path_and_size(self, full_path: str, file_size: int) -> Optional[int]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM files
                WHERE full_path = ? AND file_size = ? AND is_deleted = 0
                LIMIT 1
                """,
                (full_path, file_size),
            ).fetchone()
        return row["id"] if row else None

    def update_file_path(self, file_id: int, new_path: str, new_name: str, new_ext: str) -> None:
        now = int(time.time())
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE files
                SET full_path = ?, file_name = ?, file_ext = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_path, new_name, new_ext, now, file_id),
            )
            conn.commit()

    def soft_delete_by_hash(self, file_hash: str) -> None:
        now = int(time.time())
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE files
                SET is_deleted = 1, deleted_at = ?, updated_at = ?
                WHERE file_hash = ? AND is_deleted = 0
                """,
                (now, now, file_hash),
            )
            conn.commit()

    def update_file_meta(self, file_id: int, file_size: int, modify_time: int) -> None:
        now = int(time.time())
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE files
                SET file_size = ?, modify_time = ?, updated_at = ?
                WHERE id = ?
                """,
                (file_size, modify_time, now, file_id),
            )
            conn.commit()

    def record_search(self, query_json: str, timestamp: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO search_history (query_json, created_at) VALUES (?, ?)",
                (query_json, timestamp),
            )
            conn.commit()

    def get_recent_searches(self, limit: int = 10) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, query_json, created_at
                FROM search_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_old_searches(self, max_keep: int = 50) -> None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM search_history
                ORDER BY created_at DESC
                LIMIT 1 OFFSET ?
                """,
                (max_keep,),
            ).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM search_history WHERE id <= ?",
                    (row["id"],),
                )
                conn.commit()



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

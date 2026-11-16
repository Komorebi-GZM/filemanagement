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
        from src.app.core.path_utils import normalize_path
        norm_path = normalize_path(full_path)
        with self.connect() as conn:
            # 阶段一：快路径（利用 idx_files_full_path 索引进行精确 NFC 匹配）
            row = conn.execute(
                """
                SELECT id FROM files
                WHERE full_path = ? AND file_size = ? AND is_deleted = 0
                LIMIT 1
                """,
                (norm_path, file_size),
            ).fetchone()
            if row:
                return row["id"]

            # 阶段二：大小写不敏感兜底匹配（带 LIMIT 10 并使用 Python casefold 校验）
            rows = conn.execute(
                """
                SELECT id, full_path FROM files
                WHERE full_path = ? COLLATE NOCASE AND file_size = ? AND is_deleted = 0
                LIMIT 10
                """,
                (norm_path, file_size),
            ).fetchall()
            norm_cf = norm_path.casefold()
            for r in rows:
                if normalize_path(r["full_path"]).casefold() == norm_cf:
                    return r["id"]
        return None

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

    def create_fts_table(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5(
                file_id UNINDEXED,
                content,
                tokenize='unicode61'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_content_status (
                file_id INTEGER PRIMARY KEY,
                content_length INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                indexed_at INTEGER,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)

    def upsert_fts(self, conn: sqlite3.Connection, file_id: int, file_name: str, content: str) -> None:
        fts_content = f"{file_name} {content}"
        conn.execute("DELETE FROM file_fts WHERE file_id = ?", (file_id,))
        conn.execute(
            "INSERT INTO file_fts (file_id, content) VALUES (?, ?)",
            (file_id, fts_content),
        )
        conn.execute(
            """INSERT INTO file_content_status (file_id, content_length, status, indexed_at)
               VALUES (?, ?, 'indexed', ?)
               ON CONFLICT(file_id) DO UPDATE SET
                   content_length = excluded.content_length,
                   status = 'indexed',
                   error_message = NULL,
                   indexed_at = excluded.indexed_at""",
            (file_id, len(fts_content), int(time.time())),
        )

    def delete_fts(self, conn: sqlite3.Connection, file_id: int) -> None:
        conn.execute("DELETE FROM file_fts WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM file_content_status WHERE file_id = ?", (file_id,))

    def search_fts(self, conn: sqlite3.Connection, query: str, limit: int = 200) -> list[dict]:
        rows = conn.execute(
            """SELECT f.id AS file_id, f.file_name, f.full_path, f.file_ext,
                      f.file_size, f.modify_time, f.file_hash, f.create_time,
                      f.created_at, f.updated_at, f.is_deleted, f.deleted_at, rank
               FROM file_fts fts
               JOIN files f ON f.id = fts.file_id
               WHERE f.is_deleted = 0 AND file_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_file_content_status(self, conn: sqlite3.Connection, file_id: int) -> Optional[dict]:
        row = conn.execute(
            "SELECT * FROM file_content_status WHERE file_id = ?", (file_id,)
        ).fetchone()
        return dict(row) if row else None

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
                ORDER BY created_at DESC, id DESC
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

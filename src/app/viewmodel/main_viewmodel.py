from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from src.app.db.database import Database, DbError
from src.app.services.file_monitor import FileEvent
from src.app.model.file_record import FileRecord
from src.app.model.tag import Tag
from src.app.viewmodel.signals import MainSignals

logger = logging.getLogger(__name__)


class FileReadError(RuntimeError):
    """
    文件读取错误异常类
    当读取文件失败时抛出此异常
    """
    pass


@dataclass(frozen=True)
class ImportCandidate:
    """
    导入候选文件数据类
    用于存储待导入文件的路径和大小信息
    """
    path: Path
    size: int


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    计算文件的SHA256哈希值
    
    Args:
        path: 文件路径
        chunk_size: 分块读取的大小，默认1MB
        
    Returns:
        文件的SHA256哈希值（十六进制字符串）
        
    Raises:
        FileReadError: 当文件读取失败时
    """
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
    except OSError as e:
        raise FileReadError(f"读取文件失败: {path}: {e}") from e
    return h.hexdigest()


class MainViewModel:
    """
    主视图模型类
    负责处理核心业务逻辑，包括文件管理、标记管理、搜索等功能
    """
    def __init__(self, db: Optional[Database] = None, signals: Optional[MainSignals] = None) -> None:
        """
        初始化主视图模型
        
        Args:
            db: 数据库连接对象
            signals: 信号对象，用于UI更新
        """
        self._db = db
        self.signals = signals
        self._auto_import = False
        self._index_worker = None

    @property
    def db(self) -> Optional[Database]:
        return self._db

    @db.setter
    def db(self, value: Optional[Database]) -> None:
        self._db = value

    def list_files(self, limit: int = 200, tag_id: Optional[int] = None, sort_by: str = "name", 
                   sort_order: str = "asc", file_ext: Optional[str] = None, 
                   drive_letter: Optional[str] = None) -> list[FileRecord]:
        """
        列出文件记录，支持多种筛选和排序条件
        
        Args:
            limit: 返回结果的最大数量
            tag_id: 按标记筛选，None表示不筛选
            sort_by: 排序字段，支持 "name"（文件名）
            sort_order: 排序顺序，"asc" 升序，"desc" 降序
            file_ext: 按文件扩展名筛选，None表示不筛选
            drive_letter: 按磁盘盘符筛选（如 "C:"），None表示不筛选
            
        Returns:
            符合条件的文件记录列表
        """
        with self._db.connect() as conn:
            query = """
                SELECT DISTINCT f.id, f.file_name, f.file_ext, f.full_path, f.file_size, 
                       f.create_time, f.modify_time, f.file_hash, f.is_deleted, 
                       f.deleted_at, f.created_at, f.updated_at
                FROM files f
            """
            params = []
            conditions = ["f.is_deleted = 0"]
            
            if tag_id is not None:
                query += " JOIN file_tag_relation ftr ON f.id = ftr.file_id"
                conditions.append("ftr.tag_id = ?")
                params.append(tag_id)
            
            if file_ext is not None:
                conditions.append("f.file_ext = ?")
                params.append(file_ext)
            
            if drive_letter is not None:
                conditions.append("f.full_path LIKE ?")
                params.append(f"{drive_letter}%")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            sort_column = "file_name"
            if sort_by == "name":
                sort_column = "file_name"
            
            order = "ASC" if sort_order == "asc" else "DESC"
            query += f" ORDER BY f.{sort_column} {order}"
            query += " LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
        
        return [
            FileRecord(
                id=r["id"],
                file_name=r["file_name"],
                full_path=r["full_path"],
                file_hash=r["file_hash"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                file_ext=r["file_ext"],
                file_size=r["file_size"],
                create_time=r["create_time"],
                modify_time=r["modify_time"],
                is_deleted=bool(r["is_deleted"]),
                deleted_at=r["deleted_at"],
            )
            for r in rows
        ]
    
    def get_all_file_extensions(self) -> list[str]:
        """
        获取系统中所有文件的扩展名
        
        Returns:
            扩展名列表（去重）
        """
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT file_ext
                FROM files
                WHERE is_deleted = 0 AND file_ext IS NOT NULL
                ORDER BY file_ext
                """
            ).fetchall()
        return [r["file_ext"] for r in rows]
    
    def get_all_drive_letters(self) -> list[str]:
        """
        获取系统中所有文件所在的磁盘盘符
        
        Returns:
            磁盘盘符列表（如 ["C:", "D:"]）
        """
        import string
        from pathlib import Path
        
        drives = set()
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT full_path
                FROM files
                WHERE is_deleted = 0
                """
            ).fetchall()
        
        for r in rows:
            path = Path(r["full_path"])
            if path.drive:
                drives.add(path.drive)
        
        return sorted(drives)

    def search_files(self, query: str = "", limit: int = 200) -> list[FileRecord]:
        with self._db.connect() as conn:
            if not query:
                return self.list_files(limit)

            fts_results = []
            try:
                fts_rows = self._db.search_fts(conn, query, limit)
                fts_results = [
                    FileRecord(
                        id=r["file_id"],
                        file_name=r["file_name"],
                        full_path=r["full_path"],
                        file_hash=r.get("file_hash", ""),
                        created_at=r.get("created_at", 0),
                        updated_at=r.get("updated_at", 0),
                        file_ext=r["file_ext"],
                        file_size=r["file_size"],
                        create_time=r.get("create_time", r.get("modify_time", 0)),
                        modify_time=r["modify_time"],
                        is_deleted=bool(r.get("is_deleted", 0)),
                        deleted_at=r.get("deleted_at"),
                    )
                    for r in fts_rows
                ]
            except Exception:
                logger.exception("FTS search failed for query: %s", query)

            fts_ids = {r.id for r in fts_results}
            remaining = limit - len(fts_results)

            like_results = []
            if remaining > 0:
                search_pattern = f"%{query}%"
                if fts_ids:
                    placeholders = ",".join("?" * len(fts_ids))
                    rows = conn.execute(
                        f"""SELECT id, file_name, file_ext, full_path, file_size,
                                   create_time, modify_time, file_hash, is_deleted,
                                   deleted_at, created_at, updated_at
                            FROM files
                            WHERE is_deleted = 0
                              AND (file_name LIKE ? OR file_ext LIKE ?)
                              AND id NOT IN ({placeholders})
                            ORDER BY file_name ASC
                            LIMIT ?""",
                        (search_pattern, search_pattern, *list(fts_ids), remaining),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT id, file_name, file_ext, full_path, file_size,
                                  create_time, modify_time, file_hash, is_deleted,
                                  deleted_at, created_at, updated_at
                           FROM files
                           WHERE is_deleted = 0
                             AND (file_name LIKE ? OR file_ext LIKE ?)
                           ORDER BY file_name ASC
                           LIMIT ?""",
                        (search_pattern, search_pattern, remaining),
                    ).fetchall()
                like_results = [
                    FileRecord(
                        id=r["id"], file_name=r["file_name"],
                        full_path=r["full_path"], file_hash=r["file_hash"],
                        created_at=r["created_at"], updated_at=r["updated_at"],
                        file_ext=r["file_ext"], file_size=r["file_size"],
                        create_time=r["create_time"], modify_time=r["modify_time"],
                        is_deleted=bool(r["is_deleted"]),
                        deleted_at=r["deleted_at"],
                    )
                    for r in rows
                ]

            results = fts_results + like_results
            if query:
                self.record_search(query)
            return results

    def scan_candidates(self, paths: Sequence[Path]) -> list[ImportCandidate]:
        """
        扫描候选文件
        
        Args:
            paths: 要扫描的路径列表（可以是文件或目录）
            
        Returns:
            候选文件列表
        """
        candidates: list[ImportCandidate] = []
        for p in paths:
            if p.is_dir():
                for root, _, files in os.walk(p):
                    for name in files:
                        fp = Path(root) / name
                        try:
                            st = fp.stat()
                        except OSError:
                            continue
                        candidates.append(ImportCandidate(path=fp, size=int(st.st_size)))
            elif p.is_file():
                try:
                    st = p.stat()
                except OSError:
                    continue
                candidates.append(ImportCandidate(path=p, size=int(st.st_size)))
        return candidates

    def import_files(self, candidates: Iterable[ImportCandidate]) -> int:
        from src.app.services.import_worker import ImportWorker
        candidates_list = list(candidates)
        if not candidates_list:
            return 0
        if getattr(self, '_import_worker', None) is not None:
            logger.warning("Import already in progress, ignoring duplicate call")
            return 0
        worker = ImportWorker(self._db, candidates_list)
        if self.signals:
            worker.progress.connect(lambda c, t: self.signals.import_progress.emit(c, t))
            worker.import_finished.connect(lambda count: self.signals.import_finished.emit(count))
            worker.finished.connect(lambda: self.signals.files_updated.emit(None))
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: setattr(self, '_import_worker', None))
        if self._index_worker is not None:
            worker.file_imported.connect(lambda fid, fp: self._index_worker.enqueue(fid, Path(fp)))
        self._import_worker = worker
        worker.run()
        return 0

    def create_tag(self, tag_name: str, tag_type: Optional[str] = None, parent_id: Optional[int] = None) -> Tag:
        """
        创建新标记
        
        Args:
            tag_name: 标记名称
            tag_type: 标记类型（可选）
            parent_id: 父标记ID（可选，用于创建层级标记）
            
        Returns:
            创建的标记对象
        """
        now = int(time.time())
        with self._db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tags (tag_name, tag_type, parent_id, is_deleted, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (tag_name, tag_type, parent_id, now, now),
            )
            tag_id = cursor.lastrowid
            conn.commit()
        
        tag = self.get_tag(tag_id)
        self.signals.tags_updated.emit()
        return tag

    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """
        根据ID获取标记
        
        Args:
            tag_id: 标记ID
            
        Returns:
            标记对象，如果不存在则返回None
        """
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT id, tag_name, tag_type, parent_id, is_deleted, deleted_at, created_at, updated_at
                FROM tags
                WHERE id = ?
                """,
                (tag_id,),
            ).fetchone()
        
        if not row:
            return None
        
        return Tag(
            id=row["id"],
            tag_name=row["tag_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            tag_type=row["tag_type"],
            parent_id=row["parent_id"],
            is_deleted=bool(row["is_deleted"]),
            deleted_at=row["deleted_at"],
        )

    def list_tags(self, include_deleted: bool = False) -> list[Tag]:
        """
        列出所有标记
        
        Args:
            include_deleted: 是否包含已删除的标记
            
        Returns:
            标记列表
        """
        if self._db is None:
            return []

        with self._db.connect() as conn:
            query = """
                SELECT id, tag_name, tag_type, parent_id, is_deleted, deleted_at, created_at, updated_at
                FROM tags
            """
            if not include_deleted:
                query += " WHERE is_deleted = 0"
            query += " ORDER BY created_at ASC"
            
            rows = conn.execute(query).fetchall()
        
        return [
            Tag(
                id=r["id"],
                tag_name=r["tag_name"],
                tag_type=r["tag_type"],
                parent_id=r["parent_id"],
                is_deleted=bool(r["is_deleted"]),
                deleted_at=r["deleted_at"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def delete_tag(self, tag_id: int) -> None:
        """
        软删除标记
        
        Args:
            tag_id: 要删除的标记ID
        """
        now = int(time.time())
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE tags
                SET is_deleted = 1, deleted_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, tag_id),
            )
            conn.commit()
        
        self.signals.tags_updated.emit()

    def add_tag_to_file(self, file_id: int, tag_id: int) -> None:
        """
        为文件添加标记
        
        Args:
            file_id: 文件ID
            tag_id: 标记ID
        """
        now = int(time.time())
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO file_tag_relation (file_id, tag_id, created_at)
                VALUES (?, ?, ?)
                """,
                (file_id, tag_id, now),
            )
            conn.commit()

    def remove_tag_from_file(self, file_id: int, tag_id: int) -> None:
        """
        从文件中移除标记
        
        Args:
            file_id: 文件ID
            tag_id: 标记ID
        """
        with self._db.connect() as conn:
            conn.execute(
                """
                DELETE FROM file_tag_relation
                WHERE file_id = ? AND tag_id = ?
                """,
                (file_id, tag_id),
            )
            conn.commit()

    def get_file_tags(self, file_id: int) -> list[Tag]:
        """
        获取文件的所有标记
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件的标记列表
        """
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT t.id, t.tag_name, t.tag_type, t.parent_id, t.is_deleted, t.deleted_at, t.created_at, t.updated_at
                FROM tags t
                JOIN file_tag_relation ftr ON t.id = ftr.tag_id
                WHERE ftr.file_id = ? AND t.is_deleted = 0
                """,
                (file_id,),
            ).fetchall()
        
        return [
            Tag(
                id=r["id"],
                tag_name=r["tag_name"],
                tag_type=r["tag_type"],
                parent_id=r["parent_id"],
                is_deleted=bool(r["is_deleted"]),
                deleted_at=r["deleted_at"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def soft_delete_file(self, file_id: int) -> None:
        """
        软删除文件
        
        Args:
            file_id: 要删除的文件ID
        """
        now = int(time.time())
        with self._db.connect() as conn:
            conn.execute(
                """
                UPDATE files
                SET is_deleted = 1, deleted_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, file_id),
            )
            conn.commit()
        
        if self.signals:
            self.signals.files_updated.emit(None)

    def get_file_note(self, file_id: int) -> Optional[str]:
        """
        获取文件的文档简介
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件的文档简介，如果不存在则返回None
        """
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT content
                FROM file_notes
                WHERE file_id = ?
                """,
                (file_id,),
            ).fetchone()
        
        return row["content"] if row else None

    def set_file_note(self, file_id: int, content: str) -> None:
        """
        设置文件的文档简介
        
        Args:
            file_id: 文件ID
            content: 文档简介内容
        """
        now = int(time.time())
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_notes (file_id, content, updated_at)
                VALUES (?, ?, ?)
                """,
                (file_id, content, now),
            )
            conn.commit()

    def get_file_imprints(self, file_id: int) -> list[dict]:
        """
        获取文件的特定印记，按时间倒序排序
        
        Args:
            file_id: 文件ID
            
        Returns:
            特定印记列表，每个元素包含id、content和created_at
        """
        with self._db.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, content, created_at
                FROM file_imprints
                WHERE file_id = ?
                ORDER BY created_at DESC
                """,
                (file_id,),
            ).fetchall()
        
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "created_at": r["created_at"]
            }
            for r in rows
        ]

    def add_file_imprint(self, file_id: int, content: str) -> None:
        """
        添加文件的特定印记
        
        Args:
            file_id: 文件ID
            content: 特定印记内容
        """
        now = int(time.time())
        with self._db.connect() as conn:
            conn.execute(
                """
                INSERT INTO file_imprints (file_id, content, created_at)
                VALUES (?, ?, ?)
                """,
                (file_id, content, now),
            )
            conn.commit()
    
    def get_all_files(self, sort_by: str = "name", sort_order: str = "asc") -> list[FileRecord]:
        """
        获取所有文件
        
        Args:
            sort_by: 排序字段
            sort_order: 排序顺序
            
        Returns:
            文件记录列表
        """
        return self.list_files(sort_by=sort_by, sort_order=sort_order)
    
    def get_files_by_tag(self, tag_id: int) -> list[FileRecord]:
        """
        根据标签获取文件
        
        Args:
            tag_id: 标签ID
            
        Returns:
            文件记录列表
        """
        return self.list_files(tag_id=tag_id)
    
    def get_file_by_id(self, file_id: int) -> Optional[FileRecord]:
        """
        根据ID获取文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件记录，如果不存在则返回None
        """
        with self._db.connect() as conn:
            row = conn.execute(
                """
                SELECT id, file_name, file_ext, full_path, file_size, create_time, modify_time,
                       file_hash, is_deleted, deleted_at, created_at, updated_at
                FROM files
                WHERE id = ? AND is_deleted = 0
                """,
                (file_id,),
            ).fetchone()
        
        if not row:
            return None
        
        return FileRecord(
            id=row["id"],
            file_name=row["file_name"],
            full_path=row["full_path"],
            file_hash=row["file_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            file_ext=row["file_ext"],
            file_size=row["file_size"],
            create_time=row["create_time"],
            modify_time=row["modify_time"],
            is_deleted=bool(row["is_deleted"]),
            deleted_at=row["deleted_at"],
        )
    
    def get_all_tags(self) -> list[Tag]:
        """
        获取所有标签
        
        Returns:
            标签列表
        """
        return self.list_tags()

    def fuzzy_search_tags(self, query: str = "") -> list[Tag]:
        """
        模糊搜索标记
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的标记列表
        """
        all_tags = self.get_all_tags()
        if not query:
            return all_tags
        return [t for t in all_tags if query.lower() in (t.tag_name or "").lower()]

    def count_files(self, tag_id: Optional[int] = None) -> int:
        if self._db is None:
            return 0
        try:
            if tag_id is None:
                return self._db.count_all_files()
            return self._db.count_files_by_tag(tag_id)
        except DbError:
            logger.error("Failed to count files", exc_info=True)
            return 0

    def _on_file_system_changed(self, events: list[FileEvent]) -> None:
        if self._db is None:
            return
        updated = False
        for ev in events:
            if ev.event_type == "modified":
                p = Path(ev.src_path)
                if p.exists():
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    file_id = self._db.find_by_path_and_size(ev.src_path, int(st.st_size))
                    if file_id is None:
                        try:
                            file_hash = sha256_file(p)
                        except FileReadError:
                            continue
                        row = self._db.find_by_hash(file_hash)
                        if row:
                            file_id = row["id"]
                    if file_id is None:
                        with self._db.connect() as conn:
                            row = conn.execute(
                                "SELECT id FROM files WHERE full_path = ? AND is_deleted = 0 LIMIT 1",
                                (ev.src_path,),
                            ).fetchone()
                            file_id = row["id"] if row else None
                    if file_id is not None:
                        self._handle_file_modified(file_id, int(st.st_size), int(st.st_mtime))
                        updated = True
                        if self._index_worker:
                            ext = p.suffix.lower()
                            if ext in {".txt", ".md", ".log", ".csv", ".pdf", ".docx", ".xlsx"}:
                                self._index_worker.enqueue(file_id, p)
            elif ev.event_type == "deleted":
                file_id = None
                with self._db.connect() as conn:
                    row = conn.execute(
                        "SELECT id FROM files WHERE full_path = ? AND is_deleted = 0 LIMIT 1",
                        (ev.src_path,),
                    ).fetchone()
                    if row:
                        file_id = row["id"]
                self._handle_file_deleted_by_path(ev.src_path)
                updated = True
                if file_id is not None and self._db is not None:
                    with self._db.connect() as fts_conn:
                        self._db.delete_fts(fts_conn, file_id)
            elif ev.event_type == "moved":
                new_path = Path(ev.dest_path)
                if new_path.exists():
                    try:
                        file_hash = sha256_file(new_path)
                    except FileReadError:
                        continue
                    file_id = self._handle_file_moved(file_hash, ev.dest_path)
                    updated = True
                    if file_id is not None and self._index_worker:
                        ext = new_path.suffix.lower()
                        if ext in {".txt", ".md", ".log", ".csv", ".pdf", ".docx", ".xlsx"}:
                            self._index_worker.enqueue(file_id, new_path)
            elif ev.event_type == "created":
                if self._auto_import:
                    p = Path(ev.src_path)
                    if p.exists():
                        try:
                            st = p.stat()
                        except OSError:
                            continue
                        cand = ImportCandidate(path=p, size=int(st.st_size))
                        self.import_files([cand])
                        updated = True
        if updated and self.signals:
            self.signals.files_updated.emit(None)

    def _handle_file_moved(self, file_hash: str, new_full_path: str) -> Optional[int]:
        row = self._db.find_by_hash(file_hash)
        if row is None:
            return None
        p = Path(new_full_path)
        self._db.update_file_path(
            file_id=row["id"],
            new_path=new_full_path,
            new_name=p.name,
            new_ext=p.suffix.lower().lstrip(".") if p.suffix else None,
        )
        return row["id"]

    def _handle_file_deleted_by_path(self, full_path: str) -> None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT file_hash FROM files WHERE full_path = ? AND is_deleted = 0 LIMIT 1",
                (full_path,),
            ).fetchone()
        if row:
            self._db.soft_delete_by_hash(row["file_hash"])

    def _handle_file_modified(self, file_id: int, file_size: int, modify_time: int) -> None:
        self._db.update_file_meta(file_id, file_size, modify_time)

    def record_search(self, query: str) -> None:
        if not query:
            return
        now = int(time.time())
        payload = json.dumps({"query": query, "timestamp": now})
        self._db.record_search(payload, now)
        self._db.delete_old_searches(max_keep=50)

    def get_recent_searches(self, limit: int = 10) -> list[dict]:
        return self._db.get_recent_searches(limit)

    def set_auto_import(self, enabled: bool) -> None:
        self._auto_import = enabled

    def init_index_worker(self) -> None:
        if self._db is None:
            return
        from src.app.services.index_worker import IndexWorker
        self._index_worker = IndexWorker(self._db)
        if self.signals:
            self._index_worker.indexing_progress.connect(
                lambda c, t: self.signals.indexing_progress.emit(c, t)
            )
        self._index_worker.start()

    def start_progressive_indexing(self) -> None:
        if self._db is None or self._index_worker is None:
            return
        conn = self._db.connect()
        rows = conn.execute(
            """SELECT f.id, f.full_path, f.file_ext FROM files f
               LEFT JOIN file_content_status fcs ON f.id = fcs.file_id
               WHERE f.is_deleted = 0
                 AND (fcs.file_id IS NULL OR fcs.status = 'pending')
               ORDER BY f.modify_time DESC"""
        ).fetchall()
        conn.close()
        if not rows:
            return
        supported = {".txt", ".md", ".log", ".csv", ".pdf", ".docx", ".xlsx"}
        items = []
        for r in rows:
            path = Path(r["full_path"])
            if path.suffix.lower() in supported:
                items.append((r["id"], path))
        if items:
            self._index_worker.enqueue_batch(items)


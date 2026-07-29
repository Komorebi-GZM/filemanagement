import hashlib
import logging
import time
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal

from src.app.db.database import Database
from src.app.viewmodel.main_viewmodel import sha256_file, ImportCandidate

logger = logging.getLogger(__name__)


class ImportWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()
    file_imported = pyqtSignal(int, str)

    def __init__(self, db: Database, candidates: list[ImportCandidate], parent: Optional[QObject] = None):
        super().__init__(parent)
        self._db = db
        self._candidates = candidates

    def run(self):
        thread = QThread()
        self.moveToThread(thread)
        thread.started.connect(lambda: self._do_import(thread), Qt.DirectConnection)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _do_import(self, thread: QThread) -> None:
        now = int(time.time())
        inserted = 0
        conn = self._db.connect()
        total = len(self._candidates)
        for i, c in enumerate(self._candidates):
            try:
                file_hash = sha256_file(c.path)
            except Exception:
                logger.exception("SHA256 failed: %s", c.path)
                self.progress.emit(i + 1, total)
                continue
            file_name = c.path.name
            file_ext = c.path.suffix.lower().lstrip(".") if c.path.suffix else None
            full_path = str(c.path.resolve())
            try:
                st = c.path.stat()
            except OSError:
                self.progress.emit(i + 1, total)
                continue
            row = conn.execute(
                "SELECT id FROM files WHERE file_hash = ?", (file_hash,)
            ).fetchone()
            if row is None:
                conn.execute(
                    """INSERT INTO files (file_name, file_ext, full_path, file_size,
                       create_time, modify_time, file_hash, is_deleted, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                    (file_name, file_ext, full_path, int(st.st_size),
                     int(st.st_ctime), int(st.st_mtime), file_hash, now, now),
                )
                file_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                inserted += 1
            else:
                file_id = row["id"]
                conn.execute(
                    """UPDATE files SET file_name=?, file_ext=?, full_path=?, file_size=?,
                       create_time=?, modify_time=?, is_deleted=0, deleted_at=NULL, updated_at=?
                       WHERE file_hash=?""",
                    (file_name, file_ext, full_path, int(st.st_size),
                     int(st.st_ctime), int(st.st_mtime), now, file_hash),
                )
            self.file_imported.emit(file_id, full_path)
            self.progress.emit(i + 1, total)
        conn.commit()
        conn.close()
        self.finished.emit()
        logger.info("Async import finished: %s new files", inserted)
        thread.quit()

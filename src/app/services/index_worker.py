import logging
import time
from pathlib import Path
from queue import Empty as QueueEmpty, Queue, Full as QueueFull
from typing import Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from src.app.db.database import Database
from src.app.services.text_extractor import extract_text

logger = logging.getLogger(__name__)

INDEX_BATCH_SIZE = 100
INDEX_BATCH_INTERVAL_MS = 200
QUEUE_MAXSIZE = 10000

SUPPORTED_EXTENSIONS = {".txt", ".md", ".log", ".csv", ".pdf", ".docx", ".xlsx"}


class IndexWorker(QObject):
    indexing_progress = pyqtSignal(int, int)
    indexing_finished = pyqtSignal()
    index_updated = pyqtSignal(int)

    def __init__(self, db: Database, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._db = db
        self._queue: Queue = Queue(maxsize=QUEUE_MAXSIZE)
        self._total = 0
        self._processed = 0
        self._running = False
        self._thread: Optional[QThread] = None

    def enqueue(self, file_id: int, path: Path) -> None:
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return
        try:
            self._queue.put_nowait((file_id, path))
        except QueueFull:
            logger.warning("Index queue full, dropping oldest")
            try:
                self._queue.get_nowait()
                self._queue.put_nowait((file_id, path))
            except QueueFull:
                pass

    def enqueue_batch(self, items: list[tuple[int, Path]]) -> None:
        for file_id, path in items:
            self.enqueue(file_id, path)
        self._total = self._queue.qsize()
        self._processed = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._process_queue)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None

    def _process_queue(self) -> None:
        conn = self._db.connect()
        self._db.create_fts_table(conn)
        while self._running:
            processed_in_batch = 0
            while processed_in_batch < INDEX_BATCH_SIZE and self._running:
                try:
                    file_id, path = self._queue.get(timeout=0.1)
                except QueueEmpty:
                    if self._queue.empty():
                        break
                    continue
                self._index_one(conn, file_id, path)
                processed_in_batch += 1
                self._processed += 1
                self.indexing_progress.emit(self._processed, self._total)
            if processed_in_batch > 0:
                conn.commit()
                QThread.msleep(INDEX_BATCH_INTERVAL_MS)
            if self._total > 0 and self._queue.empty() and self._processed >= self._total:
                self.indexing_finished.emit()
                break
        conn.close()

    def _index_one(self, conn, file_id: int, path: Path) -> None:
        try:
            ext = path.suffix.lower().lstrip(".")
            text = extract_text(path, ext)
            if text:
                file_name = path.name
                self._db.upsert_fts(conn, file_id, file_name, text)
            else:
                reason = "skipped_too_large" if path.stat().st_size > 50*1024*1024 else "skipped_format"
                conn.execute(
                    "INSERT INTO file_content_status (file_id, content_length, status, indexed_at) "
                    "VALUES (?, 0, ?, ?) ON CONFLICT(file_id) DO UPDATE SET "
                    "content_length = 0, status = excluded.status, error_message = NULL, indexed_at = excluded.indexed_at",
                    (file_id, reason, int(time.time())),
                )
            self.index_updated.emit(file_id)
        except Exception:
            logger.exception("Index failed for file_id=%s path=%s", file_id, path)
            now = int(time.time())
            conn.execute(
                "INSERT INTO file_content_status (file_id, content_length, status, indexed_at) "
                "VALUES (?, 0, 'error', ?) ON CONFLICT(file_id) DO UPDATE SET "
                "status = 'error', content_length = 0, indexed_at = excluded.indexed_at",
                (file_id, now),
            )
            self.index_updated.emit(file_id)

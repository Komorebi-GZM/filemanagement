from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer


@dataclass
class FileEvent:
    event_type: str  # "created" | "modified" | "deleted" | "moved"
    src_path: str
    dest_path: str  # only for "moved"
    file_hash: str  # empty string if unknown
    is_directory: bool


class _FileChangeHandler(PatternMatchingEventHandler):
    IGNORE_PATTERNS = [
        "*.tmp", "*.temp", "~$*", "*.swp", "*.swx",
        "*.lnk", "Thumbs.db", ".DS_Store",
    ]
    IGNORE_DIRS = [".git", "__pycache__", ".svn"]

    def __init__(self, queue_fn):
        exclude_patterns = [
            pattern
            for pat in self.IGNORE_PATTERNS
            for pattern in (pat, f"**/{pat}")
        ] + [
            pattern
            for dir_name in self.IGNORE_DIRS
            for pattern in (f"{dir_name}/**", f"**/{dir_name}/**")
        ]
        super().__init__(
            patterns=None,
            ignore_patterns=exclude_patterns,
            ignore_directories=True,
            case_sensitive=False,
        )
        self._queue_fn = queue_fn

    def on_modified(self, event: FileSystemEvent):
        self._queue_fn("modified", src_path=event.src_path)

    def on_created(self, event: FileSystemEvent):
        self._queue_fn("created", src_path=event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        self._queue_fn("deleted", src_path=event.src_path)

    def on_moved(self, event: FileSystemEvent):
        self._queue_fn(
            "moved",
            src_path=event.src_path,
            dest_path=event.dest_path,
        )


class FileMonitor(QObject):
    file_system_changed = pyqtSignal(object)  # list[FileEvent]
    _event_queued = pyqtSignal()

    def __init__(self, debounce_ms: int = 2000, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._debounce_ms = debounce_ms
        self._pending: dict[str, FileEvent] = {}
        self._observer = Observer()
        self._handlers: list[_FileChangeHandler] = []
        self._watch_dirs: list[Path] = []

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush)
        self._event_queued.connect(self._on_event_queued)

    def start(self, watch_dirs: list[Path]) -> None:
        self._watch_dirs = watch_dirs
        for d in watch_dirs:
            if not d.exists():
                continue
            h = _FileChangeHandler(self._queue_event)
            self._handlers.append(h)
            self._observer.schedule(h, str(d), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        self._timer.stop()
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=3)
        self._pending.clear()

    def is_running(self) -> bool:
        return self._observer.is_alive()

    def _queue_event(
        self,
        event_type: str,
        src_path: str,
        dest_path: str = "",
    ) -> None:
        key = dest_path or src_path
        self._pending[key] = FileEvent(
            event_type=event_type,
            src_path=src_path,
            dest_path=dest_path,
            file_hash="",
            is_directory=False,
        )
        self._event_queued.emit()

    def _on_event_queued(self) -> None:
        self._timer.start(self._debounce_ms)

    def _flush(self) -> None:
        if not self._pending:
            return
        batch = list(self._pending.values())
        self._pending.clear()
        self.file_system_changed.emit(batch)

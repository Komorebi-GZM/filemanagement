from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal


class MainSignals(QObject):
    """主信号类"""
    files_updated = pyqtSignal(list)
    tags_updated = pyqtSignal()
    file_tagged = pyqtSignal(int, int)  # file_id, tag_id
    file_untagged = pyqtSignal(int, int)  # file_id, tag_id
    file_note_updated = pyqtSignal(int)  # file_id
    file_imprint_added = pyqtSignal(int)  # file_id
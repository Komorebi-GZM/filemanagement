from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QKeyEvent


class CommandPalette(QWidget):
    text_entered = pyqtSignal(str)
    tag_selected_for_file = pyqtSignal(int, int)

    def __init__(self, parent=None, vm=None):
        super().__init__(parent)
        self.vm = vm
        self.context_file_id = None
        self._history_items: list[str] = []
        self._history_index = -1
        self._suppress_history_reset = False

        layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索命令...")
        self.list_widget = QListWidget()
        layout.addWidget(self.search_box)
        layout.addWidget(self.list_widget)

        self.list_widget.itemActivated.connect(self._on_item_activated)
        self.search_box.textChanged.connect(self._on_text_changed)
        self.search_box.installEventFilter(self)

    def set_context_file(self, file_id: int, file_name: str):
        self.context_file_id = file_id
        self._history_index = -1
        if file_id is not None:
            self.search_box.setPlaceholderText(f"为文件 {file_name} 添加标签...")
            self._load_tags()
        else:
            self.search_box.setPlaceholderText("搜索命令...")
            self.list_widget.clear()

    def set_history(self, items: list[dict]):
        self._history_items = []
        import json
        for item in items:
            try:
                data = json.loads(item["query_json"])
                q = data.get("query", "")
                if q:
                    self._history_items.append(q)
            except (json.JSONDecodeError, KeyError):
                continue
        self._history_index = -1
        if not self.context_file_id and self._history_items:
            self.list_widget.clear()
            for h in self._history_items:
                self.list_widget.addItem(QListWidgetItem(h))

    def eventFilter(self, obj, event):
        if obj is self.search_box and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                self._on_arrow_key(event.key())
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            self._on_arrow_key(event.key())
            event.accept()
        else:
            super().keyPressEvent(event)

    def _on_arrow_key(self, key: int):
        if self.context_file_id is not None:
            return
        if not self._history_items:
            return
        n = len(self._history_items)
        if key == Qt.Key_Up:
            idx = max(0, self._history_index - 1) if self._history_index >= 0 else n - 1
        else:
            if self._history_index >= n - 1:
                idx = -1
            else:
                idx = self._history_index + 1

        self._history_index = idx
        self._suppress_history_reset = True
        if 0 <= idx < n:
            self.search_box.setText(self._history_items[idx])
        else:
            self.search_box.clear()
        self._suppress_history_reset = False

    def _on_text_changed(self, text: str):
        if text and not self._suppress_history_reset:
            self._history_index = -1

    def _load_tags(self):
        self.list_widget.clear()
        if self.vm is not None:
            tags = self.vm.get_all_tags()
            for tag in tags:
                item = QListWidgetItem(tag.tag_name)
                item.setData(Qt.UserRole, tag.id)
                self.list_widget.addItem(item)

    def _on_item_activated(self, item):
        if self.context_file_id is not None:
            tag_id = item.data(Qt.UserRole)
            if tag_id is not None:
                self.tag_selected_for_file.emit(self.context_file_id, tag_id)
                self.hide()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.set_context_file(None, "")

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QKeyEvent, QColor


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

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(400)
        self.setMaximumWidth(600)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索命令...")
        self.list_widget = QListWidget()
        layout.addWidget(self.search_box)
        layout.addWidget(self.list_widget)

        self.setStyleSheet("""
            CommandPalette {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QLineEdit {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
            QListWidget {
                border: none;
                border-radius: 6px;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #F1F5F9;
            }
            QListWidget::item:selected {
                background: #DBEAFE;
                color: #2563EB;
            }
        """)

        self.list_widget.itemActivated.connect(self._on_item_activated)
        self.search_box.textChanged.connect(self._on_text_changed)
        self.search_box.returnPressed.connect(self._on_return_pressed)
        self.search_box.installEventFilter(self)

    def set_context_file(self, file_id: int, file_name: str):
        self.context_file_id = file_id
        self._history_index = -1
        self.search_box.blockSignals(True)
        self.search_box.clear()
        self.search_box.blockSignals(False)
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
        if not self.context_file_id:
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
        if self.context_file_id is not None:
            self._load_tags(text)
            return
        if text and not self._suppress_history_reset:
            self._history_index = -1

    def _load_tags(self, query: str = ""):
        self.list_widget.clear()
        if self.vm is None:
            return
        q = query.strip()
        if q:
            if hasattr(self.vm, "fuzzy_search_tags"):
                tags = self.vm.fuzzy_search_tags(q)
            else:
                tags = [
                    t for t in self.vm.get_all_tags()
                    if q.lower() in (t.tag_name or "").lower()
                ]
        else:
            tags = self.vm.get_all_tags()
        for tag in tags:
            item = QListWidgetItem(tag.tag_name)
            item.setData(Qt.UserRole, tag.id)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _on_return_pressed(self):
        if self.context_file_id is not None:
            item = self.list_widget.currentItem() or (
                self.list_widget.item(0) if self.list_widget.count() > 0 else None
            )
            if item is not None:
                self._on_item_activated(item)
            return
        text = self.search_box.text().strip()
        if text:
            self.text_entered.emit(text)

    def _on_item_activated(self, item):
        if self.context_file_id is not None:
            tag_id = item.data(Qt.UserRole)
            if tag_id is not None:
                self.tag_selected_for_file.emit(self.context_file_id, tag_id)
                self.hide()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.set_context_file(None, "")

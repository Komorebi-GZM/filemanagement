from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PyQt5.QtCore import pyqtSignal, Qt

class CommandPalette(QWidget):
    text_entered = pyqtSignal(str)
    tag_selected_for_file = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.context_file_id = None
        
        layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索命令...")
        self.list_widget = QListWidget()
        layout.addWidget(self.search_box)
        layout.addWidget(self.list_widget)

        self.list_widget.itemActivated.connect(self._on_item_activated)

    def set_context_file(self, file_id: int, file_name: str):
        self.context_file_id = file_id
        if file_id is not None:
            self.search_box.setPlaceholderText(f"为文件 {file_name} 添加标签...")
            self._load_tags()
        else:
            self.search_box.setPlaceholderText("搜索命令...")
            self.list_widget.clear()

    def _load_tags(self):
        self.list_widget.clear()
        if hasattr(self.parent(), 'vm'):
            tags = self.parent().vm.get_all_tags()
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

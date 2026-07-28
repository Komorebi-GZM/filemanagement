from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget
from PyQt5.QtCore import pyqtSignal

class CommandPalette(QWidget):
    text_entered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.list_widget = QListWidget()
        layout.addWidget(self.search_box)
        layout.addWidget(self.list_widget)

from PyQt5.QtWidgets import QApplication
from src.app.ui.command_palette import CommandPalette

def test_command_palette_creation(qapp):
    palette = CommandPalette()
    assert palette.search_box is not None
    assert palette.list_widget is not None

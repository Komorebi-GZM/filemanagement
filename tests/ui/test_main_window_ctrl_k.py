from unittest.mock import MagicMock
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from src.app.ui.main_window import MainWindow

def test_ctrl_k_shows_palette(qapp, monkeypatch):
    monkeypatch.setattr('src.app.db.database.Database.connect', MagicMock())
    win = MainWindow()
    win.show()
    assert win.command_palette.isHidden()
    
    QTest.keyClick(win, Qt.Key_K, Qt.ControlModifier)
    assert not win.command_palette.isHidden()

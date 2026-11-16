from unittest.mock import MagicMock
from PyQt5.QtCore import Qt

from src.app.model.file_record import FileRecord
from src.app.model.tag import Tag
from src.app.ui.main_window import MainWindow
from src.app.viewmodel.signals import MainSignals


def _setup_window(monkeypatch, vm):
    monkeypatch.setattr("src.app.db.database.Database.connect", MagicMock())
    signals = MainSignals()
    vm.get_all_tags.return_value = []
    vm.get_all_files.return_value = []
    vm.get_all_file_extensions.return_value = []
    vm.list_files.return_value = []
    vm.count_files.return_value = 0
    vm.get_file_tags.return_value = []
    vm.get_file_note.return_value = None
    vm.get_file_imprints.return_value = []

    win = MainWindow(vm=vm, signals=signals)
    return win, signals


def test_location_combo_displays_label_passes_key(qapp, monkeypatch):
    vm = MagicMock()
    vm.get_all_locations.return_value = [
        ("Macintosh HD", "/"),
        ("Backup", "/Volumes/Backup"),
    ]

    win, _ = _setup_window(monkeypatch, vm)

    combo = win.filter_location_combo
    assert combo.count() == 3
    assert combo.itemText(0) == "所有位置"
    assert combo.itemData(0) is None

    assert combo.itemText(1) == "Macintosh HD"
    assert combo.itemData(1) == "/"

    assert combo.itemText(2) == "Backup"
    assert combo.itemData(2) == "/Volumes/Backup"

    # Selecting "Macintosh HD" triggers filter with location="/"
    vm.list_files.reset_mock()
    combo.setCurrentIndex(1)
    vm.list_files.assert_called_with(file_ext=None, location="/")

    # Selecting "Backup" triggers filter with location="/Volumes/Backup"
    vm.list_files.reset_mock()
    combo.setCurrentIndex(2)
    vm.list_files.assert_called_with(file_ext=None, location="/Volumes/Backup")


def test_location_combo_legacy_vm_fallback(qapp, monkeypatch):
    # Mock VM without get_all_locations attribute
    vm = MagicMock(spec=["get_all_tags", "get_all_files", "get_all_file_extensions",
                         "get_all_drive_letters", "list_files", "count_files",
                         "get_file_tags", "get_file_note", "get_file_imprints", "signals"])
    vm.get_all_drive_letters.return_value = ["C:", "D:"]

    win, _ = _setup_window(monkeypatch, vm)

    combo = win.filter_location_combo
    assert combo.count() == 3
    assert combo.itemText(0) == "所有位置"
    assert combo.itemText(1) == "C:"
    assert combo.itemText(2) == "D:"

    vm.list_files.reset_mock()
    combo.setCurrentIndex(1)
    vm.list_files.assert_called_with(file_ext=None, location="C:")

from unittest.mock import MagicMock
from PyQt5.QtWidgets import QMessageBox

from src.app.model.file_record import FileRecord
from src.app.model.tag import Tag
from src.app.ui.main_window import MainWindow
from src.app.viewmodel.signals import MainSignals


def _make_window(monkeypatch):
    monkeypatch.setattr("src.app.db.database.Database.connect", MagicMock())
    signals = MainSignals()
    vm = MagicMock()
    vm.get_all_tags.return_value = [
        Tag(id=10, tag_name="Work", created_at=0, updated_at=0),
        Tag(id=20, tag_name="Docs", created_at=0, updated_at=0),
    ]
    vm.get_all_files.return_value = [
        FileRecord(
            id=1,
            file_name="alpha.txt",
            full_path="/tmp/alpha.txt",
            file_hash="h1",
            created_at=0,
            updated_at=0,
            file_ext="txt",
            file_size=12,
            modify_time=0,
        ),
        FileRecord(
            id=2,
            file_name="beta.txt",
            full_path="/tmp/beta.txt",
            file_hash="h2",
            created_at=0,
            updated_at=0,
            file_ext="txt",
            file_size=24,
            modify_time=0,
        ),
    ]
    vm.get_all_file_extensions.return_value = ["txt"]
    vm.get_all_drive_letters.return_value = []
    vm.list_files.return_value = vm.get_all_files.return_value
    vm.count_files.return_value = 2
    vm.get_file_tags.return_value = []
    vm.get_file_note.return_value = "initial note"
    vm.get_file_imprints.return_value = []
    vm.get_file_by_id.side_effect = lambda fid: next(
        (f for f in vm.get_all_files.return_value if f.id == fid), None
    )

    win = MainWindow(vm=vm, signals=signals)
    return win, vm, signals


def test_files_updated_none_reloads_and_empty_list_clears(qapp, monkeypatch):
    win, vm, signals = _make_window(monkeypatch)
    assert win.file_list.count() == 2

    # Empty search/filter list should intentionally clear the view
    win._update_file_list([])
    assert win.file_list.count() == 0

    # ViewModel emitting None should reload all files from DB
    signals.files_updated.emit(None)
    assert win.file_list.count() == 2


def test_async_import_dialog_uses_import_finished_signal(qapp, monkeypatch, tmp_path):
    win, vm, signals = _make_window(monkeypatch)

    sample = tmp_path / "sample.txt"
    sample.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        "PyQt5.QtWidgets.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(sample)], ""),
    )
    info_calls = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda parent, title, text, *args: info_calls.append((title, text)),
    )
    vm.import_files.return_value = 0

    # Calling _on_import_files should NOT show a premature "0 files" dialog
    win._on_import_files()
    assert vm.import_files.called
    assert info_calls == []

    # Completion signal delivers actual imported count
    signals.import_finished.emit(3)
    assert info_calls == [("导入完成", "成功导入 3 个文件")]

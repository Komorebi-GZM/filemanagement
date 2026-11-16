from unittest.mock import MagicMock
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QDialog, QInputDialog, QMenu, QMessageBox

from src.app.model.file_record import FileRecord
from src.app.model.tag import Tag
from src.app.ui.main_window import MainWindow, NoteDialog
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


def test_file_list_context_menu_actions_wired(qapp, monkeypatch):
    win, vm, _ = _make_window(monkeypatch)
    win.file_list.setCurrentRow(0)
    assert win.file_list.item(0).isSelected()

    # Intercept QMenu.exec_ and trigger "添加注释"
    def trigger_action(action_text):
        def _exec(self, *args, **kwargs):
            for action in self.actions():
                if action.text() == action_text:
                    action.trigger()
                    return action
            return None
        return _exec

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)

    # 1. 添加注释 -> NoteDialog -> vm.set_file_note
    monkeypatch.setattr(QMenu, "exec_", trigger_action("添加注释"))
    monkeypatch.setattr(NoteDialog, "exec_", lambda self: QDialog.Accepted)
    monkeypatch.setattr(NoteDialog, "get_note", lambda self: "updated note")
    win.file_list.show_context_menu(QPoint(5, 5))
    vm.set_file_note.assert_called_once_with(1, "updated note")

    # 2. 添加标签 (single selection) -> opens CommandPalette scoped to file 1
    monkeypatch.setattr(QMenu, "exec_", trigger_action("添加标签"))
    win.file_list.show_context_menu(QPoint(5, 5))
    assert win.command_palette.context_file_id == 1

    # 3. 添加标签 (multi selection) -> QInputDialog -> vm.add_tag_to_file
    win.command_palette.hide()
    win.file_list.item(1).setSelected(True)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args, **kwargs: ("Docs", True))
    win.file_list.show_context_menu(QPoint(5, 5))
    vm.add_tag_to_file.assert_any_call(1, 20)
    vm.add_tag_to_file.assert_any_call(2, 20)

    # 4. 删除 -> confirmation -> vm.soft_delete_file
    win.file_list.clearSelection()
    win.file_list.item(0).setSelected(True)
    monkeypatch.setattr(QMenu, "exec_", trigger_action("删除"))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    win.file_list.show_context_menu(QPoint(5, 5))
    vm.soft_delete_file.assert_called_once_with(1)


def test_tag_tree_context_menu_actions_wired(qapp, monkeypatch):
    win, vm, _ = _make_window(monkeypatch)
    root = win.tag_tree.topLevelItem(0)
    tag_item = root.child(0)
    tag_rect = win.tag_tree.visualItemRect(tag_item)
    root_rect = win.tag_tree.visualItemRect(root)

    captured_actions = {}

    def _exec_and_trigger(action_text):
        def _exec(self, *args, **kwargs):
            captured_actions["actions"] = {a.text(): a for a in self.actions()}
            act = captured_actions["actions"].get(action_text)
            if act and act.isEnabled():
                act.trigger()
            return act
        return _exec

    # Root node ("所有文件") must disable delete action
    monkeypatch.setattr(QMenu, "exec_", _exec_and_trigger("删除标签"))
    win.tag_tree.show_context_menu(root_rect.center())
    assert captured_actions["actions"]["删除标签"].isEnabled() is False
    vm.delete_tag.assert_not_called()

    # Tag node: "添加标签" creates child tag under tag id=10
    monkeypatch.setattr(QMenu, "exec_", _exec_and_trigger("添加标签"))
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("SubTag", True))
    win.tag_tree.show_context_menu(tag_rect.center())
    vm.create_tag.assert_called_once_with("SubTag", parent_id=10)

    # Tag node: "删除标签" deletes tag id=10 after confirmation
    monkeypatch.setattr(QMenu, "exec_", _exec_and_trigger("删除标签"))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    win.tag_tree.show_context_menu(tag_rect.center())
    vm.delete_tag.assert_called_once_with(10)

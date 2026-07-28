from unittest.mock import MagicMock
from src.app.model.tag import Tag
from src.app.ui.main_window import MainWindow


def test_sidebar_dynamic_counts(qapp, monkeypatch):
    monkeypatch.setattr('src.app.db.database.Database.connect', MagicMock())
    win = MainWindow()
    win.vm.get_all_tags = MagicMock(return_value=[
        Tag(id=1, tag_name="工作", created_at=0, updated_at=0),
        Tag(id=2, tag_name="生活", created_at=0, updated_at=0),
    ])
    def mock_count_files(tag_id=None):
        if tag_id is None:
            return 15
        elif tag_id == 1:
            return 5
        elif tag_id == 2:
            return 10
        return 0

    win.vm.count_files = MagicMock(side_effect=mock_count_files)
    win._update_tag_tree()

    assert win.tag_tree.topLevelItemCount() == 1
    root = win.tag_tree.topLevelItem(0)
    assert root.text(0) == "所有文件 (15)"
    assert root.childCount() == 2
    assert root.child(0).text(0) == "工作 (5)"
    assert root.child(1).text(0) == "生活 (10)"

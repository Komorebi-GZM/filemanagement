import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


class MockVM:
    def __init__(self):
        self.recent_searches = [
            {"query_json": '{"query": "hello", "timestamp": 1003}'},
            {"query_json": '{"query": "world", "timestamp": 1002}'},
            {"query_json": '{"query": "test", "timestamp": 1001}'},
        ]

    def get_recent_searches(self, limit=10):
        return self.recent_searches

    def get_all_tags(self):
        return []

    def search_files(self, query=""):
        return []


@pytest.fixture
def app():
    qapp = QApplication.instance()
    if not qapp:
        qapp = QApplication([])
    return qapp


def test_command_palette_history(app):
    from src.app.ui.command_palette import CommandPalette

    mock_vm = MockVM()
    cp = CommandPalette(parent=None, vm=mock_vm)
    cp.set_history(mock_vm.get_recent_searches(10))

    assert cp.list_widget.count() == 3
    assert cp.list_widget.item(0).text() == "hello"
    assert cp.list_widget.item(1).text() == "world"
    assert cp.list_widget.item(2).text() == "test"

    cp.search_box.setText("")
    cp._history_index = -1

    # Press Down -> first item
    cp._on_arrow_key(Qt.Key_Down)
    assert cp._history_index == 0
    assert cp.search_box.text() == "hello"

    # Press Down -> second item
    cp._on_arrow_key(Qt.Key_Down)
    assert cp._history_index == 1
    assert cp.search_box.text() == "world"

    # Press Up -> back to first item
    cp._on_arrow_key(Qt.Key_Up)
    assert cp._history_index == 0
    assert cp.search_box.text() == "hello"

    # Test no-op at boundaries
    cp._on_arrow_key(Qt.Key_Up)
    assert cp._history_index == 0
    assert cp.search_box.text() == "hello"

    # Reset with new search input clears history nav
    cp.search_box.setText("new input")
    cp.search_box.textChanged.emit("new input")
    assert cp._history_index == -1


def test_command_palette_context_file_disables_history(app):
    from src.app.ui.command_palette import CommandPalette

    mock_vm = MockVM()
    cp = CommandPalette(parent=None, vm=mock_vm)
    cp.set_context_file(42, "test.txt")

    cp._on_arrow_key(Qt.Key_Down)
    assert cp._history_index == -1


def test_history_wraps_around(app):
    from src.app.ui.command_palette import CommandPalette

    mock_vm = MockVM()
    cp = CommandPalette(parent=None, vm=mock_vm)
    cp.set_history(mock_vm.get_recent_searches(10))
    cp._history_index = -1

    # Down -> first
    cp._on_arrow_key(Qt.Key_Down)
    assert cp._history_index == 0

    # Down -> second
    cp._on_arrow_key(Qt.Key_Down)
    assert cp._history_index == 1

    # Down -> third
    cp._on_arrow_key(Qt.Key_Down)
    assert cp._history_index == 2

    # Down -> wrap to -1 (clear)
    cp._on_arrow_key(Qt.Key_Down)
    assert cp._history_index == -1
    assert cp.search_box.text() == ""

    # Up from cleared -> last item (wrap around)
    cp._on_arrow_key(Qt.Key_Up)
    assert cp._history_index == 2
    assert cp.search_box.text() == "test"


def test_command_palette_live_tag_filtering_and_return_activation(app):
    from src.app.model.tag import Tag
    from src.app.ui.command_palette import CommandPalette

    class TagVM(MockVM):
        def __init__(self):
            super().__init__()
            self.fuzzy_queries = []
            self._tags = [
                Tag(id=1, tag_name="工作文档", created_at=0, updated_at=0),
                Tag(id=2, tag_name="设计稿", created_at=0, updated_at=0),
                Tag(id=3, tag_name="Design Specs", created_at=0, updated_at=0),
            ]

        def get_all_tags(self):
            return list(self._tags)

        def fuzzy_search_tags(self, query=""):
            self.fuzzy_queries.append(query)
            if not query:
                return list(self._tags)
            return [t for t in self._tags if query.lower() in t.tag_name.lower()]

    vm = TagVM()
    cp = CommandPalette(parent=None, vm=vm)
    text_searches = []
    selected_tags = []
    cp.text_entered.connect(text_searches.append)
    cp.tag_selected_for_file.connect(lambda fid, tid: selected_tags.append((fid, tid)))

    cp.set_context_file(7, "notes.txt")
    assert cp.list_widget.count() == 3

    cp.search_box.setText("design")
    assert vm.fuzzy_queries == ["design"]
    assert cp.list_widget.count() == 1
    assert cp.list_widget.item(0).text() == "Design Specs"

    # Pressing Enter in tag mode emits tag_selected_for_file, NOT text_entered
    cp.search_box.returnPressed.emit()
    assert selected_tags == [(7, 3)]
    assert text_searches == []

    # Re-opening clears stale text cleanly without leaking prior query
    cp.set_context_file(8, "other.txt")
    assert cp.search_box.text() == ""
    assert cp.list_widget.count() == 3

    # Fallback works even when VM only implements get_all_tags (no fuzzy_search_tags)
    fallback_vm = MockVM()
    fallback_vm.get_all_tags = lambda: vm.get_all_tags()
    cp2 = CommandPalette(parent=None, vm=fallback_vm)
    cp2.set_context_file(9, "fallback.txt")
    cp2.search_box.setText("设")
    assert [cp2.list_widget.item(i).text() for i in range(cp2.list_widget.count())] == ["设计稿"]

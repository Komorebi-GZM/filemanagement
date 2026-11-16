import pytest
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QHBoxLayout, QLayout
from PyQt5.QtCore import Qt
from src.app.model.file_record import FileRecord
from src.app.model.tag import Tag
from src.app.ui.main_window import MainWindow, TagChipWidget

class MockVM:
    def __init__(self):
        self.tags_removed = []
        self.tags_added = []
    
    def get_all_tags(self): 
        return [Tag(id=101, tag_name="test_tag", created_at=0, updated_at=0, parent_id=None)]

    def get_all_files(self, sort_by=None, sort_order=None): return []
    def get_all_file_extensions(self): return []
    def get_all_drive_letters(self): return []
    def count_files(self, tag_id): return 0
    def list_files(self, file_ext=None, drive_letter=None): return []

    def get_file_tags(self, file_id):
        if file_id == 1:
            return [Tag(id=101, tag_name="test_tag", created_at=0, updated_at=0, parent_id=None)]
        return []
    
    def remove_tag_from_file(self, file_id, tag_id):
        self.tags_removed.append((file_id, tag_id))
        
    def get_recent_searches(self, limit=10):
        return []

    def add_tag_to_file(self, file_id, tag_id):
        self.tags_added.append((file_id, tag_id))

    def get_file_note(self, file_id):
        return ""
        
    def get_file_imprints(self, file_id):
        return []

@pytest.fixture
def app():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app

class MockSignals:
    class MockSignal:
        def connect(self, fn): pass
        def emit(self, *args, **kwargs): pass
    
    def __init__(self):
        self.files_updated = self.MockSignal()
        self.tags_updated = self.MockSignal()
        self.indexing_progress = self.MockSignal()
        self.import_progress = self.MockSignal()
        self.import_finished = self.MockSignal()

def test_inspector_tags(app):
    mock_vm = MockVM()
    mock_signals = MockSignals()
    main_window = MainWindow(vm=mock_vm, signals=mock_signals)
    
    # Fake file
    file = FileRecord(id=1, file_name="test.txt", full_path="/test.txt", file_size=10, modify_time="2023-01-01 10:00:00", file_hash="abc", created_at="2023-01-01 10:00:00", updated_at="2023-01-01 10:00:00")
    
    # 1. _load_file_preview creates tag widgets with x buttons
    main_window._load_file_preview(file)
    
    assert hasattr(main_window, 'tags_container')
    layout = main_window.tags_container.layout()
    assert layout is not None
    
    # Find buttons
    x_button = None
    plus_button = None
    
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget():
            w = item.widget()
            if isinstance(w, QPushButton) and w.text() == "+":
                plus_button = w
            elif isinstance(w, TagChipWidget):
                x_button = w.remove_btn
                        
    assert x_button is not None, "x button not found"
    assert plus_button is not None, "+ button not found"
    
    # 2. Clicking x calls remove_file_tag
    x_button.click()
    assert (1, 101) in mock_vm.tags_removed
    
    # 3. Clicking + toggles real command palette
    plus_button.click()
    assert main_window.command_palette.context_file_id == 1
    assert main_window.command_palette.search_box.placeholderText() == "为文件 test.txt 添加标签..."
    assert main_window.command_palette.isHidden() == False
    
    # Verify tags are populated
    list_widget = main_window.command_palette.list_widget
    assert list_widget.count() == 1
    item = list_widget.item(0)
    assert item.text() == "test_tag"
    assert item.data(Qt.UserRole) == 101
    
    # Verify emitting tag selection
    main_window.command_palette.list_widget.itemActivated.emit(item)
    assert (1, 101) in mock_vm.tags_added
    assert main_window.command_palette.isHidden() == True
    
    # Verify closing it clears state
    main_window.command_palette.show()
    main_window.command_palette.hide()
    assert main_window.command_palette.context_file_id is None
    assert main_window.command_palette.search_box.placeholderText() == "搜索命令..."

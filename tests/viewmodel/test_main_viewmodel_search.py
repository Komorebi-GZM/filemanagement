from unittest.mock import MagicMock
from src.app.viewmodel.main_viewmodel import MainViewModel
from src.app.model.tag import Tag


def test_fuzzy_search_tags():
    vm = MainViewModel()
    vm.db = MagicMock()
    # Mock db to return some tags
    vm.db.get_all_tags.return_value = [Tag(1, "工作", 0, 0), Tag(2, "设计", 0, 0)]
    results = vm.fuzzy_search_tags("设")
    assert len(results) == 1
    assert results[0].tag_name == "设计"


def test_fuzzy_search_tags_empty_query():
    vm = MainViewModel()
    vm.db = MagicMock()
    tags = [Tag(1, "工作", 0, 0), Tag(2, "设计", 0, 0)]
    vm.db.get_all_tags.return_value = tags
    results = vm.fuzzy_search_tags("")
    assert len(results) == 2
    assert results == tags


def test_fuzzy_search_tags_case_insensitive():
    vm = MainViewModel()
    vm.db = MagicMock()
    tags = [Tag(1, "Python", 0, 0), Tag(2, "Java", 0, 0)]
    vm.db.get_all_tags.return_value = tags
    results = vm.fuzzy_search_tags("python")
    assert len(results) == 1
    assert results[0].tag_name == "Python"


def test_fuzzy_search_tags_no_match():
    vm = MainViewModel()
    vm.db = MagicMock()
    tags = [Tag(1, "工作", 0, 0), Tag(2, "设计", 0, 0)]
    vm.db.get_all_tags.return_value = tags
    results = vm.fuzzy_search_tags("测试")
    assert len(results) == 0

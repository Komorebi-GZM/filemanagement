from unittest.mock import MagicMock
from src.app.viewmodel.main_viewmodel import MainViewModel
from src.app.model.tag import Tag


def test_fuzzy_search_tags():
    vm = MainViewModel()
    vm.get_all_tags = MagicMock(return_value=[Tag(1, "工作", 0, 0), Tag(2, "设计", 0, 0)])
    results = vm.fuzzy_search_tags("设")
    assert len(results) == 1
    assert results[0].tag_name == "设计"


def test_fuzzy_search_tags_empty_query():
    vm = MainViewModel()
    tags = [Tag(1, "工作", 0, 0), Tag(2, "设计", 0, 0)]
    vm.get_all_tags = MagicMock(return_value=tags)
    results = vm.fuzzy_search_tags("")
    assert len(results) == 2
    assert results == tags


def test_fuzzy_search_tags_case_insensitive():
    vm = MainViewModel()
    tags = [Tag(1, "Python", 0, 0), Tag(2, "Java", 0, 0)]
    vm.get_all_tags = MagicMock(return_value=tags)
    results = vm.fuzzy_search_tags("python")
    assert len(results) == 1
    assert results[0].tag_name == "Python"


def test_fuzzy_search_tags_no_match():
    vm = MainViewModel()
    tags = [Tag(1, "工作", 0, 0), Tag(2, "设计", 0, 0)]
    vm.get_all_tags = MagicMock(return_value=tags)
    results = vm.fuzzy_search_tags("测试")
    assert len(results) == 0


def test_fuzzy_search_tags_none_tag_name():
    vm = MainViewModel()
    tags = [Tag(1, None, 0, 0), Tag(2, "设计", 0, 0)]
    vm.get_all_tags = MagicMock(return_value=tags)
    results = vm.fuzzy_search_tags("设")
    assert len(results) == 1
    assert results[0].tag_name == "设计"


def test_fuzzy_search_tags_db_none():
    vm = MainViewModel()
    results = vm.fuzzy_search_tags("设")
    assert results == []

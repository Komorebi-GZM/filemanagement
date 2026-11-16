from unittest.mock import MagicMock
import pytest
from src.app.db.database import Database
from src.app.viewmodel.main_viewmodel import MainViewModel


def test_count_files_without_db():
    vm = MainViewModel(db=None)
    assert vm.count_files(None) == 0
    assert vm.count_files(1) == 0


def test_count_files_with_db(db_session):
    # Setup test data in SQLite database
    db_session.execute(
        """
        INSERT INTO files (id, file_name, file_ext, full_path, file_size, create_time, modify_time, file_hash, is_deleted, created_at, updated_at)
        VALUES 
            (1, 'doc1.txt', 'txt', '/path/doc1.txt', 100, 0, 0, 'hash1', 0, 0, 0),
            (2, 'doc2.pdf', 'pdf', '/path/doc2.pdf', 200, 0, 0, 'hash2', 0, 0, 0),
            (3, 'doc3.png', 'png', '/path/doc3.png', 300, 0, 0, 'hash3', 1, 0, 0)
        """
    )
    db_session.execute(
        """
        INSERT INTO tags (id, tag_name, created_at, updated_at)
        VALUES 
            (10, 'Work', 0, 0),
            (20, 'Personal', 0, 0)
        """
    )
    db_session.execute(
        """
        INSERT INTO file_tag_relation (file_id, tag_id, created_at)
        VALUES 
            (1, 10, 0),
            (2, 10, 0),
            (3, 10, 0),
            (2, 20, 0)
        """
    )

    db = Database(":memory:")
    # Override connect to return the active test db_session
    db.connect = MagicMock(return_value=db_session)
    
    vm = MainViewModel(db=db)

    # All non-deleted files count (doc1 and doc2, doc3 is deleted)
    assert vm.count_files(None) == 2

    # Tag 10 has doc1, doc2, doc3 attached, but doc3 is deleted -> count 2
    assert vm.count_files(10) == 2

    # Tag 20 has doc2 attached -> count 1
    assert vm.count_files(20) == 1

    # Nonexistent tag -> count 0
    assert vm.count_files(999) == 0


def test_get_all_drive_letters_sql_and_soft_delete_signal(db_session):
    from src.app.viewmodel.signals import MainSignals

    db_session.execute(
        """
        INSERT INTO files (id, file_name, file_ext, full_path, file_size, create_time, modify_time, file_hash, is_deleted, created_at, updated_at)
        VALUES
            (1, 'a.txt', 'txt', 'D:\\work\\a.txt', 100, 0, 0, 'h1', 0, 0, 0),
            (2, 'b.txt', 'txt', 'C:\\docs\\b.txt', 100, 0, 0, 'h2', 0, 0, 0),
            (3, 'c.txt', 'txt', 'E:\\old\\c.txt', 100, 0, 0, 'h3', 1, 0, 0),
            (4, 'd.txt', 'txt', '/home/user/d.txt', 100, 0, 0, 'h4', 0, 0, 0),
            (5, 'e.txt', 'txt', '1:\\invalid\\e.txt', 100, 0, 0, 'h5', 0, 0, 0)
        """
    )

    db = Database(":memory:")
    db.connect = MagicMock(return_value=db_session)
    signals = MainSignals()
    vm = MainViewModel(db=db, signals=signals)

    assert vm.get_all_drive_letters() == ["C:", "D:"]
    assert MainViewModel(db=None).get_all_drive_letters() == []

    received = []
    signals.files_updated.connect(received.append)
    vm.soft_delete_file(1)
    assert received == [None]
    assert vm.get_all_drive_letters() == ["C:"]

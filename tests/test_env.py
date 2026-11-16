import sys


def test_python_version():
    assert sys.version_info.major == 3
    assert sys.version_info >= (3, 11)


def test_db_session_fixture(db_session):
    cursor = db_session.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    assert "files" in tables
    assert "tags" in tables
    assert "file_tag_relation" in tables

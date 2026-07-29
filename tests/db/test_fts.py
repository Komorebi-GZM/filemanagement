import pytest
from src.app.db.database import Database


class TestFTS:
    def test_create_fts_table(self, db_session):
        db = Database(":memory:")
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (id INTEGER PRIMARY KEY, file_name TEXT);
        """)
        db.create_fts_table(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='file_fts'"
        ).fetchall()
        assert len(rows) == 1

    def test_upsert_and_search(self, db_session):
        db = Database(":memory:")
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY, file_name TEXT, full_path TEXT,
                file_ext TEXT, file_size INTEGER, modify_time INTEGER,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.execute("INSERT INTO files (id, file_name) VALUES (1, 'report.txt')")
        db.create_fts_table(conn)
        db.upsert_fts(conn, file_id=1, file_name="report.txt", content="quarterly budget review")
        results = db.search_fts(conn, "budget", limit=10)
        assert len(results) == 1
        assert results[0]["file_id"] == 1

    def test_search_returns_file_name_matches(self, db_session):
        db = Database(":memory:")
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY, file_name TEXT, full_path TEXT,
                file_ext TEXT, file_size INTEGER, modify_time INTEGER,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.execute("INSERT INTO files (id, file_name) VALUES (1, 'budget_2024.xlsx')")
        db.create_fts_table(conn)
        db.upsert_fts(conn, file_id=1, file_name="budget_2024.xlsx", content="annual figures")
        results = db.search_fts(conn, "budget", limit=10)
        assert len(results) == 1

    def test_update_replaces_content(self, db_session):
        db = Database(":memory:")
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY, file_name TEXT, full_path TEXT,
                file_ext TEXT, file_size INTEGER, modify_time INTEGER,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.execute("INSERT INTO files (id, file_name) VALUES (1, 'doc.txt')")
        db.create_fts_table(conn)
        db.upsert_fts(conn, 1, "doc.txt", "alpha beta")
        db.upsert_fts(conn, 1, "doc.txt", "gamma delta")
        results = db.search_fts(conn, "gamma", limit=10)
        assert len(results) == 1
        results = db.search_fts(conn, "alpha", limit=10)
        assert len(results) == 0

    def test_delete(self, db_session):
        db = Database(":memory:")
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY, file_name TEXT, full_path TEXT,
                file_ext TEXT, file_size INTEGER, modify_time INTEGER,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.execute("INSERT INTO files (id, file_name) VALUES (1, 'doc.txt')")
        db.create_fts_table(conn)
        db.upsert_fts(conn, 1, "doc.txt", "hello world")
        db.delete_fts(conn, 1)
        results = db.search_fts(conn, "hello", limit=10)
        assert len(results) == 0

    def test_bm25_ranking(self, db_session):
        db = Database(":memory:")
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY, file_name TEXT, full_path TEXT,
                file_ext TEXT, file_size INTEGER, modify_time INTEGER,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.execute("INSERT INTO files (id, file_name) VALUES (1, 'budget_2024.xlsx')")
        conn.execute("INSERT INTO files (id, file_name) VALUES (2, 'notes.txt')")
        db.create_fts_table(conn)
        db.upsert_fts(conn, 1, "budget_2024.xlsx", "some figures")
        db.upsert_fts(conn, 2, "notes.txt", "the budget meeting was canceled")
        results = db.search_fts(conn, "budget", limit=10)
        assert len(results) == 2
        assert results[0]["file_id"] == 1  # name match ranks higher

    def test_content_status_created(self, db_session):
        db = Database(":memory:")
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (id INTEGER PRIMARY KEY, file_name TEXT);
        """)
        db.create_fts_table(conn)
        conn.execute("INSERT INTO files (id, file_name) VALUES (1, 'test.txt')")
        db.upsert_fts(conn, 1, "test.txt", "content")
        row = conn.execute(
            "SELECT status FROM file_content_status WHERE file_id = 1"
        ).fetchone()
        assert row is not None
        assert row["status"] == "indexed"

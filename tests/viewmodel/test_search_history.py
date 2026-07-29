import json
import pathlib
import tempfile
import pytest
from src.app.db.database import Database, apply_schema, load_schema_text
from src.app.viewmodel.main_viewmodel import MainViewModel
from src.app.viewmodel.signals import MainSignals


class TestSearchHistory:
    def _make_db(self):
        """Create a fresh database with schema loaded."""
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tf.name
        tf.close()
        db = Database(db_path)
        schema_path = pathlib.Path(__file__).parents[2] / "src" / "app" / "db" / "schema.sql"
        conn = db.connect()
        apply_schema(conn, load_schema_text(schema_path))
        conn.close()
        return db

    def test_record_and_retrieve(self):
        db = self._make_db()
        db.record_search(json.dumps({"query": "test"}), 1000)
        db.record_search(json.dumps({"query": "hello"}), 1001)

        results = db.get_recent_searches(10)
        assert len(results) == 2
        # Most recent first (DESC order)
        assert results[0]["query_json"] == json.dumps({"query": "hello"})
        assert results[1]["query_json"] == json.dumps({"query": "test"})

    def test_limit(self):
        db = self._make_db()
        for i in range(60):
            db.record_search(json.dumps({"query": f"q{i}"}), 1000 + i)
        db.delete_old_searches(50)
        results = db.get_recent_searches(100)
        assert len(results) <= 50

    def test_empty_history(self):
        db = self._make_db()
        results = db.get_recent_searches(10)
        assert results == []

    def test_find_by_hash_existing(self):
        db = self._make_db()
        # Insert a file manually
        conn = db.connect()
        conn.execute(
            """INSERT INTO files (file_name, file_ext, full_path, file_size, file_hash,
               create_time, modify_time, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("test.txt", "txt", "/path/test.txt", 100, "abc123",
             1000, 1000, 1000, 1000),
        )
        conn.commit()
        conn.close()

        result = db.find_by_hash("abc123")
        assert result is not None
        assert result["file_name"] == "test.txt"
        assert result["full_path"] == "/path/test.txt"

    def test_find_by_hash_missing(self):
        db = self._make_db()
        result = db.find_by_hash("nonexistent")
        assert result is None

    def test_find_by_path_and_size(self):
        db = self._make_db()
        conn = db.connect()
        conn.execute(
            """INSERT INTO files (file_name, file_ext, full_path, file_size, file_hash,
               create_time, modify_time, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("found.txt", "txt", "/path/found.txt", 500, "def456",
             1000, 1000, 1000, 1000),
        )
        conn.commit()
        conn.close()

        file_id = db.find_by_path_and_size("/path/found.txt", 500)
        assert file_id is not None

        missing = db.find_by_path_and_size("/path/found.txt", 999)
        assert missing is None

    def test_update_file_path(self):
        db = self._make_db()
        conn = db.connect()
        conn.execute(
            """INSERT INTO files (file_name, file_ext, full_path, file_size, file_hash,
               create_time, modify_time, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("old.txt", "txt", "/path/old.txt", 100, "ghi789",
             1000, 1000, 1000, 1000),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM files WHERE file_hash = ?", ("ghi789",)).fetchone()
        file_id = row["id"]
        conn.close()

        db.update_file_path(file_id, "/path/new.txt", "new.txt", "txt")

        conn = db.connect()
        row = conn.execute("SELECT full_path, file_name FROM files WHERE id = ?", (file_id,)).fetchone()
        assert row["full_path"] == "/path/new.txt"
        assert row["file_name"] == "new.txt"
        conn.close()

    def test_soft_delete_by_hash(self):
        db = self._make_db()
        conn = db.connect()
        conn.execute(
            """INSERT INTO files (file_name, file_ext, full_path, file_size, file_hash,
               create_time, modify_time, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("del.txt", "txt", "/path/del.txt", 100, "jkl012",
             1000, 1000, 1000, 1000),
        )
        conn.commit()
        conn.close()

        db.soft_delete_by_hash("jkl012")

        conn = db.connect()
        row = conn.execute("SELECT is_deleted FROM files WHERE file_hash = ?", ("jkl012",)).fetchone()
        assert row["is_deleted"] == 1
        conn.close()

    def test_update_file_meta(self):
        db = self._make_db()
        conn = db.connect()
        conn.execute(
            """INSERT INTO files (file_name, file_ext, full_path, file_size, file_hash,
               create_time, modify_time, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("meta.txt", "txt", "/path/meta.txt", 100, "mno345",
             1000, 1000, 1000, 1000),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM files WHERE file_hash = ?", ("mno345",)).fetchone()
        file_id = row["id"]
        conn.close()

        db.update_file_meta(file_id, 999, 2000)

        conn = db.connect()
        row = conn.execute("SELECT file_size, modify_time FROM files WHERE id = ?", (file_id,)).fetchone()
        assert row["file_size"] == 999
        assert row["modify_time"] == 2000
        conn.close()


class TestViewModelSearchHistory:
    def test_search_writes_history(self, vm):
        vm.search_files(query="test_query")
        history = vm.get_recent_searches(limit=10)
        assert len(history) >= 1
        assert "test_query" in history[0]["query_json"]

    def test_search_without_query_does_not_write(self, vm):
        vm.search_files(query="")
        history = vm.get_recent_searches(limit=10)
        assert len(history) == 0

    def test_auto_cleanup(self, vm):
        for i in range(60):
            vm.record_search(f"q{i}")
        history = vm.get_recent_searches(limit=100)
        assert len(history) <= 50

    @pytest.fixture
    def vm(self):
        import tempfile
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tf.name
        tf.close()
        db = Database(db_path)
        schema_path = pathlib.Path(__file__).parents[2] / "src" / "app" / "db" / "schema.sql"
        conn = db.connect()
        apply_schema(conn, load_schema_text(schema_path))
        conn.close()
        v = MainViewModel(db=db, signals=MainSignals())
        return v

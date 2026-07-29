import pathlib
import tempfile
import pytest
from pathlib import Path
from src.app.db.database import Database, apply_schema, load_schema_text
from src.app.viewmodel.main_viewmodel import MainViewModel, ImportCandidate
from src.app.viewmodel.signals import MainSignals


class TestFtsSearch:
    @pytest.fixture
    def vm_with_fts(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tf.name
        tf.close()
        db = Database(db_path)
        schema_path = pathlib.Path(__file__).parents[2] / "src" / "app" / "db" / "schema.sql"
        conn = db.connect()
        apply_schema(conn, load_schema_text(schema_path))
        conn.close()
        vm_inst = MainViewModel(db=db, signals=MainSignals())
        yield vm_inst

    def test_search_by_content(self, vm_with_fts):
        vm = vm_with_fts
        conn = vm.db.connect()
        conn.execute(
            "INSERT INTO files (id, file_name, file_ext, full_path, file_size, file_hash, created_at, updated_at) "
            "VALUES (1, 'report.txt', 'txt', '/report.txt', 100, 'hash1', 0, 0)"
        )
        conn.commit()
        vm.db.upsert_fts(conn, 1, "report.txt", "quarterly budget review 2024")
        conn.commit()
        conn.close()
        results = vm.search_files("budget")
        assert len(results) >= 1
        assert results[0].file_name == "report.txt"

    def test_search_by_file_name_still_works(self, vm_with_fts):
        vm = vm_with_fts
        conn = vm.db.connect()
        conn.execute(
            "INSERT INTO files (id, file_name, file_ext, full_path, file_size, file_hash, created_at, updated_at) "
            "VALUES (1, 'budget_2024.xlsx', 'xlsx', '/budget_2024.xlsx', 200, 'hash2', 0, 0)"
        )
        conn.commit()
        vm.db.upsert_fts(conn, 1, "budget_2024.xlsx", "annual figures")
        conn.commit()
        conn.close()
        results = vm.search_files("budget")
        assert len(results) >= 1

    def test_search_merges_fts_and_like_without_duplicates(self, vm_with_fts):
        vm = vm_with_fts
        conn = vm.db.connect()
        conn.execute(
            "INSERT INTO files (id, file_name, file_ext, full_path, file_size, file_hash, created_at, updated_at) "
            "VALUES (1, 'budget.txt', 'txt', '/budget.txt', 100, 'h1', 0, 0)"
        )
        conn.execute(
            "INSERT INTO files (id, file_name, file_ext, full_path, file_size, file_hash, created_at, updated_at) "
            "VALUES (2, 'my_budget_notes.txt', 'txt', '/my_budget_notes.txt', 100, 'h2', 0, 0)"
        )
        conn.commit()
        vm.db.upsert_fts(conn, 1, "budget.txt", "budget planning")
        vm.db.upsert_fts(conn, 2, "my_budget_notes.txt", "meeting notes")
        conn.commit()
        conn.close()
        results = vm.search_files("budget")
        assert len(results) == 2
        assert results[0].file_name == "budget.txt"

    def test_search_writes_to_history(self, vm_with_fts):
        vm = vm_with_fts
        conn = vm.db.connect()
        conn.execute(
            "INSERT INTO files (id, file_name, file_ext, full_path, file_size, file_hash, created_at, updated_at) "
            "VALUES (1, 'doc.txt', 'txt', '/doc.txt', 100, 'h3', 0, 0)"
        )
        conn.commit()
        vm.db.upsert_fts(conn, 1, "doc.txt", "some content")
        conn.commit()
        conn.close()
        vm.search_files("content")
        history = vm.get_recent_searches(limit=5)
        assert len(history) >= 1

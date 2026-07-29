import pathlib
import tempfile
import time
import pytest
from pathlib import Path
from src.app.db.database import Database, apply_schema, load_schema_text
from src.app.viewmodel.main_viewmodel import MainViewModel, ImportCandidate
from src.app.viewmodel.signals import MainSignals
from src.app.services.file_monitor import FileEvent


@pytest.fixture
def vm():
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


class TestFileSync:
    def test_handle_file_moved_updates_path(self, vm, tmp_path):
        src = tmp_path / "old.txt"
        src.write_text("hello")
        candidates = [ImportCandidate(path=src, size=src.stat().st_size)]
        vm.import_files(candidates)
        time.sleep(0.5)
        records = vm.list_files()
        assert len(records) == 1
        file_hash = records[0].file_hash

        dest = tmp_path / "new.txt"
        src.rename(dest)
        vm._handle_file_moved(file_hash, str(dest.resolve()))

        updated = vm.get_file_by_id(records[0].id)
        assert updated is not None
        assert updated.full_path == str(dest.resolve())
        assert updated.file_name == "new.txt"

    def test_handle_file_deleted_soft_deletes(self, vm, tmp_path):
        f = tmp_path / "del.txt"
        f.write_text("delete me")
        candidates = [ImportCandidate(path=f, size=f.stat().st_size)]
        vm.import_files(candidates)
        time.sleep(0.5)
        file_hash = vm.list_files()[0].file_hash

        vm._handle_file_deleted_by_path(str(f.resolve()))
        assert len(vm.list_files()) == 0

    def test_handle_file_modified_updates_size(self, vm, tmp_path):
        f = tmp_path / "mod.txt"
        f.write_text("v1")
        candidates = [ImportCandidate(path=f, size=f.stat().st_size)]
        vm.import_files(candidates)
        time.sleep(0.5)
        records = vm.list_files()
        file_hash = records[0].file_hash
        old_size = records[0].file_size

        f.write_text("v2 with more content")
        new_size = f.stat().st_size
        assert new_size != old_size

        vm._handle_file_modified(records[0].id, new_size, int(f.stat().st_mtime))

        updated = vm.get_file_by_id(records[0].id)
        assert updated is not None
        assert updated.file_size == new_size

    def test_batch_processing_dispatches_correctly(self, vm, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("aaa")
        f2.write_text("bbb")
        candidates = [
            ImportCandidate(path=f1, size=f1.stat().st_size),
            ImportCandidate(path=f2, size=f2.stat().st_size),
        ]
        vm.import_files(candidates)
        time.sleep(0.5)
        records = {r.file_name: r for r in vm.list_files()}

        events = [
            FileEvent(event_type="modified", src_path=str(f1), dest_path="",
                      file_hash=records["a.txt"].file_hash, is_directory=False),
            FileEvent(event_type="deleted", src_path=str(f2), dest_path="",
                      file_hash=records["b.txt"].file_hash, is_directory=False),
        ]

        vm._on_file_system_changed(events)
        remaining = {r.file_name for r in vm.list_files()}
        assert "b.txt" not in remaining

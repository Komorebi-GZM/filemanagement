import time
import unicodedata
from pathlib import Path

from src.app.core.path_utils import normalize_path
from src.app.db.database import Database, apply_schema, load_schema_text
from src.app.services.file_monitor import FileEvent
from src.app.viewmodel.main_viewmodel import MainViewModel
from src.app.viewmodel.signals import MainSignals


def _create_vm_with_file(tmp_path, file_name, file_size=100, modify_time=1000):
    db_file = str(tmp_path / "test.db")
    db = Database(db_file)
    schema_path = Path(__file__).parents[2] / "src" / "app" / "db" / "schema.sql"
    with db.connect() as conn:
        apply_schema(conn, load_schema_text(schema_path))
    signals = MainSignals()
    vm = MainViewModel(db=db, signals=signals)

    p = tmp_path / file_name
    norm_path = normalize_path(p)
    now = int(time.time())

    with db.connect() as conn:
        conn.execute(
            """INSERT INTO files (file_name, file_ext, full_path, file_size,
               create_time, modify_time, file_hash, is_deleted, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (p.name, p.suffix.lstrip("."), norm_path, file_size, now, modify_time, f"hash_{file_name}", now, now),
        )
    return vm, db, norm_path


def test_deleted_event_matches_nfd_unicode_path(tmp_path):
    nfd_name = unicodedata.normalize("NFD", "café_测试.txt")
    nfc_name = unicodedata.normalize("NFC", "café_测试.txt")

    vm, db, norm_path = _create_vm_with_file(tmp_path, nfc_name)

    nfd_path = str(tmp_path / nfd_name)
    event = FileEvent(event_type="deleted", src_path=nfd_path, dest_path="", file_hash="", is_directory=False)
    vm._on_file_system_changed([event])

    with db.connect() as conn:
        row = conn.execute("SELECT is_deleted FROM files WHERE full_path = ?", (norm_path,)).fetchone()
        assert row is not None
        assert row["is_deleted"] == 1


def test_deleted_event_matches_symlink_alias(tmp_path):
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    real_file = real_dir / "target.txt"
    real_file.write_text("hello", encoding="utf-8")

    link_dir = tmp_path / "link_dir"
    link_dir.symlink_to(real_dir)
    link_file = link_dir / "target.txt"

    vm, db, norm_path = _create_vm_with_file(tmp_path, "real_dir/target.txt")

    event = FileEvent(event_type="deleted", src_path=str(link_file), dest_path="", file_hash="", is_directory=False)
    vm._on_file_system_changed([event])

    with db.connect() as conn:
        row = conn.execute("SELECT is_deleted FROM files WHERE full_path = ?", (norm_path,)).fetchone()
        assert row is not None
        assert row["is_deleted"] == 1


def test_modified_event_case_insensitive_fallback(tmp_path):
    vm, db, norm_path = _create_vm_with_file(tmp_path, "CaseTest.txt", file_size=50, modify_time=100)

    # File on disk with different case
    disk_file = tmp_path / "casetest.txt"
    disk_file.write_bytes(b"x" * 80)

    # find_by_path_and_size should match case-insensitively
    file_id = db.find_by_path_and_size(str(disk_file), 50)
    assert file_id is not None

    event = FileEvent(event_type="modified", src_path=str(disk_file), dest_path="", file_hash="", is_directory=False)
    vm._on_file_system_changed([event])

    with db.connect() as conn:
        row = conn.execute("SELECT file_size FROM files WHERE id = ?", (file_id,)).fetchone()
        assert row["file_size"] == 80


def test_moved_event_stores_normalized_path(tmp_path):
    vm, db, norm_path = _create_vm_with_file(tmp_path, "original.txt")

    real_dest_dir = tmp_path / "dest_real"
    real_dest_dir.mkdir()
    link_dest_dir = tmp_path / "dest_link"
    link_dest_dir.symlink_to(real_dest_dir)

    dest_file = link_dest_dir / "new_name.txt"
    dest_file.write_text("dest content", encoding="utf-8")

    # Mock find_by_hash to find original
    with db.connect() as conn:
        row = conn.execute("SELECT file_hash FROM files WHERE full_path = ?", (norm_path,)).fetchone()
        file_hash = row["file_hash"]

    updated_id = vm._handle_file_moved(file_hash, str(dest_file))
    assert updated_id is not None

    with db.connect() as conn:
        updated_row = conn.execute("SELECT full_path FROM files WHERE id = ?", (updated_id,)).fetchone()
        # Must be resolved (not containing dest_link) and normalized NFC
        expected = normalize_path(dest_file)
        assert updated_row["full_path"] == expected
        assert "dest_link" not in updated_row["full_path"]

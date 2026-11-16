import time
from pathlib import Path

from src.app.core.path_utils import normalize_path
from src.app.db.database import Database, apply_schema, load_schema_text
from src.app.viewmodel.main_viewmodel import MainViewModel
from src.app.viewmodel.signals import MainSignals


def _setup_vm(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_file)
    schema_path = Path(__file__).parents[2] / "src" / "app" / "db" / "schema.sql"
    with db.connect() as conn:
        apply_schema(conn, load_schema_text(schema_path))
    signals = MainSignals()
    return MainViewModel(db=db, signals=signals), db


def _insert_file(db, name, path, is_deleted=0):
    now = int(time.time())
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO files (file_name, file_ext, full_path, file_size,
               create_time, modify_time, file_hash, is_deleted, created_at, updated_at)
               VALUES (?, 'txt', ?, 10, ?, ?, ?, ?, ?, ?)""",
            (name, path, now, now, f"hash_{name}_{path}", is_deleted, now, now),
        )


def test_get_all_locations_mixed_and_deleted(tmp_path):
    vm, db = _setup_vm(tmp_path)
    _insert_file(db, "1.txt", "/Users/a/1.txt")
    _insert_file(db, "2.txt", "/Volumes/USB/2.txt")
    _insert_file(db, "3.txt", "/Volumes/USB2/3.txt")
    _insert_file(db, "4.txt", r"C:\a\4.txt")
    _insert_file(db, "5.txt", r"d:\b\5.txt")
    _insert_file(db, "6.txt", "/Volumes/Old/6.txt", is_deleted=1)

    locations = vm.get_all_locations()
    labels = [label for label, key in locations]
    keys = [key for label, key in locations]

    assert "Old" not in labels
    assert "Macintosh HD" in labels
    assert "/" in keys
    assert "USB" in labels
    assert "/Volumes/USB" in keys
    assert "USB2" in labels
    assert "/Volumes/USB2" in keys
    assert "C:" in labels
    assert "D:" in labels


def test_list_files_filter_macos_root_excludes_volumes(tmp_path):
    vm, db = _setup_vm(tmp_path)
    _insert_file(db, "root.txt", "/Users/a/root.txt")
    _insert_file(db, "vol.txt", "/Volumes/USB/vol.txt")

    files = vm.list_files(location="/")
    names = [f.file_name for f in files]
    assert names == ["root.txt"]


def test_list_files_filter_volume_boundary(tmp_path):
    vm, db = _setup_vm(tmp_path)
    _insert_file(db, "usb.txt", "/Volumes/USB/file.txt")
    _insert_file(db, "usb2.txt", "/Volumes/USB2/file.txt")

    files = vm.list_files(location="/Volumes/USB")
    names = [f.file_name for f in files]
    assert names == ["usb.txt"]


def test_list_files_filter_like_special_chars(tmp_path):
    vm, db = _setup_vm(tmp_path)
    _insert_file(db, "special.txt", "/Volumes/100%_Disk/special.txt")
    _insert_file(db, "other.txt", "/Volumes/1000Disk/other.txt")

    files = vm.list_files(location="/Volumes/100%_Disk")
    names = [f.file_name for f in files]
    assert names == ["special.txt"]


def test_list_files_windows_drive_case_insensitive(tmp_path):
    vm, db = _setup_vm(tmp_path)
    _insert_file(db, "a.txt", r"c:\work\a.txt")
    _insert_file(db, "b.txt", r"C:\work\b.txt")

    # Filter with location="C:"
    files_by_loc = vm.list_files(location="C:")
    assert {f.file_name for f in files_by_loc} == {"a.txt", "b.txt"}

    # Filter with legacy drive_letter="c:"
    files_by_drive = vm.list_files(drive_letter="c:")
    assert {f.file_name for f in files_by_drive} == {"a.txt", "b.txt"}

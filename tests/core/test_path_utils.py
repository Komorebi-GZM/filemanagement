import unicodedata
from pathlib import Path

from src.app.core.path_utils import normalize_path, extract_location, escape_like


def test_normalize_path_unicode_nfc():
    nfd_text = unicodedata.normalize("NFD", "café_设计稿.txt")
    assert not unicodedata.is_normalized("NFC", nfd_text)
    norm = normalize_path(f"/tmp/{nfd_text}")
    assert unicodedata.is_normalized("NFC", norm)
    assert "café_设计稿.txt" in norm


def test_normalize_path_symlink_resolution(tmp_path):
    target = tmp_path / "real_dir" / "file.txt"
    target.parent.mkdir()
    target.write_text("content", encoding="utf-8")

    link_dir = tmp_path / "link_dir"
    link_dir.symlink_to(tmp_path / "real_dir")
    link_file = link_dir / "file.txt"

    norm_target = normalize_path(target)
    norm_link = normalize_path(link_file)
    assert norm_target == norm_link


def test_normalize_path_windows_drive_upper():
    assert normalize_path("c:/Docs/a.txt") == "C:/Docs/a.txt"
    assert normalize_path(r"d:\work\sub\file.txt") == r"D:\work\sub\file.txt"
    assert normalize_path("E:/data") == "E:/data"


def test_extract_location_windows_drives():
    assert extract_location(r"C:\a.txt") == ("C:", "C:")
    assert extract_location("d:/work/b.md") == ("D:", "D:")
    assert extract_location("e:/") == ("E:", "E:")


def test_extract_location_macos_volumes():
    assert extract_location("/Volumes/Backup/2026/a.pdf") == ("Backup", "/Volumes/Backup")
    assert extract_location("/Volumes/USB2/x.txt") == ("USB2", "/Volumes/USB2")
    assert extract_location("/Volumes/My Disk") == ("My Disk", "/Volumes/My Disk")


def test_extract_location_macos_root():
    assert extract_location("/Users/alice/Desktop/note.md") == ("Macintosh HD", "/")
    assert extract_location("/tmp/a.txt") == ("Macintosh HD", "/")
    assert extract_location("/var/log/system.log") == ("Macintosh HD", "/")
    assert extract_location("/System/Volumes/Data/Users/bob/doc.txt") == ("Macintosh HD", "/")


def test_extract_location_invalid_or_empty():
    assert extract_location("") is None
    assert extract_location("relative/path.txt") is None
    assert extract_location("   ") is None


def test_escape_like():
    assert escape_like("abc") == "abc"
    assert escape_like("100%_Disk") == r"100\%\_Disk"
    assert escape_like(r"C:\test") == r"C:\\test"

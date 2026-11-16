import pytest
from pathlib import Path
from PyQt5.QtCore import QTimer
from src.app.services.file_monitor import FileEvent, FileMonitor


class TestFileEvent:
    def test_file_event_creation(self):
        event = FileEvent(
            event_type="moved",
            src_path="/old/path.txt",
            dest_path="/new/path.txt",
            file_hash="abc123",
            is_directory=False,
        )
        assert event.event_type == "moved"
        assert event.src_path == "/old/path.txt"
        assert event.dest_path == "/new/path.txt"
        assert event.file_hash == "abc123"
        assert not event.is_directory


class TestFileMonitor:
    @pytest.fixture
    def monitor(self, qtbot):
        m = FileMonitor(debounce_ms=50)
        yield m
        m.stop()

    def test_initial_state(self, monitor):
        assert not monitor.is_running()
        assert monitor._debounce_ms == 50
        assert monitor._pending == {}

    def test_start_stop(self, monitor, tmp_path):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        monitor.start([watch_dir])
        assert monitor.is_running()
        monitor.stop()
        assert not monitor.is_running()

    def test_debounce_merges_same_file(self, monitor, tmp_path, qtbot):
        collected = []
        monitor.file_system_changed.connect(collected.append)
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        monitor.start([watch_dir])
        test_file = watch_dir / "test.txt"
        test_file.write_text("v1")
        test_file.write_text("v2")

        def check():
            return len(collected) > 0

        qtbot.waitUntil(check, timeout=5000)
        monitor.stop()
        assert len(collected) == 1
        assert len(collected[0]) == 1

    def test_debounce_separates_different_files(self, monitor, tmp_path, qtbot):
        collected = []
        monitor.file_system_changed.connect(collected.append)
        watch_dir = tmp_path / "watch2"
        watch_dir.mkdir()
        monitor.start([watch_dir])
        (watch_dir / "a.txt").write_text("a")
        (watch_dir / "b.txt").write_text("b")

        def check():
            return len(collected) > 0

        qtbot.waitUntil(check, timeout=5000)
        monitor.stop()
        assert len(collected) >= 1
        assert len(collected[0]) == 2

    def test_ignores_temp_files_and_ignored_dirs(self, monitor, tmp_path, qtbot):
        collected = []
        monitor.file_system_changed.connect(collected.append)
        watch_dir = tmp_path / "watch3"
        watch_dir.mkdir()
        git_dir = watch_dir / ".git"
        git_dir.mkdir()
        monitor.start([watch_dir])

        (watch_dir / "ignored.tmp").write_text("tmp")
        (watch_dir / "Thumbs.db").write_text("thumb")
        (git_dir / "HEAD").write_text("ref")
        (watch_dir / "valid.txt").write_text("ok")

        qtbot.waitUntil(lambda: len(collected) > 0, timeout=5000)
        qtbot.wait(80)
        monitor.stop()

        paths = [Path(ev.src_path).name for batch in collected for ev in batch]
        assert "valid.txt" in paths
        assert "ignored.tmp" not in paths
        assert "Thumbs.db" not in paths
        assert "HEAD" not in paths

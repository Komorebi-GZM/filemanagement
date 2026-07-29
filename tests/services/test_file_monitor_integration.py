import pytest


@pytest.mark.skip(reason="Requires real filesystem + qtbot; run manually to test watchdog integration")
class TestFileMonitorIntegration:
    """Real watchdog integration tests.

    Run with: conda run -n py311-pack python -m pytest tests/services/test_file_monitor_integration.py -v
    These tests are skipped by default because they rely on real filesystem timing.
    """

    def test_real_file_move_detected(self, qtbot, tmp_path):
        from src.app.services.file_monitor import FileMonitor

        monitor = FileMonitor(debounce_ms=200)
        collected = []
        monitor.file_system_changed.connect(collected.append)

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        src = watch_dir / "old_name.txt"
        src.write_text("content")

        monitor.start([watch_dir])

        def start_check():
            return monitor.is_running()
        qtbot.waitUntil(start_check, timeout=2000)

        dst = watch_dir / "new_name.txt"
        src.rename(dst)

        def check():
            if not collected:
                return False
            for batch in collected:
                for ev in batch:
                    if ev.event_type == "moved":
                        return True
            return False

        qtbot.waitUntil(check, timeout=10000)
        monitor.stop()

        assert any(
            ev.event_type == "moved"
            for batch in collected
            for ev in batch
        ), "Should detect moved event"

    def test_file_delete_detected(self, qtbot, tmp_path):
        from src.app.services.file_monitor import FileMonitor

        monitor = FileMonitor(debounce_ms=200)
        collected = []
        monitor.file_system_changed.connect(collected.append)

        watch_dir = tmp_path / "watch_del"
        watch_dir.mkdir()
        f = watch_dir / "delete_me.txt"
        f.write_text("bye")

        monitor.start([watch_dir])

        def start_check():
            return monitor.is_running()
        qtbot.waitUntil(start_check, timeout=2000)

        f.unlink()

        def check():
            if not collected:
                return False
            for batch in collected:
                for ev in batch:
                    if ev.event_type == "deleted":
                        return True
            return False

        qtbot.waitUntil(check, timeout=10000)
        monitor.stop()

        assert any(
            ev.event_type == "deleted"
            for batch in collected
            for ev in batch
        ), "Should detect deleted event"

    def test_file_modified_detected(self, qtbot, tmp_path):
        from src.app.services.file_monitor import FileMonitor

        monitor = FileMonitor(debounce_ms=200)
        collected = []
        monitor.file_system_changed.connect(collected.append)

        watch_dir = tmp_path / "watch_mod"
        watch_dir.mkdir()
        f = watch_dir / "modify_me.txt"
        f.write_text("original")

        monitor.start([watch_dir])

        def start_check():
            return monitor.is_running()
        qtbot.waitUntil(start_check, timeout=2000)

        f.write_text("modified content")

        def check():
            if not collected:
                return False
            for batch in collected:
                for ev in batch:
                    if ev.event_type == "modified":
                        return True
            return False

        qtbot.waitUntil(check, timeout=10000)
        monitor.stop()

        assert any(
            ev.event_type == "modified"
            for batch in collected
            for ev in batch
        ), "Should detect modified event"

    def test_create_detected(self, qtbot, tmp_path):
        from src.app.services.file_monitor import FileMonitor

        monitor = FileMonitor(debounce_ms=200)
        collected = []
        monitor.file_system_changed.connect(collected.append)

        watch_dir = tmp_path / "watch_create"
        watch_dir.mkdir()

        monitor.start([watch_dir])

        def start_check():
            return monitor.is_running()
        qtbot.waitUntil(start_check, timeout=2000)

        new_file = watch_dir / "new_file.txt"
        new_file.write_text("hello")

        def check():
            if not collected:
                return False
            for batch in collected:
                for ev in batch:
                    if ev.event_type == "created":
                        return True
            return False

        qtbot.waitUntil(check, timeout=10000)
        monitor.stop()

        assert any(
            ev.event_type == "created"
            for batch in collected
            for ev in batch
        ), "Should detect created event"

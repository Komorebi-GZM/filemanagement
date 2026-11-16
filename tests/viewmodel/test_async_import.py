import time
import pytest
from pathlib import Path
from PyQt5.QtCore import QCoreApplication
from src.app.db.database import Database
from src.app.viewmodel.main_viewmodel import MainViewModel, ImportCandidate
from src.app.viewmodel.signals import MainSignals


class TestAsyncImport:
    @pytest.fixture
    def vm(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        conn = db.connect()
        conn.executescript("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT, file_ext TEXT, full_path TEXT,
                file_size INTEGER, create_time INTEGER, modify_time INTEGER,
                file_hash TEXT, is_deleted INTEGER DEFAULT 0,
                deleted_at INTEGER, created_at INTEGER, updated_at INTEGER
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash);
        """)
        conn.close()
        signals = MainSignals()
        vm_inst = MainViewModel(db=db, signals=signals)
        yield vm_inst

    def test_import_files_returns_immediately(self, vm, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("hello", encoding="utf-8")
        candidates = [ImportCandidate(path=p, size=p.stat().st_size)]
        result = vm.import_files(candidates)
        assert result == 0

    def test_import_progress_signal_emitted(self, qtbot, vm, tmp_path):
        app = QCoreApplication.instance()
        p1 = tmp_path / "a.txt"
        p2 = tmp_path / "b.txt"
        p1.write_text("aaa", encoding="utf-8")
        p2.write_text("bbb", encoding="utf-8")
        candidates = [
            ImportCandidate(path=p1, size=p1.stat().st_size),
            ImportCandidate(path=p2, size=p2.stat().st_size),
        ]
        signals = []
        vm.signals.import_progress.connect(lambda c, t: signals.append((c, t)))
        vm.import_files(candidates)
        time.sleep(1.5)
        QCoreApplication.processEvents()
        assert len(signals) > 0
        assert signals[-1][0] == signals[-1][1]

    def test_files_appear_in_db_after_async_import(self, qtbot, vm, tmp_path):
        app = QCoreApplication.instance()
        p = tmp_path / "hello.txt"
        p.write_text("hello world", encoding="utf-8")
        candidates = [ImportCandidate(path=p, size=p.stat().st_size)]
        vm.import_files(candidates)
        time.sleep(1.5)
        QCoreApplication.processEvents()
        files = vm.list_files(limit=10)
        assert len(files) >= 1
        assert any("hello.txt" in f.file_name for f in files)

    def test_import_finished_emits_actual_count_and_files_updated_none(self, qtbot, vm, tmp_path):
        p1 = tmp_path / "one.txt"
        p2 = tmp_path / "two.txt"
        p1.write_text("content-1", encoding="utf-8")
        p2.write_text("content-2", encoding="utf-8")
        candidates = [
            ImportCandidate(path=p1, size=p1.stat().st_size),
            ImportCandidate(path=p2, size=p2.stat().st_size),
        ]

        finished_counts = []
        files_updated_payloads = []
        vm.signals.import_finished.connect(finished_counts.append)
        vm.signals.files_updated.connect(files_updated_payloads.append)

        vm.import_files(candidates)
        qtbot.waitUntil(lambda: len(finished_counts) == 1 and len(files_updated_payloads) == 1, timeout=5000)
        assert finished_counts == [2]
        assert files_updated_payloads == [None]

        # Re-importing the exact same active files should report 0 new imports
        finished_counts.clear()
        qtbot.waitUntil(lambda: vm._import_worker is None, timeout=5000)
        vm.import_files(candidates)
        qtbot.waitUntil(lambda: len(finished_counts) == 1, timeout=5000)
        assert finished_counts == [0]

        # Soft-deleting one and re-importing should count the restored file (1)
        files = vm.list_files(limit=10)
        vm.soft_delete_file(files[0].id)
        finished_counts.clear()
        qtbot.waitUntil(lambda: vm._import_worker is None, timeout=5000)
        vm.import_files(candidates)
        qtbot.waitUntil(lambda: len(finished_counts) == 1, timeout=5000)
        assert finished_counts == [1]

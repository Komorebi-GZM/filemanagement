import pytest
from pathlib import Path
from PyQt5.QtCore import QCoreApplication
from src.app.db.database import Database
from src.app.services.index_worker import IndexWorker


@pytest.fixture
def db_with_files(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    conn = db.connect()
    conn.executescript("""
        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT, file_ext TEXT, full_path TEXT,
            file_size INTEGER, file_hash TEXT,
            is_deleted INTEGER DEFAULT 0,
            created_at INTEGER, updated_at INTEGER
        );
    """)
    conn.execute(
        "INSERT INTO files (id, file_name, file_ext, full_path, file_size, file_hash, created_at, updated_at) "
        "VALUES (1, 'test.txt', 'txt', '/test.txt', 10, 'abc', 0, 0)"
    )
    conn.commit()
    conn.close()
    yield db


class TestIndexWorker:
    def test_enqueue_and_process(self, qtbot, tmp_path, db_with_files):
        app = QCoreApplication.instance()
        p = tmp_path / "test.txt"
        p.write_text("hello world", encoding="utf-8")
        worker = IndexWorker(db_with_files)
        worker.start()
        with qtbot.wait_signal(worker.index_updated, timeout=5000):
            worker.enqueue(1, p)
        worker.stop()
        conn = db_with_files.connect()
        row = conn.execute(
            "SELECT status FROM file_content_status WHERE file_id = 1"
        ).fetchone()
        assert row["status"] == "indexed"
        conn.close()

    def test_enqueue_batch(self, qtbot, tmp_path, db_with_files):
        app = QCoreApplication.instance()
        paths = []
        for i in range(3):
            p = tmp_path / f"test{i}.txt"
            p.write_text(f"content {i}", encoding="utf-8")
            paths.append(p)
        conn = db_with_files.connect()
        for i, p in enumerate(paths, start=2):
            conn.execute(
                "INSERT INTO files (id, file_name, file_ext, full_path, file_size, file_hash, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 10, ?, 0, 0)",
                (i, p.name, "txt", str(p), f"hash{i}")
            )
        conn.commit()
        conn.close()
        worker = IndexWorker(db_with_files)
        worker.start()
        signals_received = []
        worker.indexing_progress.connect(lambda c, t: signals_received.append((c, t)))
        items = [(i + 2, Path(p)) for i, p in enumerate(paths)]
        with qtbot.wait_signal(worker.indexing_finished, timeout=10000):
            worker.enqueue_batch(items)
        worker.stop()
        assert len(signals_received) > 0
        assert signals_received[-1][0] == signals_received[-1][1]

from __future__ import annotations

import logging
import os
from pathlib import Path

from src.app.core.logging_setup import setup_logging
from src.app.core.paths import resolve_paths
from src.app.core.settings import load_settings
from src.app.db.database import Database, apply_schema, load_schema_text
from src.app.ui.main_window import run_ui
from src.app.services.file_monitor import FileMonitor
from src.app.viewmodel.main_viewmodel import MainViewModel
from src.app.viewmodel.signals import MainSignals


def main() -> int:
    # 处理PyInstaller打包后的路径
    import sys
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        project_root = Path(sys._MEIPASS)
    else:
        # 开发环境
        project_root = Path(__file__).resolve().parents[1]
    
    settings = load_settings(project_root / "config" / "config.ini")
    paths = resolve_paths(project_root=project_root, active_user=settings.active_user)

    setup_logging(logs_dir=paths.logs_dir, log_file_rel=settings.log_file, level=settings.log_level)
    logging.getLogger(__name__).info("启动 %s (user=%s)", settings.app_name, settings.active_user)

    # 确保数据目录存在
    paths.user_dir.mkdir(parents=True, exist_ok=True)

    # 初始化数据库模式
    db_path = str(paths.db_file)
    db = Database(db_path)
    schema_sql = load_schema_text(project_root / "src" / "app" / "db" / "schema.sql")
    # 确保数据库目录存在
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    with db.connect() as conn:
        apply_schema(conn, schema_sql)

    signals = MainSignals()
    vm = MainViewModel(db=db, signals=signals)
    vm.init_index_worker()
    vm.start_progressive_indexing()

    # FileMonitor: watch all unique parent directories of imported files
    file_monitor = FileMonitor(debounce_ms=2000)
    watch_dirs: set[Path] = set()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT full_path FROM files WHERE is_deleted = 0"
        ).fetchall()
    for r in rows:
        p = Path(r["full_path"]).parent
        if p.exists():
            watch_dirs.add(p)
    if watch_dirs:
        file_monitor.start(list(watch_dirs))

    # Connect FileMonitor to ViewModel
    file_monitor.file_system_changed.connect(vm._on_file_system_changed)

    try:
        return run_ui(app_name=settings.app_name, vm=vm, signals=signals)
    finally:
        file_monitor.stop()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

class AppPaths:
    def __init__(self, project_root, config_file, logs_dir, data_dir, user_dir, db_file):
        self.project_root = project_root
        self.config_file = config_file
        self.logs_dir = logs_dir
        self.data_dir = data_dir
        self.user_dir = user_dir
        self.db_file = db_file


def resolve_paths(project_root, active_user):
    project_root = project_root.resolve()
    config_file = project_root / "config" / "config.ini"
    logs_dir = project_root / "logs"
    data_dir = project_root / "data"
    user_dir = data_dir / "users" / active_user
    db_file = user_dir / "app.sqlite3"

    return AppPaths(
        project_root=project_root,
        config_file=config_file,
        logs_dir=logs_dir,
        data_dir=data_dir,
        user_dir=user_dir,
        db_file=db_file,
    )

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    app_name: str
    active_user: str
    log_file: str
    log_level: str
    

def load_settings(config_path: Path) -> Settings:
    """加载配置文件"""
    config = configparser.ConfigParser()
    if config_path.exists():
        config.read(config_path, encoding="utf-8")
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as f:
            f.write("""
[General]
app_name = 智能文件管理系统
active_user = default

[Logging]
log_file = app.log
log_level = INFO
""")
        config.read(config_path, encoding="utf-8")
    
    return Settings(
        app_name=config.get("General", "app_name", fallback="智能文件管理系统"),
        active_user=config.get("General", "active_user", fallback="default"),
        log_file=config.get("Logging", "log_file", fallback="app.log"),
        log_level=config.get("Logging", "log_level", fallback="INFO"),
    )
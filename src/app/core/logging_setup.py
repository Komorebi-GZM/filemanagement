from __future__ import annotations

import logging
import os
from pathlib import Path


def setup_logging(logs_dir: Path, log_file_rel: str, level: str) -> None:
    """设置日志系统"""
    # 确保日志目录存在
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_dir / log_file_rel
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
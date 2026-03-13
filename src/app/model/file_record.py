from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FileRecord:
    """
    文件记录数据类
    存储文件的基本信息
    """
    id: int
    file_name: str
    full_path: str
    file_hash: str
    created_at: int
    updated_at: int
    file_ext: Optional[str] = None
    file_size: Optional[int] = None
    create_time: Optional[int] = None
    modify_time: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[int] = None

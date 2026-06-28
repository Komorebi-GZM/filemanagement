from __future__ import annotations

from dataclasses import dataclass

@dataclass
class FileImprint:
    """
    文件印记数据类
    存储文件的特定印记信息
    """
    id: int
    content: str
    created_at: int

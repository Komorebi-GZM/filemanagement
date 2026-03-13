from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Tag:
    id: int
    tag_name: str
    created_at: int
    updated_at: int
    tag_type: Optional[str] = None
    parent_id: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[int] = None

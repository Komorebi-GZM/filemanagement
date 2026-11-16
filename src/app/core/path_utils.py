from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, Union


def normalize_path(path: Union[str, Path]) -> str:
    """
    规范化路径：
    1. 消除符号链接（软链接）与相对路径（如 /tmp -> /private/tmp）。
    2. 执行 Unicode NFC 规范化，消除 macOS NFD 分解字符与 NFC 的不一致。
    3. Windows 盘符统一大写（如 c:\\ -> C:\\）。
    """
    raw_str = str(path).strip()
    if not raw_str:
        return ""

    # Windows 盘符路径（如 C:\a.txt 或 c:/a.txt）
    win_match = re.match(r"^([a-zA-Z]):([\\/].*|$)", raw_str)
    if win_match:
        drive = win_match.group(1).upper() + ":"
        rest = win_match.group(2)
        if sys.platform == "win32":
            try:
                resolved = Path(drive + rest).resolve(strict=False)
                res_str = str(resolved)
                m = re.match(r"^([a-zA-Z]):(.*)", res_str)
                if m:
                    res_str = m.group(1).upper() + ":" + m.group(2)
                return unicodedata.normalize("NFC", res_str)
            except Exception:
                pass
        # 在非 Windows 平台测试或处理 Windows 路径时，避免 POSIX resolve 附加当前工作路径
        return unicodedata.normalize("NFC", drive + rest)

    # POSIX 绝对路径或常规路径解析
    try:
        resolved_p = Path(raw_str).expanduser().resolve(strict=False)
        resolved_str = str(resolved_p)
    except Exception:
        resolved_str = raw_str

    return unicodedata.normalize("NFC", resolved_str)


def extract_location(full_path: str) -> Optional[Tuple[str, str]]:
    """
    从文件绝对路径中提取跨平台位置分类：
    Returns:
        (display_label, location_key) 或 None（若非绝对路径或无效路径）
    
    分类规则：
    - Windows 盘符：^[A-Za-z]: -> ("C:", "C:")
    - macOS 外接/独立卷：/Volumes/<name>/... -> ("<name>", "/Volumes/<name>")
    - macOS 系统卷/根目录：/System/Volumes/... 或 /... -> ("Macintosh HD", "/")
    """
    if not full_path or not isinstance(full_path, str):
        return None

    path_str = full_path.strip()
    if not path_str:
        return None

    # Windows 盘符
    win_match = re.match(r"^([a-zA-Z]):", path_str)
    if win_match:
        drive = win_match.group(1).upper() + ":"
        return (drive, drive)

    # 必须是绝对路径
    if not path_str.startswith("/"):
        return None

    # macOS APFS 内部/隐藏系统卷（如 /System/Volumes/Data/...）归入 Macintosh HD
    if path_str.startswith("/System/Volumes/"):
        return ("Macintosh HD", "/")

    # macOS 独立卷（/Volumes/<name>/...）
    if path_str.startswith("/Volumes/"):
        parts = [p for p in path_str.split("/") if p]
        if len(parts) >= 2:
            vol_name = parts[1]
            if vol_name == "Macintosh HD":
                return ("Macintosh HD", "/")
            return (vol_name, f"/Volumes/{vol_name}")
        elif len(parts) == 1:
            return ("Macintosh HD", "/")

    # 其它 POSIX 绝对路径，全部归入主系统盘
    return ("Macintosh HD", "/")


def escape_like(value: str) -> str:
    """
    对 SQLite LIKE 查询字符串进行特殊字符转义：
    将 '\\' 转义为 '\\\\', '%' 转义为 '\\%', '_' 转义为 '\\_'
    配合 SQL `LIKE ? ESCAPE '\\'` 使用。
    """
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")

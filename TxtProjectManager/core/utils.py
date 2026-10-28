"""通用小工具。"""

from datetime import datetime
from pathlib import Path


def human_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def file_meta(path: str) -> str:
    """文件列表里的第二行信息：修改时间 · 大小 · 所在目录。"""
    target = Path(path)
    try:
        stat = target.stat()
    except OSError:
        return "文件不存在 · " + str(target.parent)
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    return f"{mtime} · {human_size(stat.st_size)} · {target.parent}"


def reveal_in_explorer(path: str) -> None:
    """在资源管理器中定位文件（Windows）。"""
    import os
    import subprocess

    target = Path(path)
    try:
        if target.exists():
            subprocess.Popen(["explorer.exe", "/select,", str(target)])
        elif target.parent.exists():
            os.startfile(str(target.parent))  # noqa: S606
    except OSError:
        pass

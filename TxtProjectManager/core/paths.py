"""应用路径与数据目录定义。"""

import os
import sys
from pathlib import Path

APP_NAME = "TxtClassifyManager"
APP_TITLE = "TXT 分类管理器"


def app_data_dir() -> Path:
    """用户数据目录（配置文件、日志都放在这里）。"""
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file() -> Path:
    return app_data_dir() / "config.json"


def log_file() -> Path:
    log_dir = app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "operations.jsonl"


def app_dir() -> Path:
    """程序所在目录（打包后为 exe 所在目录）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def entry_script() -> Path:
    """入口脚本/可执行文件路径，用于开机自启动命令。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()

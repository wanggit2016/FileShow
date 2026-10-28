"""操作日志：JSONL 追加写入，支持查看、搜索与清空。"""

import json
from datetime import datetime

from .paths import log_file

MAX_BYTES = 4 * 1024 * 1024
KEEP_LINES = 2000
MAX_READ = 1000


class ActivityLog:
    def __init__(self, store):
        self.store = store
        self.path = log_file()

    @property
    def enabled(self) -> bool:
        return bool(self.store.settings.get("log_enabled", True))

    def record(self, action: str, detail: str = "") -> None:
        if not self.enabled:
            return
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "detail": detail,
        }
        try:
            self._trim_if_needed()
            with self.path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _trim_if_needed(self) -> None:
        try:
            if self.path.exists() and self.path.stat().st_size > MAX_BYTES:
                self._rewrite(self.read_raw()[-KEEP_LINES:])
        except OSError:
            pass

    def read_raw(self) -> list:
        entries = []
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []
        return entries

    def read(self, keyword: str = "", limit: int = MAX_READ) -> list:
        entries = self.read_raw()
        if keyword:
            needle = keyword.lower()
            entries = [
                e
                for e in entries
                if needle in str(e.get("action", "")).lower()
                or needle in str(e.get("detail", "")).lower()
            ]
        return entries[-limit:][::-1]

    def count(self) -> int:
        return len(self.read_raw())

    def clear(self) -> None:
        self._rewrite([])

    def _rewrite(self, entries: list) -> None:
        try:
            with self.path.open("w", encoding="utf-8") as fp:
                for entry in entries:
                    fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

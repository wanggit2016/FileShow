"""项目/文件配置的 JSON 持久化。"""

import copy
import json
import os
import uuid
from pathlib import Path

from .paths import config_file

DEFAULT_CONFIG = {
    "version": 1,
    "settings": {
        "autostart": False,
        "log_enabled": True,
    },
    "projects": [],
    "ui": {
        "window": None,
        "splitter": [330, 850],
        "last_file_id": None,
        "last_dir": "",
    },
}


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def _deep_merge(base: dict, extra: dict) -> dict:
    result = copy.deepcopy(base)
    if not isinstance(extra, dict):
        return result
    for key, value in extra.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class ConfigStore:
    """所有界面改动都写入 self.data，然后调用 save() 落盘。"""

    def __init__(self):
        self.path = config_file()
        self.data = self._load()

    # ------------------------------------------------------------------ 加载/保存
    def _load(self) -> dict:
        raw = {}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                try:
                    self.path.replace(self.path.with_suffix(".corrupt.json"))
                except OSError:
                    pass
                raw = {}
        data = _deep_merge(DEFAULT_CONFIG, raw)
        data["projects"] = self._normalize_projects(data.get("projects"))
        return data

    @staticmethod
    def _normalize_projects(items) -> list:
        projects = []
        if not isinstance(items, list):
            return projects
        for item in items:
            if not isinstance(item, dict):
                continue
            files = []
            for entry in item.get("files") or []:
                if not isinstance(entry, dict):
                    continue
                path = str(entry.get("path") or "").strip()
                if not path:
                    continue
                files.append(
                    {
                        "id": str(entry.get("id") or new_id()),
                        "name": str(entry.get("name") or Path(path).name),
                        "path": path,
                        "encoding": str(entry.get("encoding") or ""),
                    }
                )
            projects.append(
                {
                    "id": str(item.get("id") or new_id()),
                    "name": str(item.get("name") or "未命名项目"),
                    "visible": bool(item.get("visible", True)),
                    "show_fields": bool(item.get("show_fields", True)),
                    "collapsed": bool(item.get("collapsed", False)),
                    "files": files,
                }
            )
        return projects

    def save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(tmp, self.path)
        except OSError:
            pass

    # ------------------------------------------------------------------ 查询
    @property
    def projects(self) -> list:
        return self.data["projects"]

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    @property
    def ui(self) -> dict:
        return self.data["ui"]

    def find_project(self, project_id: str):
        return next((p for p in self.projects if p["id"] == project_id), None)

    def find_file(self, file_id: str):
        for project in self.projects:
            for entry in project["files"]:
                if entry["id"] == file_id:
                    return project, entry
        return None, None

    def project_name(self, project_id: str) -> str:
        project = self.find_project(project_id)
        return project["name"] if project else ""

    # ------------------------------------------------------------------ 项目操作
    def add_project(self, name: str) -> dict:
        project = {
            "id": new_id(),
            "name": (name or "").strip() or "未命名项目",
            "visible": True,
            "show_fields": True,
            "collapsed": False,
            "files": [],
        }
        self.projects.append(project)
        return project

    def rename_project(self, project_id: str, name: str) -> None:
        project = self.find_project(project_id)
        if project and name.strip():
            project["name"] = name.strip()

    def remove_project(self, project_id: str) -> None:
        self.data["projects"] = [p for p in self.projects if p["id"] != project_id]

    def move_project(self, index: int, new_index: int) -> None:
        projects = self.projects
        if not (0 <= index < len(projects)):
            return
        new_index = max(0, min(new_index, len(projects) - 1))
        if index == new_index:
            return
        projects.insert(new_index, projects.pop(index))

    def reorder_project(self, project_id: str, insert_index: int) -> None:
        ids = [p["id"] for p in self.projects]
        if project_id not in ids:
            return
        old = ids.index(project_id)
        if insert_index > old:
            insert_index -= 1
        self.move_project(old, insert_index)

    def toggle_fields(self, project_id: str) -> bool:
        project = self.find_project(project_id)
        if not project:
            return False
        project["show_fields"] = not project["show_fields"]
        return project["show_fields"]

    def set_visible(self, project_id: str, visible: bool) -> None:
        project = self.find_project(project_id)
        if project:
            project["visible"] = bool(visible)

    # ------------------------------------------------------------------ 文件操作
    def add_file(self, project_id: str, path: str):
        """返回新条目；若文件已存在该项目中则返回 None。"""
        project = self.find_project(project_id)
        if not project:
            return None
        absolute = os.path.abspath(path)
        norm = os.path.normcase(absolute)
        if any(os.path.normcase(os.path.abspath(f["path"])) == norm for f in project["files"]):
            return None
        entry = {
            "id": new_id(),
            "name": Path(absolute).name,
            "path": absolute,
            "encoding": "",
        }
        project["files"].append(entry)
        project["collapsed"] = False
        return entry

    def remove_file(self, project_id: str, file_id: str) -> None:
        project = self.find_project(project_id)
        if not project:
            return
        project["files"] = [f for f in project["files"] if f["id"] != file_id]

    def set_file_encoding(self, file_id: str, encoding: str) -> None:
        _, entry = self.find_file(file_id)
        if entry and entry.get("encoding") != encoding:
            entry["encoding"] = encoding
            self.save()

    def set_last_dir(self, directory: str) -> None:
        self.ui["last_dir"] = directory

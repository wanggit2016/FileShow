"""主窗口：顶部栏 + 左侧项目面板 + 右侧编辑区。"""

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.paths import APP_TITLE, app_data_dir
from core.utils import reveal_in_explorer

from .branding import make_app_icon
from .editor import EditorPanel
from .log_dialog import LogViewerDialog
from .settings import SettingsDialog
from .sidebar import ProjectSidebar
from .widgets import ask_confirm, ask_text, notify


class MainWindow(QMainWindow):
    def __init__(self, store, log):
        super().__init__()
        self.store = store
        self.log = log
        self._log_dialog = None

        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(make_app_icon())
        self.resize(1180, 760)
        self.setMinimumSize(900, 560)

        self._build_ui()
        self._restore_state()
        self._connect_signals()

        self.sidebar.reload()
        self._restore_last_file()
        self.log.record("启动应用", f"数据目录：{app_data_dir()}")

    # ------------------------------------------------------------------ 界面
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(6)
        self._splitter.setChildrenCollapsible(False)

        self.sidebar = ProjectSidebar(self.store)
        self.sidebar.setMinimumWidth(270)
        self.editor = EditorPanel(self.store)
        self.editor.setMinimumWidth(460)

        self._splitter.addWidget(self.sidebar)
        self._splitter.addWidget(self.editor)
        self._splitter.setSizes([330, 850])
        layout.addWidget(self._splitter, 1)

        self.setCentralWidget(root)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.setFixedHeight(62)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 10, 16, 10)
        header_layout.setSpacing(10)

        badge = QLabel("T")
        badge.setObjectName("BrandBadge")
        badge.setFixedSize(34, 34)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(badge)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(0)
        title = QLabel(APP_TITLE)
        title.setObjectName("AppTitle")
        subtitle = QLabel("按项目分类展示、查看与编辑 TXT 文件")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch(1)

        log_button = QPushButton("操作日志")
        log_button.setFixedHeight(30)
        log_button.setToolTip("查看添加、删除、保存等操作记录")
        log_button.clicked.connect(self._open_log_viewer)
        header_layout.addWidget(log_button)

        settings_button = QPushButton("设置")
        settings_button.setFixedHeight(30)
        settings_button.setToolTip("开机自启动、操作日志等系统设置")
        settings_button.clicked.connect(lambda: self._open_settings(1))
        header_layout.addWidget(settings_button)

        return header

    def _connect_signals(self) -> None:
        self.sidebar.file_selected.connect(self._on_file_selected)
        self.sidebar.new_project_requested.connect(self._create_project)
        self.sidebar.collapse_all_requested.connect(self._collapse_all_projects)
        self.sidebar.rename_project_requested.connect(self._rename_project)
        self.sidebar.delete_project_requested.connect(self._delete_project)
        self.sidebar.toggle_fields_requested.connect(self._toggle_fields)
        self.sidebar.add_existing_requested.connect(self._add_existing_files)
        self.sidebar.create_new_requested.connect(self._create_file)
        self.sidebar.remove_file_requested.connect(self._remove_file)
        self.sidebar.file_context_requested.connect(self._show_file_menu)
        self.sidebar.reorder_requested.connect(self._reorder_project)
        self.sidebar.settings_requested.connect(lambda: self._open_settings(0))

        self.editor.saved.connect(self._on_saved)
        self.editor.save_failed.connect(
            lambda path, error: self.log.record("保存失败", f"{path}：{error}")
        )
        self.editor.remove_requested.connect(self._remove_file)
        self.editor.relocated.connect(self._on_relocated)

        shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut.activated.connect(self.editor.save_now)

    # ------------------------------------------------------------------ 文件选中
    def _on_file_selected(self, file_id: str) -> None:
        project, entry = self.store.find_file(file_id)
        if not entry:
            return
        self.editor.open_file(project, entry)
        self.sidebar.set_selected_file(file_id)
        self.store.ui["last_file_id"] = file_id
        self.store.save()

    def _on_saved(self, path: str, file_id: str) -> None:
        project, entry = self.store.find_file(file_id)
        detail = f"{project['name']} / {entry['name']}" if entry else path
        self.log.record("保存文件", detail)

    def _on_relocated(self, file_id: str) -> None:
        project, entry = self.store.find_file(file_id)
        if not entry:
            return
        self.log.record("重新定位文件", f"{project['name']} / {entry['name']} → {entry['path']}")
        self.sidebar.reload()
        self._on_file_selected(file_id)

    # ------------------------------------------------------------------ 项目操作
    def _create_project(self) -> None:
        default = f"项目 {len(self.store.projects) + 1}"
        name, ok = ask_text(self, "新建项目", "项目名称：", default)
        if not ok or not name.strip():
            return
        project = self.store.add_project(name.strip())
        self.store.save()
        self.log.record("新建项目", project["name"])
        self.sidebar.reload()

    def _collapse_all_projects(self, collapsed: bool) -> None:
        if not self.store.projects:
            return
        self.sidebar.set_all_collapsed(collapsed)
        self.log.record(
            "全部折叠项目" if collapsed else "全部展开项目",
            f"{len(self.store.projects)} 个项目",
        )

    def _rename_project(self, project_id: str) -> None:
        project = self.store.find_project(project_id)
        if not project:
            return
        old_name = project["name"]
        name, ok = ask_text(self, "重命名项目", "项目名称：", old_name)
        if not ok or not name.strip():
            return
        self.store.rename_project(project_id, name)
        self.store.save()
        self.log.record("重命名项目", f"{old_name} → {project['name']}")
        self.sidebar.reload()
        current = self.editor.current_file_id()
        if current:
            current_project, entry = self.store.find_file(current)
            if entry and current_project["id"] == project_id:
                self.editor.update_project_name(project["name"])

    def _delete_project(self, project_id: str) -> None:
        project = self.store.find_project(project_id)
        if not project:
            return
        count = len(project["files"])
        if not ask_confirm(
            self,
            "删除项目",
            f"确定删除项目「{project['name']}」？\n"
            f"项目下的 {count} 个文件记录会被移除，磁盘上的文件不会被删除。",
        ):
            return
        current = self.editor.current_file_id()
        name = project["name"]
        self.store.remove_project(project_id)
        if current and not self.store.find_file(current)[1]:
            self.editor.clear_view()
            self.store.ui["last_file_id"] = None
        self.store.save()
        self.log.record("删除项目", f"{name}（{count} 个文件记录）")
        self.sidebar.reload()

    def _toggle_fields(self, project_id: str) -> None:
        project = self.store.find_project(project_id)
        if not project:
            return
        value = self.store.toggle_fields(project_id)
        self.store.save()
        self.log.record("项目字段显示", f"{project['name']}：{'显示' if value else '隐藏'}")
        self.sidebar.reload()

    def _reorder_project(self, project_id: str, index: int) -> None:
        all_ids = [p["id"] for p in self.store.projects]
        visible_ids = [p["id"] for p in self.store.projects if p.get("visible", True)]
        if project_id not in visible_ids:
            self.sidebar.reload()
            return
        if index >= len(visible_ids):
            target = len(all_ids)
        else:
            target = all_ids.index(visible_ids[index])
        before = list(all_ids)
        self.store.reorder_project(project_id, target)
        after = [p["id"] for p in self.store.projects]
        if before == after:
            self.sidebar.reload()
            return
        self.store.save()
        self.log.record("项目排序", f"{self.store.project_name(project_id)} 移动到第 {after.index(project_id) + 1} 位")
        self.sidebar.reload()

    # ------------------------------------------------------------------ 文件操作
    def _add_existing_files(self, project_id: str) -> None:
        project = self.store.find_project(project_id)
        if not project:
            return
        start_dir = self.store.ui.get("last_dir") or self._default_dir(project)
        files, _ = QFileDialog.getOpenFileNames(
            self,
            f"为「{project['name']}」选择文件",
            start_dir,
            "所有文件 (*.*);;文本文件 (*.txt *.md *.log *.ini *.json *.csv)",
        )
        if not files:
            return

        added = []
        skipped = []
        for path in files:
            entry = self.store.add_file(project_id, path)
            if entry:
                added.append(entry)
            else:
                skipped.append(Path(path).name)

        if added:
            self.store.set_last_dir(str(Path(added[0]["path"]).parent))
            self.store.save()
            self.log.record("添加文件", f"{project['name']}：{', '.join(e['name'] for e in added)}")
            self.sidebar.clear_search()
            self.sidebar.reload()
            self._on_file_selected(added[-1]["id"])

        if skipped:
            notify(
                self,
                "部分文件已存在",
                "以下文件已在该项目中，已跳过：\n" + "\n".join(skipped),
            )

    def _create_file(self, project_id: str) -> None:
        project = self.store.find_project(project_id)
        if not project:
            return
        default_dir = self.store.ui.get("last_dir") or self._default_dir(project)
        suggested = str(Path(default_dir) / "新建文本.txt")
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"新建文件并保存到「{project['name']}」",
            suggested,
            "文本文件 (*.txt);;所有文件 (*.*)",
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".txt")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.touch()
        except OSError as exc:
            notify(self, "新建文件失败", f"无法创建文件：\n{exc}", warning=True)
            return

        entry = self.store.add_file(project_id, str(target))
        if not entry:
            notify(self, "文件已存在", "该文件已经在项目中了。")
            return
        self.store.set_last_dir(str(target.parent))
        self.store.save()
        self.log.record("新建文件", f"{project['name']}：{target.name} → {target}")
        self.sidebar.clear_search()
        self.sidebar.reload()
        self._on_file_selected(entry["id"])

    def _remove_file(self, file_id: str) -> None:
        project, entry = self.store.find_file(file_id)
        if not project or not entry:
            return
        if not ask_confirm(
            self,
            "移除文件",
            f"确定从项目「{project['name']}」中移除「{entry['name']}」？\n"
            "只移除列表记录，不会删除磁盘上的文件。",
        ):
            return
        self.store.remove_file(project["id"], file_id)
        self.store.save()
        self.log.record("移除文件", f"{project['name']}：{entry['name']}")
        if self.editor.current_file_id() == file_id:
            self.editor.clear_view()
            self.store.ui["last_file_id"] = None
            self.sidebar.set_selected_file(None)
        self.sidebar.reload()

    def _show_file_menu(self, file_id: str, position) -> None:
        project, entry = self.store.find_file(file_id)
        if not entry:
            return
        menu = QMenu(self)
        copy_action = menu.addAction("复制文件路径")
        reveal_action = menu.addAction("在资源管理器中显示")
        menu.addSeparator()
        remove_action = menu.addAction("从项目中移除")
        chosen = menu.exec(position)
        if chosen == copy_action:
            QApplication.clipboard().setText(entry["path"])
        elif chosen == reveal_action:
            reveal_in_explorer(entry["path"])
        elif chosen == remove_action:
            self._remove_file(file_id)

    def _default_dir(self, project: dict) -> str:
        for entry in project["files"]:
            parent = Path(entry["path"]).parent
            if parent.exists():
                return str(parent)
        documents = Path.home() / "Documents"
        return str(documents if documents.exists() else Path.home())

    # ------------------------------------------------------------------ 设置/日志
    def _open_settings(self, tab_index: int) -> None:
        dialog = SettingsDialog(self.store, self.log, initial_tab=tab_index, parent=self)
        dialog.changed.connect(self._on_settings_changed)
        dialog.view_log_requested.connect(self._open_log_viewer)
        dialog.exec()

    def _on_settings_changed(self) -> None:
        self.sidebar.reload()
        current = self.editor.current_file_id()
        if not current:
            return
        project, entry = self.store.find_file(current)
        if entry:
            self.editor.update_project_name(project["name"])
        else:
            self.editor.clear_view()

    def _open_log_viewer(self) -> None:
        if self._log_dialog is None:
            self._log_dialog = LogViewerDialog(self.log, self)
        self._log_dialog.refresh()
        self._log_dialog.show()
        self._log_dialog.raise_()
        self._log_dialog.activateWindow()

    # ------------------------------------------------------------------ 状态恢复
    def _restore_state(self) -> None:
        window = self.store.ui.get("window")
        if isinstance(window, dict):
            try:
                rect = QRect(
                    int(window["x"]),
                    int(window["y"]),
                    int(window["width"]),
                    int(window["height"]),
                )
            except (KeyError, TypeError, ValueError):
                rect = None
            if rect is not None and rect.width() > 400 and rect.height() > 300:
                visible = any(
                    screen.availableGeometry().intersects(rect)
                    for screen in QGuiApplication.screens()
                )
                if visible:
                    self.setGeometry(rect)
            if window.get("maximized"):
                self.showMaximized()

        sizes = self.store.ui.get("splitter")
        if isinstance(sizes, list) and len(sizes) == 2:
            try:
                self._splitter.setSizes([int(sizes[0]), int(sizes[1])])
            except (TypeError, ValueError):
                pass

    def _restore_last_file(self) -> None:
        last = self.store.ui.get("last_file_id")
        if not last:
            return
        project, entry = self.store.find_file(last)
        if not entry:
            return
        if not project.get("visible", True):
            return
        if project["collapsed"]:
            project["collapsed"] = False
            self.store.save()
            self.sidebar.reload()
        self._on_file_selected(last)

    def _persist_state(self) -> None:
        geometry = self.geometry()
        self.store.ui["window"] = {
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
            "maximized": self.isMaximized(),
        }
        self.store.ui["splitter"] = self._splitter.sizes()
        self.store.ui["last_file_id"] = self.editor.current_file_id()
        self.store.save()

    def closeEvent(self, event):  # noqa: N802
        self.editor.flush()
        self._persist_state()
        self.log.record("退出应用")
        if self._log_dialog is not None:
            self._log_dialog.close()
        super().closeEvent(event)

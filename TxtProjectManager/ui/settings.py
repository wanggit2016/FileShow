"""设置对话框：项目管理 + 系统设置。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import autostart
from core.paths import config_file, log_file
from core.utils import reveal_in_explorer

from .widgets import ElidedLabel, ask_confirm, ask_text, notify


class ProjectTable(QTableWidget):
    """支持整行拖拽排序的表格。"""

    row_move_requested = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self.setHorizontalHeaderLabels(["项目名称", "是否显示", "显示文件字段"])
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(38)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 96)
        self.setColumnWidth(2, 150)

    def dropEvent(self, event):  # noqa: N802
        source_row = self.currentRow()
        if source_row < 0:
            event.ignore()
            return
        target = self.rowAt(int(event.position().y()))
        indicator = self.dropIndicatorPosition()
        if target < 0:
            target = self.rowCount()
        elif indicator == QAbstractItemView.DropIndicatorPosition.BelowItem:
            target += 1
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        if target != source_row:
            self.row_move_requested.emit(source_row, target)


class ProjectSettingsPage(QWidget):
    changed = Signal()

    def __init__(self, store, log, parent=None):
        super().__init__(parent)
        self.store = store
        self.log = log
        self._building = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        hint = QLabel(
            "维护项目名称、是否在左侧列表中显示、是否显示文件字段，按住表格中的行拖拽即可调整项目顺序。"
        )
        hint.setObjectName("HintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = ProjectTable()
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        add_button = QPushButton("＋ 新建项目")
        add_button.setProperty("role", "primary")
        add_button.clicked.connect(self._add_project)
        buttons.addWidget(add_button)

        delete_button = QPushButton("删除项目")
        delete_button.setProperty("role", "danger")
        delete_button.clicked.connect(self._delete_project)
        buttons.addWidget(delete_button)

        up_button = QPushButton("上移")
        up_button.clicked.connect(lambda: self._move_selected(-1))
        buttons.addWidget(up_button)

        down_button = QPushButton("下移")
        down_button.clicked.connect(lambda: self._move_selected(1))
        buttons.addWidget(down_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.table.itemChanged.connect(self._on_item_changed)
        self.table.row_move_requested.connect(self._on_row_move)
        self.rebuild()

    # ------------------------------------------------------------------ 数据
    def _pid_at(self, row: int):
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def rebuild(self) -> None:
        self._building = True
        self.table.setRowCount(0)
        for project in self.store.projects:
            row = self.table.rowCount()
            self.table.insertRow(row)
            item = QTableWidgetItem(project["name"])
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            item.setData(Qt.ItemDataRole.UserRole, project["id"])
            self.table.setItem(row, 0, item)

            visible_check = QCheckBox()
            visible_check.setChecked(bool(project.get("visible", True)))
            visible_check.setToolTip("关闭后该项目不会出现在左侧列表中")
            visible_check.toggled.connect(
                lambda checked, pid=project["id"]: self._on_visible_toggled(pid, checked)
            )
            visible_wrap = QWidget()
            visible_layout = QHBoxLayout(visible_wrap)
            visible_layout.setContentsMargins(0, 0, 0, 0)
            visible_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            visible_layout.addWidget(visible_check)
            self.table.setCellWidget(row, 1, visible_wrap)

            check = QCheckBox()
            check.setChecked(bool(project["show_fields"]))
            check.setToolTip("在左侧列表中显示文件路径、修改时间与大小")
            check.toggled.connect(
                lambda checked, pid=project["id"]: self._on_fields_toggled(pid, checked)
            )
            wrap = QWidget()
            wrap_layout = QHBoxLayout(wrap)
            wrap_layout.setContentsMargins(0, 0, 0, 0)
            wrap_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wrap_layout.addWidget(check)
            self.table.setCellWidget(row, 2, wrap)
        self._building = False

    def _select_row(self, row: int) -> None:
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)

    def _selected_row(self) -> int:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    # ------------------------------------------------------------------ 操作
    def _add_project(self) -> None:
        default = f"项目 {len(self.store.projects) + 1}"
        name, ok = ask_text(self, "新建项目", "项目名称：", default)
        if not ok or not name.strip():
            return
        project = self.store.add_project(name.strip())
        self.store.save()
        self.log.record("新建项目", project["name"])
        self.rebuild()
        self._select_row(self.table.rowCount() - 1)
        self.changed.emit()

    def _delete_project(self) -> None:
        row = self._selected_row()
        pid = self._pid_at(row)
        project = self.store.find_project(pid)
        if not project:
            return
        if not ask_confirm(
            self,
            "删除项目",
            f"确定删除项目「{project['name']}」？\n"
            f"项目下的 {len(project['files'])} 个文件记录会被移除，磁盘文件不会删除。",
        ):
            return
        name = project["name"]
        self.store.remove_project(pid)
        self.store.save()
        self.log.record("删除项目", f"{name}（{len(project['files'])} 个文件记录）")
        self.rebuild()
        self.changed.emit()

    def _move_selected(self, offset: int) -> None:
        row = self._selected_row()
        project = self.store.find_project(self._pid_at(row))
        if not project:
            return
        target = row + offset
        if not (0 <= target < len(self.store.projects)):
            return
        self.store.move_project(row, target)
        self.store.save()
        self.log.record("项目排序", f"{project['name']} 移动到第 {target + 1} 位")
        self.rebuild()
        self._select_row(target)
        self.changed.emit()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._building or item.column() != 0:
            return
        pid = self._pid_at(item.row())
        project = self.store.find_project(pid)
        if not project:
            return
        name = item.text().strip()
        if not name:
            self.rebuild()
            return
        if name == project["name"]:
            return
        old = project["name"]
        self.store.rename_project(pid, name)
        self.store.save()
        self.log.record("重命名项目", f"{old} → {name}")
        self.changed.emit()

    def _on_visible_toggled(self, pid: str, checked: bool) -> None:
        if self._building:
            return
        project = self.store.find_project(pid)
        if not project:
            return
        self.store.set_visible(pid, checked)
        self.store.save()
        self.log.record("项目显示", f"{project['name']}：{'显示' if checked else '隐藏'}")
        self.changed.emit()

    def _on_fields_toggled(self, pid: str, checked: bool) -> None:
        if self._building:
            return
        project = self.store.find_project(pid)
        if not project:
            return
        project["show_fields"] = checked
        self.store.save()
        self.log.record("项目字段显示", f"{project['name']}：{'显示' if checked else '隐藏'}")
        self.changed.emit()

    def _on_row_move(self, source: int, target: int) -> None:
        projects = self.store.projects
        if not (0 <= source < len(projects)):
            return
        new_index = target - 1 if target > source else target
        new_index = max(0, min(new_index, len(projects) - 1))
        if new_index == source:
            self.rebuild()
            return
        name = projects[source]["name"]
        self.store.move_project(source, new_index)
        self.store.save()
        self.log.record("项目排序", f"{name} 移动到第 {new_index + 1} 位")
        self.rebuild()
        self._select_row(new_index)
        self.changed.emit()


class SystemSettingsPage(QWidget):
    changed = Signal()
    view_log_requested = Signal()

    def __init__(self, store, log, parent=None):
        super().__init__(parent)
        self.store = store
        self.log = log
        self._syncing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("启动与日志")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        # ---- 开机自启动
        self._autostart_box = QCheckBox("开机时自动启动本程序")
        self._autostart_box.setChecked(autostart.is_enabled())
        self._autostart_box.toggled.connect(self._toggle_autostart)
        layout.addWidget(self._autostart_box)

        autostart_hint = QLabel(
            "开启后会写入当前用户的启动项（注册表 HKCU\\...\\Run），登录 Windows 后自动运行。"
        )
        autostart_hint.setObjectName("HintLabel")
        autostart_hint.setWordWrap(True)
        layout.addWidget(autostart_hint)

        # ---- 操作日志
        self._log_box = QCheckBox("记录操作日志")
        self._log_box.setChecked(bool(self.store.settings.get("log_enabled", True)))
        self._log_box.toggled.connect(self._toggle_logging)
        layout.addWidget(self._log_box)

        log_hint = QLabel("记录添加/删除项目、添加/移除文件、保存文件、修改设置等操作。")
        log_hint.setObjectName("HintLabel")
        log_hint.setWordWrap(True)
        layout.addWidget(log_hint)

        # ---- 存储位置
        location = QFrame()
        location.setObjectName("SettingRow")
        location_layout = QVBoxLayout(location)
        location_layout.setContentsMargins(14, 12, 14, 12)
        location_layout.setSpacing(8)

        location_layout.addWidget(self._row_label("日志文件"))
        log_path = ElidedLabel(str(log_file()), Qt.TextElideMode.ElideMiddle, location)
        log_path.setObjectName("HintLabel")
        location_layout.addWidget(log_path)

        log_buttons = QHBoxLayout()
        log_buttons.setSpacing(8)
        view_button = QPushButton("查看操作日志")
        view_button.setProperty("role", "primary")
        view_button.clicked.connect(self.view_log_requested)
        log_buttons.addWidget(view_button)

        open_log_button = QPushButton("打开所在文件夹")
        open_log_button.clicked.connect(lambda: reveal_in_explorer(str(log_file())))
        log_buttons.addWidget(open_log_button)
        log_buttons.addStretch(1)
        location_layout.addLayout(log_buttons)

        location_layout.addWidget(self._row_label("数据保存位置"))
        config_path = ElidedLabel(str(config_file()), Qt.TextElideMode.ElideMiddle, location)
        config_path.setObjectName("HintLabel")
        location_layout.addWidget(config_path)

        open_data_button = QPushButton("打开数据目录")
        open_data_button.clicked.connect(lambda: reveal_in_explorer(str(config_file())))
        open_data_row = QHBoxLayout()
        open_data_row.addWidget(open_data_button)
        open_data_row.addStretch(1)
        location_layout.addLayout(open_data_row)

        layout.addWidget(location)
        layout.addStretch(1)

    @staticmethod
    def _row_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    # ------------------------------------------------------------------ 操作
    def _toggle_autostart(self, checked: bool) -> None:
        if self._syncing:
            return
        if not autostart.set_enabled(checked):
            self._syncing = True
            self._autostart_box.setChecked(not checked)
            self._syncing = False
            notify(self, "设置失败", "无法写入开机启动项，请检查系统权限。", warning=True)
            return
        self.store.settings["autostart"] = checked
        self.store.save()
        self.log.record("系统设置", ("开启" if checked else "关闭") + "开机自启动")

    def _toggle_logging(self, checked: bool) -> None:
        if self._syncing:
            return
        if not checked:
            self.log.record("系统设置", "关闭操作日志记录")
        self.store.settings["log_enabled"] = checked
        self.store.save()
        if checked:
            self.log.record("系统设置", "开启操作日志记录")


class SettingsDialog(QDialog):
    changed = Signal()
    view_log_requested = Signal()

    def __init__(self, store, log, initial_tab: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(720, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.project_page = ProjectSettingsPage(store, log)
        self.system_page = SystemSettingsPage(store, log)
        self.tabs.addTab(self.project_page, "项目管理")
        self.tabs.addTab(self.system_page, "系统设置")
        self.tabs.setCurrentIndex(max(0, min(initial_tab, 1)))
        layout.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        done_button = QPushButton("完成")
        done_button.setProperty("role", "primary")
        done_button.clicked.connect(self.accept)
        bottom.addWidget(done_button)
        layout.addLayout(bottom)

        self.project_page.changed.connect(self.changed)
        self.system_page.changed.connect(self.changed)
        self.system_page.view_log_requested.connect(self._view_logs)

    def _view_logs(self) -> None:
        """设置窗为模态窗口，查看日志前先关闭它。"""
        self.accept()
        self.view_log_requested.emit()

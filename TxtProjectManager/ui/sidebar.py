"""左侧项目/文件面板，支持拖拽调整项目顺序。"""

from pathlib import Path

from PySide6.QtCore import QEvent, QMimeData, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.utils import file_meta

from .widgets import ElidedLabel, chevrons_icon, repolish

PROJECT_MIME = "application/x-txt-project-id"


class FileRow(QWidget):
    clicked = Signal(str)
    context_requested = Signal(str, QPoint)

    def __init__(self, entry: dict, show_fields: bool, selected: bool, parent=None):
        super().__init__(parent)
        self.file_id = entry["id"]
        self.setObjectName("FileRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("missing", "false" if Path(entry["path"]).exists() else "true")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 5, 10, 5)
        layout.setSpacing(1)

        self._name = ElidedLabel(entry["name"])
        self._name.setObjectName("FileName")
        layout.addWidget(self._name)

        if show_fields:
            meta = ElidedLabel(file_meta(entry["path"]), Qt.TextElideMode.ElideRight)
            meta.setObjectName("FileMeta")
            layout.addWidget(meta)

        tooltip = entry["path"]
        if not Path(entry["path"]).exists():
            tooltip = "文件不存在：" + entry["path"]
        self.setToolTip(tooltip)
        self.set_selected(selected)

    def set_selected(self, selected: bool) -> None:
        value = "true" if selected else "false"
        self.setProperty("selected", value)
        self._name.setProperty("selected", value)
        repolish(self)
        repolish(self._name)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):  # noqa: N802
        self.context_requested.emit(self.file_id, event.globalPos())


class CardHeader(QFrame):
    """卡片头部：按住并拖动可调整项目顺序。"""

    drag_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardHeader")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._press_pos = None

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._press_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.position().toPoint() - self._press_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._press_pos = None
                self.drag_requested.emit()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._press_pos = None
        super().mouseReleaseEvent(event)


class ProjectCard(QFrame):
    add_file_clicked = Signal(str, QPoint)
    menu_requested = Signal(str, QPoint)
    toggle_requested = Signal(str)
    drag_started = Signal(str)
    file_clicked = Signal(str)
    file_context = Signal(str, QPoint)

    def __init__(self, project: dict, selected_file_id: str, parent=None):
        super().__init__(parent)
        self.project = project
        self.project_id = project["id"]
        self.setObjectName("ProjectCard")
        self._rows = []
        self._row_entries = []
        self.drag_enabled = True
        self._expanded = not project["collapsed"]

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = CardHeader()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(9, 7, 6, 7)
        header_layout.setSpacing(3)

        handle = QLabel("\u283f")
        handle.setObjectName("DragHandle")
        handle.setToolTip("按住拖动可调整项目顺序")
        header_layout.addWidget(handle)

        self._arrow = QPushButton("\u25be")
        self._arrow.setProperty("role", "icon")
        self._arrow.setFixedSize(20, 20)
        self._arrow.setCursor(Qt.CursorShape.PointingHandCursor)
        self._arrow.setToolTip("收起 / 展开")
        self._arrow.clicked.connect(lambda: self.toggle_requested.emit(self.project_id))
        header_layout.addWidget(self._arrow)

        self._name = ElidedLabel(project["name"])
        self._name.setObjectName("ProjectName")
        self._name.setToolTip(project["name"])
        self._name.installEventFilter(self)
        header_layout.addWidget(self._name, 1)

        self._count = QLabel(str(len(project["files"])))
        self._count.setObjectName("ProjectCount")
        self._count.setToolTip(f"{len(project['files'])} 个文件")
        header_layout.addWidget(self._count)

        self._add_button = QPushButton("\uff0b\u6dfb\u52a0\u6587\u4ef6")
        self._add_button.setObjectName("AddFileButton")
        self._add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_button.setToolTip("添加文件：选择已有文件，或新建文件并选择保存路径")
        self._add_button.clicked.connect(self._emit_add_file)
        header_layout.addWidget(self._add_button)

        self._menu_button = QPushButton("\u22ef")
        self._menu_button.setProperty("role", "icon")
        self._menu_button.setFixedSize(22, 22)
        self._menu_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._menu_button.setToolTip("项目操作")
        self._menu_button.clicked.connect(self._emit_menu)
        header_layout.addWidget(self._menu_button)

        root.addWidget(self._header)

        self._body = QWidget()
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(6, 0, 6, 8)
        body_layout.setSpacing(1)
        if not project["files"]:
            hint = QLabel("暂无文件，点击「＋添加文件」")
            hint.setObjectName("CardHint")
            hint.setContentsMargins(10, 0, 0, 6)
            body_layout.addWidget(hint)
        for entry in project["files"]:
            row = FileRow(entry, project["show_fields"], entry["id"] == selected_file_id)
            row.clicked.connect(self.file_clicked)
            row.context_requested.connect(self.file_context)
            body_layout.addWidget(row)
            self._rows.append(row)
            self._row_entries.append((entry, row))
        root.addWidget(self._body)

        self._header.drag_requested.connect(self._start_drag)
        self.set_expanded(self._expanded)
        self.set_selected_file(selected_file_id)

    # ------------------------------------------------------------------ 交互
    def _emit_add_file(self) -> None:
        point = self._add_button.mapToGlobal(QPoint(0, self._add_button.height() + 4))
        self.add_file_clicked.emit(self.project_id, point)

    def _emit_menu(self) -> None:
        point = self._menu_button.mapToGlobal(QPoint(0, self._menu_button.height() + 4))
        self.menu_requested.emit(self.project_id, point)

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._name and event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                self.toggle_requested.emit(self.project_id)
                return True
        return super().eventFilter(obj, event)

    def _start_drag(self) -> None:
        if not self.drag_enabled:
            return
        mime = QMimeData()
        mime.setData(PROJECT_MIME, self.project_id.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.grab()
        if pixmap.width() > 320:
            pixmap = pixmap.scaledToWidth(320, Qt.TransformationMode.SmoothTransformation)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(26, 20))
        self.drag_started.emit(self.project_id)
        drag.exec(Qt.DropAction.MoveAction)

    # ------------------------------------------------------------------ 状态
    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._body.setVisible(expanded)
        self._arrow.setText("\u25be" if expanded else "\u25b8")

    def apply_filter(self, keyword: str) -> bool:
        """按关键字过滤：项目名命中则显示全部文件，否则只显示命中的文件。"""
        keyword = keyword.strip().lower()
        if not keyword:
            for _, row in self._row_entries:
                row.setVisible(True)
            self.setVisible(True)
            self.set_expanded(not self.project["collapsed"])
            return True

        project_hit = keyword in str(self.project["name"]).lower()
        file_hit = False
        for entry, row in self._row_entries:
            hit = project_hit or keyword in str(entry["name"]).lower()
            row.setVisible(hit)
            file_hit = file_hit or hit
        visible = project_hit or file_hit
        self.setVisible(visible)
        if visible:
            self.set_expanded(True)
        return visible

    def set_selected_file(self, file_id: str) -> None:
        ids = [f["id"] for f in self.project["files"]]
        self.setProperty("selected", "true" if file_id in ids else "false")
        repolish(self)
        for row in self._rows:
            row.set_selected(row.file_id == file_id)

    def set_drag_side(self, side: str) -> None:
        self.setProperty("dragSide", side)
        repolish(self)


class DropCanvas(QWidget):
    """承载项目卡片的容器，负责接收拖拽并计算插入位置。"""

    index_hint = Signal(int)
    dropped = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarCanvas")
        self.setAcceptDrops(True)
        self._index = -1

    def cards(self) -> list:
        layout = self.layout()
        result = []
        if layout is None:
            return result
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, ProjectCard):
                result.append(widget)
        return result

    def _index_at(self, y: int) -> int:
        for i, card in enumerate(self.cards()):
            if y < card.geometry().center().y():
                return i
        return len(self.cards())

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasFormat(PROJECT_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # noqa: N802
        if not event.mimeData().hasFormat(PROJECT_MIME):
            event.ignore()
            return
        index = self._index_at(int(event.position().y()))
        if index != self._index:
            self._index = index
            self.index_hint.emit(index)
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):  # noqa: N802
        self._index = -1
        self.index_hint.emit(-1)
        event.accept()

    def dropEvent(self, event):  # noqa: N802
        index = self._index_at(int(event.position().y()))
        self._index = -1
        self.index_hint.emit(-1)
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        self.dropped.emit(index)


class ProjectSidebar(QWidget):
    file_selected = Signal(str)
    add_existing_requested = Signal(str)
    create_new_requested = Signal(str)
    rename_project_requested = Signal(str)
    delete_project_requested = Signal(str)
    toggle_fields_requested = Signal(str)
    remove_file_requested = Signal(str)
    file_context_requested = Signal(str, QPoint)
    reorder_requested = Signal(str, int)
    settings_requested = Signal()
    new_project_requested = Signal()
    collapse_all_requested = Signal(bool)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self._selected_file_id = None
        self._drag_project_id = None
        self._cards = []

        self.setObjectName("Sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setObjectName("SidebarHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.setFixedHeight(46)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 10, 8)
        header_layout.setSpacing(4)

        title = QLabel("项目")
        title.setObjectName("SidebarTitle")
        header_layout.addWidget(title)

        self._count_label = QLabel("")
        self._count_label.setObjectName("SidebarCount")
        header_layout.addWidget(self._count_label)
        header_layout.addStretch(1)

        new_button = QPushButton("\uff0b")
        new_button.setProperty("role", "icon")
        new_button.setFixedSize(26, 26)
        new_button.setToolTip("新建项目")
        new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        new_button.clicked.connect(self.new_project_requested)
        header_layout.addWidget(new_button)

        collapse_button = QPushButton()
        collapse_button.setIcon(chevrons_icon(True))
        collapse_button.setIconSize(QSize(16, 16))
        collapse_button.setProperty("role", "icon")
        collapse_button.setFixedSize(26, 26)
        collapse_button.setToolTip("全部折叠")
        collapse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        collapse_button.clicked.connect(lambda: self.collapse_all_requested.emit(True))
        header_layout.addWidget(collapse_button)

        expand_button = QPushButton()
        expand_button.setIcon(chevrons_icon(False))
        expand_button.setIconSize(QSize(16, 16))
        expand_button.setProperty("role", "icon")
        expand_button.setFixedSize(26, 26)
        expand_button.setToolTip("全部展开")
        expand_button.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_button.clicked.connect(lambda: self.collapse_all_requested.emit(False))
        header_layout.addWidget(expand_button)

        settings_button = QPushButton("设置")
        settings_button.setProperty("role", "ghost")
        settings_button.setFixedHeight(26)
        settings_button.setToolTip("项目设置：维护项目名称、字段显示、拖拽排序")
        settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_button.clicked.connect(self.settings_requested)
        header_layout.addWidget(settings_button)

        root.addWidget(header)

        search_wrap = QWidget()
        search_wrap.setObjectName("SidebarSearchWrap")
        search_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        search_layout = QHBoxLayout(search_wrap)
        search_layout.setContentsMargins(10, 8, 10, 2)
        search_layout.setSpacing(0)
        self._search = QLineEdit()
        self._search.setObjectName("SidebarSearch")
        self._search.setPlaceholderText("搜索项目或文件")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedHeight(30)
        self._search.textChanged.connect(lambda _: self._apply_filter())
        search_layout.addWidget(self._search)
        root.addWidget(search_wrap)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("SidebarScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().setAutoFillBackground(False)

        self._canvas = DropCanvas()
        self._canvas_layout = QVBoxLayout(self._canvas)
        self._canvas_layout.setContentsMargins(10, 10, 10, 12)
        self._canvas_layout.setSpacing(8)

        self._empty = QLabel("还没有项目\n点击上方「＋」新建项目")
        self._empty.setObjectName("SidebarEmpty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setContentsMargins(0, 40, 0, 0)
        self._canvas_layout.addWidget(self._empty)
        self._canvas_layout.addStretch(1)

        self._scroll.setWidget(self._canvas)
        root.addWidget(self._scroll, 1)

        self._canvas.index_hint.connect(self._highlight_drop)
        self._canvas.dropped.connect(self._handle_drop)

    # ------------------------------------------------------------------ 构建
    def reload(self) -> None:
        for card in self._cards:
            self._canvas_layout.removeWidget(card)
            card.deleteLater()
        self._cards = []

        projects = self.store.projects
        if self._selected_file_id:
            project, entry = self.store.find_file(self._selected_file_id)
            if entry is None:
                self._selected_file_id = None

        for project in projects:
            if not project.get("visible", True):
                continue
            card = ProjectCard(project, self._selected_file_id)
            self._connect_card(card)
            self._canvas_layout.insertWidget(self._canvas_layout.count() - 1, card)
            self._cards.append(card)

        self._empty.setVisible(not self._cards)
        self._count_label.setText(f"{len(self._cards)} 个" if self._cards else "")
        self._update_card_selection()
        self._apply_filter()

    def _apply_filter(self) -> None:
        keyword = self._search.text().strip()
        visible = 0
        self._search.setToolTip("" if not keyword else f"搜索：{keyword}")
        for card in self._cards:
            card.drag_enabled = not keyword
            if card.apply_filter(keyword):
                visible += 1

        if keyword and visible == 0:
            self._empty.setText("未找到匹配的项目或文件\n试试其他关键字")
            self._empty.setVisible(True)
            self._count_label.setText("0 个匹配")
        elif not self._cards:
            if self.store.projects:
                self._empty.setText("项目已全部隐藏\n可在「设置 → 项目管理」中开启显示")
            else:
                self._empty.setText("还没有项目\n点击上方「＋」新建项目")
            self._empty.setVisible(True)
            self._count_label.setText("")
        else:
            self._empty.setVisible(False)
            self._count_label.setText(f"匹配 {visible} 个" if keyword else f"{len(self._cards)} 个")

    def set_all_collapsed(self, collapsed: bool) -> None:
        for project in self.store.projects:
            project["collapsed"] = collapsed
        self.store.save()
        for card in self._cards:
            card.set_expanded(not collapsed)

    def clear_search(self) -> None:
        if self._search.text():
            self._search.clear()

    def _connect_card(self, card: ProjectCard) -> None:
        card.add_file_clicked.connect(self._show_add_menu)
        card.menu_requested.connect(self._show_project_menu)
        card.toggle_requested.connect(self._toggle_project)
        card.drag_started.connect(self._on_drag_started)
        card.file_clicked.connect(self._on_file_clicked)
        card.file_context.connect(self.file_context_requested)

    def set_selected_file(self, file_id) -> None:
        self._selected_file_id = file_id
        self._update_card_selection()

    def _update_card_selection(self) -> None:
        for card in self._cards:
            card.set_selected_file(self._selected_file_id)

    # ------------------------------------------------------------------ 交互
    def _on_file_clicked(self, file_id: str) -> None:
        self.set_selected_file(file_id)
        self.file_selected.emit(file_id)

    def _toggle_project(self, project_id: str) -> None:
        project = self.store.find_project(project_id)
        if not project:
            return
        project["collapsed"] = not project["collapsed"]
        self.store.save()
        for card in self._cards:
            if card.project_id == project_id:
                card.set_expanded(not project["collapsed"])

    def _show_add_menu(self, project_id: str, position: QPoint) -> None:
        menu = QMenu(self)
        existing = menu.addAction("选择已有文件…")
        create = menu.addAction("新建文件…")
        chosen = menu.exec(position)
        if chosen == existing:
            self.add_existing_requested.emit(project_id)
        elif chosen == create:
            self.create_new_requested.emit(project_id)

    def _show_project_menu(self, project_id: str, position: QPoint) -> None:
        project = self.store.find_project(project_id)
        if not project:
            return
        menu = QMenu(self)
        rename = menu.addAction("重命名项目")
        fields = menu.addAction("隐藏文件字段" if project["show_fields"] else "显示文件字段")
        menu.addSeparator()
        delete = menu.addAction("删除项目")
        chosen = menu.exec(position)
        if chosen == rename:
            self.rename_project_requested.emit(project_id)
        elif chosen == fields:
            self.toggle_fields_requested.emit(project_id)
        elif chosen == delete:
            self.delete_project_requested.emit(project_id)

    # ------------------------------------------------------------------ 拖拽
    def _on_drag_started(self, project_id: str) -> None:
        self._drag_project_id = project_id

    def _highlight_drop(self, index: int) -> None:
        total = len(self._cards)
        for i, card in enumerate(self._cards):
            side = ""
            if index == total and i == total - 1:
                side = "bottom"
            elif index < total and i == index:
                side = "top"
            card.set_drag_side(side)

    def _handle_drop(self, index: int) -> None:
        self._highlight_drop(-1)
        project_id = self._drag_project_id
        self._drag_project_id = None
        if project_id is not None:
            self.reorder_requested.emit(project_id, index)

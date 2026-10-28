"""右侧内容编辑区：自动保存、编码识别、行号显示。"""

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QTextFormat,
    QTextOption,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from core.textfile import describe_encoding, is_text_file, read_text, write_text
from core.utils import human_size, reveal_in_explorer

from .widgets import ElidedLabel, ask_confirm, repolish


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """带行号与当前行高亮的纯文本编辑器。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContentEditor")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)

        font = QFont()
        font.setFamilies(["Consolas", "Microsoft YaHei Mono", "Courier New"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        self.setTabStopDistance(QFontMetricsF(font).horizontalAdvance(" ") * 4)
        self.document().setDocumentMargin(14)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_number_width(0)
        self._highlight_current_line()

    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 20 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self, _count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width(0)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(rect.left(), rect.top(), self.line_number_area_width(), rect.height())
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#fbfcfe"))
        painter.setPen(QColor("#edf0f6"))
        painter.drawLine(
            self.line_number_area.width() - 1,
            event.rect().top(),
            self.line_number_area.width() - 1,
            event.rect().bottom(),
        )

        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        painter.setFont(self.font())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#3b6ef6") if number == current else QColor("#aab2c2"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 9,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            number += 1

    def _highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#f5f8ff"))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


class EditorPanel(QWidget):
    saved = Signal(str, str)  # 路径, 文件 id
    save_failed = Signal(str, str)
    remove_requested = Signal(str)
    relocated = Signal(str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self._entry = None
        self._encoding = "utf-8"
        self._dirty = False
        self._loading = False
        self._readonly = False
        self._project_name = ""

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self.save_now)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_empty_state())
        self._stack.addWidget(self._build_editor_card())
        self._stack.setCurrentIndex(0)
        root.addWidget(self._stack)

    # ------------------------------------------------------------------ 界面构建
    def _build_empty_state(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("EmptyState")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addStretch(1)

        badge = QLabel("TXT")
        badge.setObjectName("EmptyBadge")
        badge.setFixedSize(88, 88)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("未选择文件")
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("在左侧选择一个文件，即可在这里查看与编辑，修改后自动保存")
        hint.setObjectName("EmptyHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addStretch(1)
        return widget

    def _build_editor_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("EditorCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ---- 头部
        header = QWidget()
        header.setObjectName("EditorHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 13, 18, 11)
        header_layout.setSpacing(5)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._title = ElidedLabel("")
        self._title.setObjectName("EditorTitle")
        title_row.addWidget(self._title, 1)

        self._project_chip = QLabel("")
        self._project_chip.setObjectName("EditorProject")
        title_row.addWidget(self._project_chip)

        self._status = QLabel("")
        self._status.setObjectName("StatusChip")
        self._status.setProperty("state", "idle")
        title_row.addWidget(self._status)
        header_layout.addLayout(title_row)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._path_label = ElidedLabel("", Qt.TextElideMode.ElideMiddle)
        self._path_label.setObjectName("EditorPath")
        path_row.addWidget(self._path_label, 1)

        reload_button = QPushButton("重新加载")
        reload_button.setProperty("role", "link")
        reload_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reload_button.clicked.connect(self._reload_from_disk)
        path_row.addWidget(reload_button)

        reveal_button = QPushButton("打开所在位置")
        reveal_button.setProperty("role", "link")
        reveal_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reveal_button.clicked.connect(self._reveal_file)
        path_row.addWidget(reveal_button)
        header_layout.addLayout(path_row)

        card_layout.addWidget(header)

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background:#eef1f7; border:none;")
        card_layout.addWidget(separator)

        # ---- 异常提示条
        self._banner = QFrame()
        self._banner.setObjectName("WarningBanner")
        banner_layout = QHBoxLayout(self._banner)
        banner_layout.setContentsMargins(12, 8, 10, 8)
        banner_layout.setSpacing(8)

        self._banner_label = QLabel("")
        self._banner_label.setObjectName("WarningText")
        self._banner_label.setWordWrap(True)
        banner_layout.addWidget(self._banner_label, 1)

        self._locate_button = QPushButton("重新定位文件")
        self._locate_button.setProperty("role", "link")
        self._locate_button.clicked.connect(self._locate_file)
        banner_layout.addWidget(self._locate_button)

        self._remove_button = QPushButton("从项目中移除")
        self._remove_button.setProperty("role", "link")
        self._remove_button.clicked.connect(self._request_remove)
        banner_layout.addWidget(self._remove_button)

        self._banner.setVisible(False)
        self._banner_wrap = QWidget()
        banner_wrap_layout = QVBoxLayout(self._banner_wrap)
        banner_wrap_layout.setContentsMargins(14, 10, 14, 0)
        banner_wrap_layout.setSpacing(0)
        banner_wrap_layout.addWidget(self._banner)
        self._banner_wrap.setVisible(False)
        card_layout.addWidget(self._banner_wrap)

        # ---- 编辑器
        self.editor = CodeEditor()
        self.editor.textChanged.connect(self._on_text_changed)
        card_layout.addWidget(self.editor, 1)

        # ---- 底部状态
        footer = QWidget()
        footer.setObjectName("EditorFooter")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 7, 18, 7)
        footer_layout.setSpacing(10)

        self._footer_left = QLabel("")
        self._footer_left.setObjectName("FooterText")
        footer_layout.addWidget(self._footer_left)
        footer_layout.addStretch(1)

        save_hint = QLabel("自动保存已开启（Ctrl+S 立即保存）")
        save_hint.setObjectName("FooterText")
        footer_layout.addWidget(save_hint)
        self._save_hint = save_hint
        card_layout.addWidget(footer)

        return card

    # ------------------------------------------------------------------ 打开文件
    def open_file(self, project: dict, entry: dict) -> None:
        if self._entry and self._entry["id"] != entry["id"]:
            self.save_now()

        self._entry = entry
        self._project_name = project["name"]
        self._project_chip.setText(project["name"])
        self._project_chip.setToolTip(project["name"])
        self._title.set_full_text(entry["name"])
        self._path_label.set_full_text(entry["path"])
        self._path_label.setToolTip(entry["path"])
        self._dirty = False
        self._save_timer.stop()
        self._stack.setCurrentIndex(1)

        path = Path(entry["path"])
        if not path.exists():
            self._readonly = True
            self._set_editor_text("")
            self.editor.setReadOnly(True)
            self._set_status("error", "文件不存在")
            self._show_banner("文件不存在或已被移动，无法读取与保存。", actions=True)
            self._update_footer()
            return

        if not is_text_file(str(path)):
            self._readonly = True
            self._encoding = ""
            self._save_timer.stop()
            self.editor.setReadOnly(True)
            self._set_editor_text(self._readonly_placeholder(path))
            self._set_status("idle", "只读")
            self._show_banner("该文件不是文本文件，不支持编辑，仅可查看文件信息。", actions=False)
            self._save_hint.setText("只读预览模式")
            self._update_footer()
            return

        try:
            text, encoding = read_text(str(path))
        except OSError as exc:
            self._readonly = True
            self._set_editor_text("")
            self.editor.setReadOnly(True)
            self._set_status("error", "读取失败")
            self._show_banner(f"读取失败：{exc}", actions=True)
            self._update_footer()
            return

        self._readonly = False
        self._encoding = encoding
        self.store.set_file_encoding(entry["id"], encoding)
        self.editor.setReadOnly(False)
        self._set_editor_text(text)
        self._hide_banner()
        self._set_status("idle", "已加载")
        self._save_hint.setText("自动保存已开启（Ctrl+S 立即保存）")
        self._update_footer()
        self.editor.setFocus()

    def clear_view(self) -> None:
        self._save_timer.stop()
        self._entry = None
        self._dirty = False
        self._stack.setCurrentIndex(0)

    def current_file_id(self):
        return self._entry["id"] if self._entry else None

    def current_entry(self):
        return self._entry

    def update_project_name(self, name: str) -> None:
        if self._entry is None:
            return
        self._project_name = name
        self._project_chip.setText(name)
        self._project_chip.setToolTip(name)

    # ------------------------------------------------------------------ 编辑/保存
    def _set_editor_text(self, text: str) -> None:
        self._loading = True
        self.editor.setPlainText(text)
        self._loading = False
        self.editor.document().setModified(False)

    @staticmethod
    def _readonly_placeholder(path: Path) -> str:
        try:
            size = human_size(path.stat().st_size)
        except OSError:
            size = "未知"
        kind = path.suffix.lower().lstrip(".").upper() or "未知类型"
        return (
            "该文件不是文本文件，无法在这里预览或编辑。\n\n"
            f"文件类型：{kind}\n"
            f"文件大小：{size}\n"
            f"文件路径：{path}\n\n"
            "可点击上方「打开所在位置」，用系统默认程序查看该文件。"
        )

    def _on_text_changed(self) -> None:
        if self._loading:
            return
        self._update_footer()
        if self.editor.isReadOnly() or self._entry is None:
            return
        self._dirty = True
        self._set_status("dirty", "编辑中…")
        self._save_timer.start()

    def flush(self) -> None:
        self.save_now()

    def save_now(self) -> bool:
        self._save_timer.stop()
        if self._entry is None or not self._dirty or self.editor.isReadOnly():
            return False
        path = Path(self._entry["path"])
        try:
            write_text(str(path), self.editor.toPlainText(), self._encoding)
        except (OSError, UnicodeEncodeError) as exc:
            self._dirty = True
            self._set_status("error", "保存失败")
            self._show_banner(f"保存失败：{exc}", actions=False)
            self.save_failed.emit(str(path), str(exc))
            return False

        self._dirty = False
        self.editor.document().setModified(False)
        self._hide_banner()
        self._set_status("saved", "已保存 " + datetime.now().strftime("%H:%M:%S"))
        self.saved.emit(str(path), self._entry["id"])
        return True

    def _set_status(self, state: str, text: str) -> None:
        self._status.setProperty("state", state)
        self._status.setText(text)
        repolish(self._status)

    def _update_footer(self) -> None:
        if self._readonly:
            size = ""
            if self._entry:
                try:
                    size = " · 大小 " + human_size(Path(self._entry["path"]).stat().st_size)
                except OSError:
                    size = ""
            self._footer_left.setText("只读 · 不可编辑" + size)
            return
        text = self.editor.toPlainText()
        self._footer_left.setText(
            f"编码 {describe_encoding(self._encoding)}  ·  "
            f"{self.editor.blockCount()} 行  ·  {len(text)} 字符"
        )

    # ------------------------------------------------------------------ 提示条
    def _show_banner(self, text: str, actions: bool) -> None:
        self._banner_label.setText(text)
        self._locate_button.setVisible(actions)
        self._remove_button.setVisible(actions)
        self._banner.setVisible(True)
        self._banner_wrap.setVisible(True)

    def _hide_banner(self) -> None:
        self._banner.setVisible(False)
        self._banner_wrap.setVisible(False)

    # ------------------------------------------------------------------ 其他操作
    def _reload_from_disk(self) -> None:
        if self._entry is None:
            return
        if self._dirty:
            if not ask_confirm(
                self,
                "重新加载",
                "当前文件有未保存的修改，重新加载会丢弃这些修改，是否继续？",
            ):
                return
        self._dirty = False
        project, entry = self.store.find_file(self._entry["id"])
        if entry:
            self.open_file(project, entry)

    def _reveal_file(self) -> None:
        if self._entry:
            reveal_in_explorer(self._entry["path"])

    def _locate_file(self) -> None:
        if self._entry is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "重新定位文件",
            str(Path(self._entry["path"]).parent),
            "所有文件 (*.*);;文本文件 (*.txt *.md *.log *.json *.csv)",
        )
        if not path:
            return
        self._entry["path"] = os.path.abspath(path)
        self._entry["name"] = Path(path).name
        self._entry["encoding"] = ""
        self.store.save()
        file_id = self._entry["id"]
        project, entry = self.store.find_file(file_id)
        if entry:
            self.open_file(project, entry)
        self.relocated.emit(file_id)

    def _request_remove(self) -> None:
        if self._entry:
            self.remove_requested.emit(self._entry["id"])

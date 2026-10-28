"""通用小组件与对话框辅助函数。"""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QDialog,
    QInputDialog,
    QLabel,
    QMessageBox,
    QSizePolicy,
)


def repolish(widget) -> None:
    """动态属性变化后刷新样式。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def ask_text(parent, title: str, label: str, default: str = "") -> tuple:
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(default)
    dialog.setOkButtonText("确定")
    dialog.setCancelButtonText("取消")
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return dialog.textValue(), accepted


def ask_confirm(parent, title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Icon.Question)
    box.setText(text)
    confirm = box.addButton("确定", QMessageBox.ButtonRole.YesRole)
    box.addButton("取消", QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(confirm)
    box.exec()
    return box.clickedButton() is confirm


def notify(parent, title: str, text: str, warning: bool = False) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Icon.Warning if warning else QMessageBox.Icon.Information)
    box.setText(text)
    box.addButton("好", QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def chevrons_icon(up: bool, color: str = "#6b7488") -> QIcon:
    """绘制双向箭头图标：up 表示全部折叠，否则表示全部展开。"""
    size = 18
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    if up:
        shapes = [(9, 4), (9, 10)]
        offset = 4
    else:
        shapes = [(9, 13), (9, 7)]
        offset = -4
    for apex_x, apex_y in shapes:
        painter.drawPolyline(
            QPolygonF(
                [
                    QPointF(apex_x - 5, apex_y + offset),
                    QPointF(apex_x, apex_y),
                    QPointF(apex_x + 5, apex_y + offset),
                ]
            )
        )
    painter.end()
    return QIcon(pixmap)


class ElidedLabel(QLabel):
    """宽度不足时自动省略的标签。"""

    def __init__(self, text: str = "", mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle, parent=None):
        super().__init__(parent)
        self._full_text = text or ""
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self.setToolTip(self._full_text)
        self._apply_elide()

    def set_full_text(self, text: str) -> None:
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        self._apply_elide()

    def full_text(self) -> str:
        return self._full_text

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self) -> None:
        metrics = QFontMetrics(self.font())
        available = max(0, self.width() - 2 * self.margin())
        if available <= 0:
            elided = self._full_text
        else:
            elided = metrics.elidedText(self._full_text, self._mode, available)
        if elided != super().text():
            super().setText(elided)

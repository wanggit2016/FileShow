"""应用图标：运行时绘制，打包时由 make_icon.py 导出为 ico。"""

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)


def render_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # 圆角渐变底色
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#5f95ff"))
    gradient.setColorAt(1.0, QColor("#2b57d6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    radius = size * 0.24
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # 纸张
    paper = QRectF(size * 0.27, size * 0.20, size * 0.46, size * 0.60)
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(paper, size * 0.05, size * 0.05)

    # 文字行
    painter.setPen(QPen(QColor("#9db6ef"), max(1.0, size * 0.035)))
    line_x1 = paper.left() + size * 0.09
    line_x2 = paper.right() - size * 0.09
    for index, ratio in enumerate((0.30, 0.46, 0.62)):
        y = paper.top() + paper.height() * ratio
        width_ratio = 1.0 if index < 2 else 0.62
        painter.drawLine(
            line_x1,
            y,
            line_x1 + (line_x2 - line_x1) * width_ratio,
            y,
        )

    if size >= 48:
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", int(size * 0.20))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(0, size * 0.62, size, size * 0.3),
            Qt.AlignmentFlag.AlignCenter,
            "TXT",
        )

    painter.end()
    return image


def make_app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(render_icon(size)))
    return icon


def png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def build_ico(path: str) -> None:
    """生成多尺寸 ico 文件（内嵌 PNG 数据）。"""
    import struct

    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [png_bytes(render_icon(size)) for size in sizes]

    entries = bytearray()
    payload = bytearray()
    offset = 6 + 16 * len(sizes)
    for size, data in zip(sizes, images):
        dim = 0 if size == 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)

    with open(path, "wb") as fp:
        fp.write(struct.pack("<HHH", 0, 1, len(images)) + bytes(entries) + bytes(payload))

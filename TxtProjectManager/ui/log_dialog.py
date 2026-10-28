"""操作日志查看窗口。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.utils import reveal_in_explorer

from .widgets import ask_confirm


class LogViewerDialog(QDialog):
    def __init__(self, log, parent=None):
        super().__init__(parent)
        self.log = log
        self.setWindowTitle("操作日志")
        self.resize(820, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索操作或详情，例如：添加文件")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_button)

        clear_button = QPushButton("清空日志")
        clear_button.setProperty("role", "danger")
        clear_button.clicked.connect(self._clear)
        toolbar.addWidget(clear_button)

        open_button = QPushButton("打开日志文件")
        open_button.clicked.connect(lambda: reveal_in_explorer(str(self.log.path)))
        toolbar.addWidget(open_button)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["时间", "操作", "详情"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 172)
        self.table.setColumnWidth(1, 120)
        layout.addWidget(self.table, 1)

        self.status = QLabel("")
        self.status.setObjectName("HintLabel")
        layout.addWidget(self.status)

        self.refresh()

    def refresh(self) -> None:
        keyword = self.search.text().strip()
        entries = self.log.read(keyword=keyword)
        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(
                (entry.get("time", ""), entry.get("action", ""), entry.get("detail", ""))
            ):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, column, item)

        suffix = "（操作日志记录已关闭，不会产生新记录）" if not self.log.enabled else ""
        if keyword:
            self.status.setText(f"匹配到 {len(entries)} 条记录 {suffix}")
        elif entries:
            self.status.setText(f"共显示最近 {len(entries)} 条记录 {suffix}")
        else:
            self.status.setText("暂无日志记录 " + suffix)

    def _clear(self) -> None:
        if not ask_confirm(self, "清空日志", "确定清空全部操作日志？该操作不可撤销。"):
            return
        self.log.clear()
        self.log.record("清空操作日志", "")
        self.refresh()

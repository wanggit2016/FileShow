"""全局样式表与主题。"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

COLORS = {
    "bg": "#f3f5f9",
    "panel": "#ffffff",
    "border": "#e6e9f1",
    "text": "#1c2430",
    "muted": "#8b93a3",
    "accent": "#3b6ef6",
    "accent_dark": "#2f5fe0",
}

QSS = """
QWidget {
    color: #1c2430;
    font-size: 13px;
}
QMainWindow, QWidget#Root, QDialog { background: #f3f5f9; }

/* ---------- 顶部栏 ---------- */
QWidget#Header {
    background: #ffffff;
    border-bottom: 1px solid #e6e9f1;
}
QLabel#BrandBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5f95ff, stop:1 #2f5fe0);
    border-radius: 9px;
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
}
QLabel#AppTitle { font-size: 16px; font-weight: 600; color: #1a2231; }
QLabel#AppSubtitle { font-size: 11px; color: #98a1b2; }

/* ---------- 按钮 ---------- */
QPushButton {
    background: #ffffff;
    border: 1px solid #e2e6ef;
    border-radius: 7px;
    padding: 6px 14px;
    color: #3c4557;
}
QPushButton:hover { background: #f4f7fd; border-color: #cfd8ea; color: #2f5fe0; }
QPushButton:pressed { background: #e9eefb; }
QPushButton:disabled { color: #b6bdca; border-color: #eef1f7; background: #fafbfd; }

QPushButton[role="primary"] {
    background: #3b6ef6; border: 1px solid #3b6ef6; color: #ffffff; font-weight: 600;
}
QPushButton[role="primary"]:hover { background: #2f5fe0; border-color: #2f5fe0; color: #ffffff; }
QPushButton[role="primary"]:pressed { background: #2851c4; }
QPushButton[role="danger"] { color: #d3383e; border-color: #f3cdcd; background: #fff7f7; }
QPushButton[role="danger"]:hover { background: #fdeeee; border-color: #eab6b8; color: #c62b30; }
QPushButton[role="link"] {
    background: transparent; border: none; color: #3b6ef6; padding: 3px 6px; font-size: 12px;
}
QPushButton[role="link"]:hover { color: #2f5fe0; background: #eef3ff; border-radius: 6px; }
QPushButton[role="icon"] {
    background: transparent; border: none; border-radius: 7px; padding: 4px 7px;
    color: #6b7488; font-size: 15px;
}
QPushButton[role="icon"]:hover { background: #eef2fb; color: #2f5fe0; }
QPushButton#AddFileButton {
    background: transparent; border: none; color: #3b6ef6;
    font-size: 11px; padding: 2px 5px; border-radius: 5px;
}
QPushButton#AddFileButton:hover { background: #eaf0ff; color: #2f5fe0; }

/* ---------- 左侧栏 ---------- */
QWidget#Sidebar { background: #ffffff; border-right: 1px solid #e6e9f1; }
QWidget#SidebarHeader { background: #ffffff; border-bottom: 1px solid #eef1f7; }
QWidget#SidebarSearchWrap { background: #ffffff; border-bottom: 1px solid #eef1f7; }
QLineEdit#SidebarSearch {
    background: #f5f7fb; border: 1px solid #e7eaf2; border-radius: 8px;
    padding: 4px 9px; font-size: 12px; color: #2b3446;
}
QLineEdit#SidebarSearch:focus { border-color: #b9cdfb; background: #ffffff; }
QLabel#SidebarTitle { font-size: 12px; font-weight: 600; color: #5b6472; letter-spacing: 2px; }
QLabel#SidebarCount { font-size: 11px; color: #98a1b2; }
QScrollArea#SidebarScroll { background: transparent; border: none; }
QWidget#SidebarCanvas { background: transparent; }
QLabel#SidebarEmpty { color: #9aa3b2; font-size: 12px; }

QFrame#ProjectCard {
    background: #fbfcfe;
    border: 1px solid #edf0f6;
    border-radius: 10px;
}
QFrame#ProjectCard:hover { border-color: #dde4f2; background: #f8fafe; }
QFrame#ProjectCard[selected="true"] { background: #f4f8ff; border-color: #d5e2fb; }
QFrame#ProjectCard[dragSide="top"] { border-top: 2px solid #3b6ef6; }
QFrame#ProjectCard[dragSide="bottom"] { border-bottom: 2px solid #3b6ef6; }
QLabel#DragHandle { color: #c3cad8; font-size: 13px; }
QLabel#DragHandle:hover { color: #8e9bb3; }
QLabel#ProjectName { font-size: 13px; font-weight: 600; color: #1f2939; }
QLabel#ProjectCount {
    font-size: 10px; color: #929bab; background: #eef1f7;
    border-radius: 8px; padding: 1px 6px;
}
QLabel#CardHint { font-size: 11px; color: #a2aab9; }

QWidget#FileRow { background: transparent; border-radius: 7px; border-left: 2px solid transparent; }
QWidget#FileRow:hover { background: #eef3fc; }
QWidget#FileRow[selected="true"] { background: #e8efff; border-left: 2px solid #3b6ef6; }
QLabel#FileName { font-size: 12px; color: #3c4761; }
QLabel#FileName[selected="true"] { color: #234dc4; font-weight: 600; }
QLabel#FileMeta { font-size: 10px; color: #9ba4b4; }
QWidget#FileRow[missing="true"] QLabel#FileName { color: #c62b30; }

/* ---------- 右侧编辑区 ---------- */
QFrame#EditorCard { background: #ffffff; border: 1px solid #e6e9f1; border-radius: 12px; }
QWidget#EditorHeader { background: #ffffff; border-top-left-radius: 12px; border-top-right-radius: 12px; }
QLabel#EditorTitle { font-size: 15px; font-weight: 600; color: #1a2231; }
QLabel#EditorPath { font-size: 11px; color: #949dae; }
QLabel#EditorProject { font-size: 11px; color: #3b6ef6; background: #eef3ff;
    border-radius: 8px; padding: 2px 8px; }
QLabel#StatusChip { font-size: 11px; border-radius: 9px; padding: 3px 10px; }
QLabel#StatusChip[state="saved"] { color: #0d7a4d; background: #e8f7ef; }
QLabel#StatusChip[state="dirty"] { color: #9a6100; background: #fdf3e3; }
QLabel#StatusChip[state="error"] { color: #c62b30; background: #fdeceb; }
QLabel#StatusChip[state="idle"] { color: #7b8494; background: #f2f4f9; }
QWidget#EditorFooter { background: #fbfcfe; border-top: 1px solid #eef1f7;
    border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
QLabel#FooterText { font-size: 11px; color: #98a1b2; }
QPlainTextEdit#ContentEditor {
    border: none;
    background: #ffffff;
    selection-background-color: #cfe0ff;
    selection-color: #10203a;
}

QFrame#WarningBanner { background: #fff8e8; border: 1px solid #ffe3a8; border-radius: 8px; }
QLabel#WarningText { color: #8a5a00; font-size: 12px; }

QWidget#EmptyState { background: transparent; }
QLabel#EmptyBadge {
    background: #e9effc; color: #7b97e0; border-radius: 22px;
    font-size: 20px; font-weight: 700; letter-spacing: 1px;
}
QLabel#EmptyTitle { font-size: 15px; font-weight: 600; color: #47536b; }
QLabel#EmptyHint { font-size: 12px; color: #9aa3b2; }

/* ---------- 表单控件 ---------- */
QLineEdit, QSpinBox {
    background: #ffffff; border: 1px solid #e2e6ef; border-radius: 7px; padding: 6px 10px;
    selection-background-color: #cfe0ff;
}
QLineEdit:focus { border-color: #3b6ef6; }
QCheckBox { spacing: 8px; color: #3c4557; }

/* ---------- 表格 ---------- */
QTableWidget {
    background: #ffffff; border: none; gridline-color: #f1f3f8;
    selection-background-color: #e8efff; selection-color: #1c2430;
    alternate-background-color: #fbfcfe;
}
QTableWidget::item { padding: 4px 6px; border: none; }
QTableWidget::item:selected { background: #e8efff; color: #1c2430; }
QHeaderView::section {
    background: #f7f9fc; border: none; border-bottom: 1px solid #eceff5;
    padding: 7px 6px; color: #6b7488; font-weight: 600;
}
QTableCornerButton::section { background: #f7f9fc; border: none; }

/* ---------- 设置页 ---------- */
QTabWidget::pane { border: 1px solid #e6e9f1; border-radius: 10px; background: #ffffff; top: -1px; }
QTabBar::tab {
    background: transparent; color: #6b7488; padding: 8px 18px; margin-right: 4px;
    border: none; font-size: 13px;
}
QTabBar::tab:selected { color: #3b6ef6; font-weight: 600; border-bottom: 2px solid #3b6ef6; }
QTabBar::tab:hover:!selected { color: #2f5fe0; }
QLabel#FieldLabel { font-size: 12px; color: #6b7488; }
QLabel#HintLabel { font-size: 11px; color: #9aa3b2; }
QLabel#SectionTitle { font-size: 13px; font-weight: 600; color: #2b3446; }
QFrame#SettingRow { background: #fbfcfe; border: 1px solid #eef1f7; border-radius: 9px; }

/* ---------- 菜单 / 滚动条 / 提示 ---------- */
QMenu { background: #ffffff; border: 1px solid #e4e8f1; border-radius: 8px; padding: 5px; }
QMenu::item { padding: 7px 22px 7px 14px; border-radius: 6px; color: #3c4557; }
QMenu::item:selected { background: #eef3ff; color: #2f5fe0; }
QMenu::separator { height: 1px; background: #eef1f7; margin: 4px 8px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #d8dde8; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #c3cada; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #d8dde8; border-radius: 5px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

QSplitter::handle { background: transparent; }
QToolTip { background: #1f2937; color: #ffffff; border: none; padding: 5px 8px; }
"""


def apply_theme(app: QApplication) -> None:
    font = QFont()
    font.setFamilies(["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"])
    font.setPointSize(9)
    app.setFont(font)
    app.setStyleSheet(QSS)

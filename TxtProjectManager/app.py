"""TXT 分类管理器入口。"""

import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from core.activity_log import ActivityLog
from core.paths import APP_TITLE, app_data_dir
from core.store import ConfigStore
from ui.branding import make_app_icon
from ui.main_window import MainWindow
from ui.theme import apply_theme


def _install_excepthook() -> None:
    def hook(exc_type, exc_value, tb):
        message = "".join(traceback.format_exception(exc_type, exc_value, tb))
        if sys.stderr is not None:
            sys.stderr.write(message)
        try:
            with (app_data_dir() / "error.log").open("a", encoding="utf-8") as fp:
                fp.write(message + "\n")
        except OSError:
            pass
        if QApplication.instance() is not None:
            QMessageBox.critical(None, "程序异常", message[-1500:])

    sys.excepthook = hook


def main() -> None:
    _install_excepthook()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationDisplayName(APP_TITLE)
    app.setOrganizationName("TxtClassifyManager")
    app.setWindowIcon(make_app_icon())
    apply_theme(app)

    store = ConfigStore()
    log = ActivityLog(store)
    window = MainWindow(store, log)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

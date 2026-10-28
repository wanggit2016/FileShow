"""生成 exe 图标 assets/app.ico（构建时使用）。"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from ui.branding import build_ico  # noqa: E402


def main() -> None:
    app = QGuiApplication(sys.argv)
    target = Path(__file__).resolve().parent / "assets" / "app.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    build_ico(str(target))
    print(f"icon written: {target}")
    app.quit()


if __name__ == "__main__":
    main()

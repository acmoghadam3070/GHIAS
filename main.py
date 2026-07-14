#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
فایل اصلی اجرای نرم‌افزار
=============================================================================

اجرای این فایل، پنجره ورودی اصلی برنامه را باز می‌کند که از آنجا
می‌توان بین بخش‌های مختلف نرم‌افزار (بانک سؤالات، ارزیابی میدانی و...)
جابه‌جا شد.
=============================================================================
"""

import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "app"))
sys.path.insert(0, str(PROJECT_ROOT / "database"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from database import get_database  # noqa: E402
from question_designer import STYLE_SHEET  # noqa: E402
from main_window import LauncherWindow  # noqa: E402


def main() -> None:
    """راه‌اندازی برنامه GHIAS."""
    database = get_database()

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLE_SHEET)
    app.setFont(QFont("Tahoma", 10))

    window = LauncherWindow(database)
    window.show()

    exit_code = app.exec()
    database.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

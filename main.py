#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
فایل اصلی اجرای نرم‌افزار
=============================================================================

اجرای این فایل، اول صفحه ورود را نشان می‌دهد. بعد از ورود موفق، بر
اساس نقش کاربر (ادمین / ارزیاب / مصاحبه‌شونده)، صفحه ورودی مناسب باز
می‌شود.
=============================================================================
"""

import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "app"))
sys.path.insert(0, str(PROJECT_ROOT / "database"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QDialog

from database import get_database  # noqa: E402
from question_designer import STYLE_SHEET  # noqa: E402
from main_window import LauncherWindow  # noqa: E402
from login_window import LoginWindow  # noqa: E402
from auth_repository import AuthRepository  # noqa: E402

ICON_PATH = PROJECT_ROOT / "assets" / "icons" / "app_icon.png"


def main() -> None:
    """راه‌اندازی برنامه GHIAS."""
    database = get_database()

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLE_SHEET)
    app.setFont(QFont("Tahoma", 10))
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))

    auth_repository = AuthRepository(database)
    login_window = LoginWindow(auth_repository)

    if login_window.exec() != QDialog.Accepted or login_window.authenticated_user is None:
        database.close()
        sys.exit(0)

    current_user = login_window.authenticated_user

    window = LauncherWindow(database, current_user)
    window.show()

    exit_code = app.exec()
    database.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

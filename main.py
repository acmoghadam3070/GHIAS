#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
سامانه GHIAS
فایل اصلی اجرای نرم‌افزار
=============================================================================
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------
# Project Root
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# Project Imports
# ---------------------------------------------------------

from database.database import get_database
from app.question_designer import STYLE_SHEET
from app.main_window import LauncherWindow


# ---------------------------------------------------------
# Application Start
# ---------------------------------------------------------

def main():

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
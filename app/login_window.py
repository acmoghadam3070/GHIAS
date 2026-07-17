#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره ورود (Login Window)
=============================================================================

اولین پنجره‌ای که کاربر هنگام اجرای برنامه می‌بیند. بعد از ورود موفق،
اطلاعات کاربر (شامل نقش او) در اختیار بقیه برنامه قرار می‌گیرد تا بر
اساس نقش، فقط بخش‌های مجاز نمایش داده شوند.
=============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))
sys.path.insert(0, str(APP_DIR))

from auth_repository import AuthRepository  # noqa: E402

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LoginWindow(QDialog):
    """دیالوگ ورود به سامانه GHIAS."""

    def __init__(self, repository: AuthRepository):
        super().__init__()
        self.repository = repository
        self.authenticated_user: Optional[dict[str, Any]] = None

        self.setWindowTitle("ورود به سامانه قیاس (GHIAS)")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(380)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        title = QLabel("قیاس (GHIAS)")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1c2b3a;")
        layout.addWidget(title)

        subtitle = QLabel("سامانه ارزیابی هوشمند")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        layout.addWidget(QLabel("نام کاربری:"))
        self.username_edit = QLineEdit()
        layout.addWidget(self.username_edit)

        layout.addWidget(QLabel("رمز عبور:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.returnPressed.connect(self._on_login)
        layout.addWidget(self.password_edit)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #eb5757;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        login_button = QPushButton("ورود")
        login_button.setObjectName("PrimaryButton")
        login_button.clicked.connect(self._on_login)
        layout.addWidget(login_button)

    def _on_login(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self.error_label.setText("لطفاً نام کاربری و رمز عبور را وارد کنید.")
            return

        user = self.repository.authenticate(username, password)
        if user is None:
            self.error_label.setText("نام کاربری یا رمز عبور اشتباه است.")
            self.password_edit.clear()
            return

        self.authenticated_user = user
        self.accept()

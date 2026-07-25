#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره ورود (Login Window) - نسخه دوم
=============================================================================

جریان ورود در این نسخه دو یا سه مرحله دارد:
    ۱) نام کاربری + رمز عبور + کپچای تصویری
    ۲) اگر حساب ورود دومرحله‌ای فعال داشته باشد: وارد کردن کد پیامکی
    ۳) ورود موفق

اگر پنج بار رمز اشتباه وارد شود، حساب به‌مدت پنج دقیقه قفل می‌شود.
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
from captcha_utils import generate_captcha, verify_captcha  # noqa: E402

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

LOGO_PATH = PROJECT_ROOT / "assets" / "images" / "logo.png"

GLASS_STYLE = """
QDialog {
    background-color: #1c2b3a;
}
QFrame#GlassCard {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(201, 160, 74, 0.35);
    border-radius: 16px;
}
QLabel { color: #f4f6f8; }
QLabel#Title { font-size: 22px; font-weight: bold; color: #f2c94c; }
QLabel#Subtitle { color: #d7dee6; }
QLabel#ErrorLabel { color: #eb5757; font-weight: bold; }
QLineEdit {
    background-color: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(201, 160, 74, 0.5);
    border-radius: 8px;
    padding: 8px;
    color: #1c2b3a;
}
QPushButton#PrimaryButton {
    background-color: #c9a04a;
    color: #1c2b3a;
    border: none;
    border-radius: 8px;
    padding: 10px;
    font-weight: bold;
}
QPushButton#PrimaryButton:hover { background-color: #ddb662; }
QPushButton#LinkButton {
    background: transparent;
    color: #f2c94c;
    border: none;
    text-decoration: underline;
}
"""


class LoginWindow(QDialog):
    """دیالوگ ورود چندمرحله‌ای به سامانه GHIAS."""

    def __init__(self, repository: AuthRepository):
        super().__init__()
        self.repository = repository
        self.authenticated_user: Optional[dict[str, Any]] = None

        self.captcha_text = ""
        self.pending_user: Optional[dict[str, Any]] = None

        self.setWindowTitle("ورود به سامانه قیاس (GHIAS)")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setStyleSheet(GLASS_STYLE)

        self._build_ui()
        self._refresh_captcha()

    # ------------------------------------------------------------- ساخت رابط
    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("GlassCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(12)

        if LOGO_PATH.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(LOGO_PATH)).scaledToWidth(140, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(logo_label)

        title = QLabel("قیاس (GHIAS)")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("سامانه ارزیابی هوشمند")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(6)

        self.stacked = QStackedWidget()
        card_layout.addWidget(self.stacked)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        card_layout.addWidget(self.error_label)

        self._build_password_step()
        self._build_otp_step()

        outer_layout.addWidget(card)

    def _build_password_step(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(QLabel("نام کاربری:"))
        self.username_edit = QLineEdit()
        layout.addWidget(self.username_edit)

        layout.addWidget(QLabel("رمز عبور:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_edit)

        layout.addWidget(QLabel("کد امنیتی تصویر را وارد کنید:"))
        captcha_row = QHBoxLayout()
        self.captcha_image_label = QLabel()
        self.captcha_image_label.setFixedSize(180, 60)
        captcha_row.addWidget(self.captcha_image_label)

        refresh_button = QPushButton("↻")
        refresh_button.setFixedWidth(36)
        refresh_button.clicked.connect(self._refresh_captcha)
        captcha_row.addWidget(refresh_button)
        layout.addLayout(captcha_row)

        self.captcha_edit = QLineEdit()
        self.captcha_edit.setPlaceholderText("کد تصویر بالا")
        self.captcha_edit.returnPressed.connect(self._on_submit_password_step)
        layout.addWidget(self.captcha_edit)

        login_button = QPushButton("ورود")
        login_button.setObjectName("PrimaryButton")
        login_button.clicked.connect(self._on_submit_password_step)
        layout.addWidget(login_button)

        self.stacked.addWidget(page)

    def _build_otp_step(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        info = QLabel("یک کد یکبارمصرف برای شماره موبایل ثبت‌شده ارسال شد.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.otp_dev_label = QLabel("")
        self.otp_dev_label.setWordWrap(True)
        self.otp_dev_label.setStyleSheet("color: #f2c94c;")
        layout.addWidget(self.otp_dev_label)

        layout.addWidget(QLabel("کد پیامک‌شده را وارد کنید:"))
        self.otp_edit = QLineEdit()
        self.otp_edit.returnPressed.connect(self._on_submit_otp_step)
        layout.addWidget(self.otp_edit)

        confirm_button = QPushButton("تأیید و ورود")
        confirm_button.setObjectName("PrimaryButton")
        confirm_button.clicked.connect(self._on_submit_otp_step)
        layout.addWidget(confirm_button)

        resend_button = QPushButton("ارسال مجدد کد")
        resend_button.setObjectName("LinkButton")
        resend_button.clicked.connect(self._resend_otp)
        layout.addWidget(resend_button)

        self.stacked.addWidget(page)

    # ------------------------------------------------------------- کپچا
    def _refresh_captcha(self) -> None:
        self.captcha_text, image_bytes = generate_captcha()
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(image_bytes))
        self.captcha_image_label.setPixmap(pixmap)
        self.captcha_edit.clear()

    # ------------------------------------------------------------- مرحله رمز عبور
    def _on_submit_password_step(self) -> None:
        self.error_label.setText("")

        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        captcha_input = self.captcha_edit.text()

        if not username or not password or not captcha_input:
            self.error_label.setText("همه فیلدها را کامل کنید.")
            return

        if not verify_captcha(captcha_input, self.captcha_text):
            self.error_label.setText("کد امنیتی تصویر اشتباه است.")
            self._refresh_captcha()
            return

        result = self.repository.authenticate(username, password)

        if result.status == "locked":
            self.error_label.setText(
                "حساب شما به‌دلیل تلاش‌های ناموفق مکرر، موقتاً قفل شده است.\n"
                "لطفاً چند دقیقه دیگر دوباره تلاش کنید."
            )
            self._refresh_captcha()
            return

        if result.status == "invalid":
            remaining = result.remaining_attempts
            if remaining is not None:
                self.error_label.setText(
                    f"نام کاربری یا رمز عبور اشتباه است. ({remaining} تلاش باقی‌مانده)"
                )
            else:
                self.error_label.setText("نام کاربری یا رمز عبور اشتباه است.")
            self.password_edit.clear()
            self._refresh_captcha()
            return

        # result.status == "ok"
        user = result.user
        if self.repository.requires_two_factor(user):
            self.pending_user = user
            self.repository.generate_and_send_otp(user["id"])
            dev_code = self.repository.peek_last_otp(user["id"])
            self.otp_dev_label.setText(
                f"(حالت آزمایشی — پنل پیامک هنوز وصل نیست: کد شما {dev_code} است)"
            )
            self.stacked.setCurrentIndex(1)
            return

        self.authenticated_user = user
        self.accept()

    # ------------------------------------------------------------- مرحله OTP
    def _on_submit_otp_step(self) -> None:
        self.error_label.setText("")
        if self.pending_user is None:
            return

        code = self.otp_edit.text().strip()
        if not code:
            self.error_label.setText("کد را وارد کنید.")
            return

        if not self.repository.verify_otp(self.pending_user["id"], code):
            self.error_label.setText("کد وارد‌شده اشتباه یا منقضی است.")
            return

        self.authenticated_user = self.pending_user
        self.accept()

    def _resend_otp(self) -> None:
        if self.pending_user is None:
            return
        self.repository.generate_and_send_otp(self.pending_user["id"])
        dev_code = self.repository.peek_last_otp(self.pending_user["id"])
        self.otp_dev_label.setText(
            f"(حالت آزمایشی — پنل پیامک هنوز وصل نیست: کد شما {dev_code} است)"
        )
        self.error_label.setText("کد جدید ارسال شد.")

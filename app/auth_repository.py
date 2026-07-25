#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه داده احراز هویت و مدیریت کاربران (Auth Repository) - نسخه دوم
=============================================================================

این فایل مسئول موارد زیر است:
    - بررسی نام کاربری و رمز عبور هنگام ورود
    - قفل موقت حساب بعد از چند بار رمز اشتباه
    - ورود دومرحله‌ای با کد یکبارمصرف پیامکی (OTP)
    - مدیریت کاربران (افزودن، غیرفعال کردن، تغییر رمز عبور)

رمز عبور هرگز به‌صورت خام ذخیره نمی‌شود؛ با الگوریتم استاندارد PBKDF2
هش می‌شود.

نکته مهم برای آینده (نسخه وب): این فایل کاملاً مستقل از رابط گرافیکی
است. تمام منطق قفل حساب و OTP در همین‌جا نوشته شده تا وقتی نسخه وب
ساخته شد، بدون تغییر، پشت یک API قابل استفاده مجدد باشد.
=============================================================================
"""

from __future__ import annotations

import binascii
import hashlib
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from database import Database

PBKDF2_ITERATIONS = 100_000
VALID_ROLES = {"admin", "inspector", "interviewee"}

LOCKOUT_THRESHOLD = 5          # تعداد رمز اشتباه مجاز قبل از قفل شدن
LOCKOUT_MINUTES = 5            # مدت قفل حساب (دقیقه)
OTP_LENGTH = 6
OTP_VALID_MINUTES = 5          # مدت اعتبار کد یکبارمصرف


def hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    """هش کردن رمز عبور با PBKDF2. خروجی: (رشته هش، رشته salt) به‌صورت hex."""
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return binascii.hexlify(derived_key).decode(), binascii.hexlify(salt).decode()


# =============================================================================
# رابط استاندارد ارسال پیامک (تا وقتی پنل واقعی وصل شود)
# =============================================================================

class SMSProvider:
    """
    رابط پایه ارسال پیامک. برای اتصال یک پنل پیامک واقعی در آینده، کافی
    است یک کلاس جدید از همین کلاس بسازید و متد send_otp را با تماس
    واقعی به API پنل پیامک پر کنید؛ هیچ‌جای دیگر کد نیازی به تغییر ندارد.
    """

    def send_otp(self, phone_number: str, code: str) -> bool:
        raise NotImplementedError


class StubSMSProvider(SMSProvider):
    """
    نسخه آزمایشی: چون هنوز پنل پیامک واقعی وصل نیست، این کلاس پیامکی
    ارسال نمی‌کند؛ فقط کد را برمی‌گرداند تا در رابط کاربری مستقیم به
    کاربر نمایش داده شود (فقط برای تست، نه برای استفاده واقعی).
    """

    def send_otp(self, phone_number: str, code: str) -> bool:
        return True


# =============================================================================
# نتیجه ورود
# =============================================================================

@dataclass
class AuthResult:
    """
    نتیجه یک تلاش برای ورود. status یکی از این مقادیر است:
        "ok"              - نام کاربری و رمز عبور درست بود
        "invalid"         - نام کاربری یا رمز عبور اشتباه بود
        "locked"          - حساب به‌خاطر تلاش‌های ناموفق مکرر، موقتاً قفل است
    """

    status: str
    user: Optional[dict[str, Any]] = None
    locked_until: Optional[str] = None
    remaining_attempts: Optional[int] = None


class AuthRepository:
    """مسئول تمام عملیات پایگاه داده مربوط به کاربران، ورود، و OTP."""

    def __init__(self, db: Database, sms_provider: Optional[SMSProvider] = None):
        self.db = db
        self.sms_provider = sms_provider or StubSMSProvider()

    # ------------------------------------------------------------- ورود (رمز عبور)
    def authenticate(self, username: str, password: str) -> AuthResult:
        """
        بررسی نام کاربری و رمز عبور، همراه با منطق قفل حساب.
        این متد کد دومرحله‌ای (OTP) را بررسی نمی‌کند؛ اگر کاربر
        two_factor_enabled داشته باشد، مرحله بعد باید verify_otp
        فراخوانی شود.
        """
        user = self.db.query_one(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username.strip(),),
        )
        if user is None:
            return AuthResult(status="invalid")

        user = dict(user)

        if user["locked_until"]:
            locked_until = datetime.strptime(user["locked_until"], "%Y-%m-%d %H:%M:%S")
            if locked_until > datetime.now():
                return AuthResult(status="locked", locked_until=user["locked_until"])
            # زمان قفل تمام شده؛ شمارنده را ریست می‌کنیم
            self.db.execute(
                "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
                (user["id"],),
            )
            user["failed_login_attempts"] = 0
            user["locked_until"] = None

        computed_hash, _ = hash_password(password, user["password_salt"])
        if computed_hash != user["password_hash"]:
            attempts = (user["failed_login_attempts"] or 0) + 1
            if attempts >= LOCKOUT_THRESHOLD:
                locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
                self.db.execute(
                    "UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?",
                    (attempts, locked_until.strftime("%Y-%m-%d %H:%M:%S"), user["id"]),
                )
                return AuthResult(status="locked", locked_until=locked_until.strftime("%Y-%m-%d %H:%M:%S"))

            self.db.execute(
                "UPDATE users SET failed_login_attempts = ? WHERE id = ?", (attempts, user["id"])
            )
            return AuthResult(status="invalid", remaining_attempts=LOCKOUT_THRESHOLD - attempts)

        # ورود موفق: ریست شمارنده و ثبت زمان ورود
        self.db.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_until = NULL, "
            "last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user["id"],),
        )
        return AuthResult(status="ok", user=user)

    # ------------------------------------------------------------- ورود دومرحله‌ای (OTP)
    def requires_two_factor(self, user: dict[str, Any]) -> bool:
        return bool(user.get("two_factor_enabled")) and bool(user.get("phone_number"))

    def generate_and_send_otp(self, user_id: int) -> bool:
        """ساخت یک کد یکبارمصرف تازه و تلاش برای ارسال آن از طریق پیامک."""
        user = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if user is None or not user["phone_number"]:
            return False

        code = "".join(random.choices("0123456789", k=OTP_LENGTH))
        expires_at = datetime.now() + timedelta(minutes=OTP_VALID_MINUTES)
        self.db.execute(
            "UPDATE users SET otp_code = ?, otp_expires_at = ? WHERE id = ?",
            (code, expires_at.strftime("%Y-%m-%d %H:%M:%S"), user_id),
        )
        return self.sms_provider.send_otp(user["phone_number"], code)

    def peek_last_otp(self, user_id: int) -> Optional[str]:
        """
        فقط برای حالت آزمایشی (وقتی پنل پیامک واقعی وصل نیست): آخرین
        کد ساخته‌شده را برمی‌گرداند تا در رابط کاربری نمایش داده شود.
        """
        user = self.db.query_one("SELECT otp_code FROM users WHERE id = ?", (user_id,))
        return user["otp_code"] if user else None

    def verify_otp(self, user_id: int, code: str) -> bool:
        user = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if user is None or not user["otp_code"] or not user["otp_expires_at"]:
            return False

        expires_at = datetime.strptime(user["otp_expires_at"], "%Y-%m-%d %H:%M:%S")
        if expires_at < datetime.now():
            return False

        if code.strip() != user["otp_code"]:
            return False

        self.db.execute(
            "UPDATE users SET otp_code = NULL, otp_expires_at = NULL WHERE id = ?", (user_id,)
        )
        return True

    # ------------------------------------------------------------- مدیریت کاربران
    def list_users(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, username, full_name, role, phone_number, two_factor_enabled, "
            "is_active, last_login_at FROM users ORDER BY username"
        )
        return [dict(row) for row in rows]

    def add_user(
        self, username: str, password: str, full_name: str, role: str,
        phone_number: str = "", two_factor_enabled: bool = False,
    ) -> int:
        if role not in VALID_ROLES:
            raise ValueError(f"نقش نامعتبر است: {role}")

        existing = self.db.query_one(
            "SELECT id FROM users WHERE username = ?", (username.strip(),)
        )
        if existing is not None:
            raise ValueError(f"نام کاربری «{username}» قبلاً استفاده شده است.")

        if two_factor_enabled and not phone_number.strip():
            raise ValueError("برای فعال‌سازی ورود دومرحله‌ای، شماره موبایل الزامی است.")

        password_hash, password_salt = hash_password(password)
        return self.db.execute(
            """
            INSERT INTO users (
                username, password_hash, password_salt, full_name, role,
                phone_number, two_factor_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username.strip(), password_hash, password_salt, full_name.strip(), role,
                phone_number.strip() or None, 1 if two_factor_enabled else 0,
            ),
        )

    def set_active(self, user_id: int, is_active: bool) -> None:
        self.db.execute(
            "UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id)
        )

    def change_password(self, user_id: int, new_password: str) -> None:
        password_hash, password_salt = hash_password(new_password)
        self.db.execute(
            "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
            (password_hash, password_salt, user_id),
        )

    def change_role(self, user_id: int, role: str) -> None:
        if role not in VALID_ROLES:
            raise ValueError(f"نقش نامعتبر است: {role}")
        self.db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))

    def unlock_account(self, user_id: int) -> None:
        """باز کردن دستی قفل یک حساب توسط ادمین، بدون نیاز به صبر کردن."""
        self.db.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
            (user_id,),
        )

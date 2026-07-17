#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه داده احراز هویت و مدیریت کاربران (Auth Repository)
=============================================================================

این فایل مسئول موارد زیر است:
    - بررسی نام کاربری و رمز عبور هنگام ورود
    - مدیریت کاربران (افزودن، غیرفعال کردن، تغییر رمز عبور)

رمز عبور هرگز به‌صورت خام ذخیره نمی‌شود؛ با الگوریتم استاندارد PBKDF2
(بخشی از کتابخانه اصلی پایتون، بدون نیاز به نصب هیچ پکیج جانبی) هش
می‌شود.

سه نقش تعریف‌شده:
    admin       - دسترسی کامل به تمام بخش‌های نرم‌افزار
    inspector   - فقط دسترسی به بخش ارزیابی میدانی
    interviewee - فقط دسترسی به پاسخ‌دهی سؤالات (جزئیات این نقش هنوز
                  نهایی نشده و در نسخه‌های بعدی تکمیل می‌شود)
=============================================================================
"""

from __future__ import annotations

import binascii
import hashlib
import os
from typing import Any, Optional

from database import Database

PBKDF2_ITERATIONS = 100_000

VALID_ROLES = {"admin", "inspector", "interviewee"}


def hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    """
    هش کردن یک رمز عبور. اگر salt داده نشود، یک salt تصادفی تازه ساخته
    می‌شود (برای ثبت کاربر جدید). اگر salt داده شود، همان salt برای
    مقایسه در فرآیند ورود استفاده می‌شود.
    خروجی: (رشته هش، رشته salt) هر دو به‌صورت hex.
    """
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return binascii.hexlify(derived_key).decode(), binascii.hexlify(salt).decode()


class AuthRepository:
    """مسئول تمام عملیات پایگاه داده مربوط به کاربران و ورود."""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------- ورود
    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        """
        بررسی نام کاربری و رمز عبور. در صورت درست بودن، اطلاعات کاربر
        بازگردانده می‌شود؛ در غیر این صورت None.
        """
        user = self.db.query_one(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username.strip(),),
        )
        if user is None:
            return None

        computed_hash, _ = hash_password(password, user["password_salt"])
        if computed_hash != user["password_hash"]:
            return None

        self.db.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],)
        )
        return dict(user)

    # ------------------------------------------------------------- مدیریت کاربران
    def list_users(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, username, full_name, role, is_active, last_login_at "
            "FROM users ORDER BY username"
        )
        return [dict(row) for row in rows]

    def add_user(self, username: str, password: str, full_name: str, role: str) -> int:
        if role not in VALID_ROLES:
            raise ValueError(f"نقش نامعتبر است: {role}")

        existing = self.db.query_one(
            "SELECT id FROM users WHERE username = ?", (username.strip(),)
        )
        if existing is not None:
            raise ValueError(f"نام کاربری «{username}» قبلاً استفاده شده است.")

        password_hash, password_salt = hash_password(password)
        return self.db.execute(
            """
            INSERT INTO users (username, password_hash, password_salt, full_name, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username.strip(), password_hash, password_salt, full_name.strip(), role),
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

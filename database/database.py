#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه اتصال به پایگاه داده
=============================================================================

این فایل مسئول موارد زیر است:
    - ساخت اتصال به فایل پایگاه داده SQLite
    - اجرای فایل create_database.sql برای ساخت جداول (در صورت نبودن)
    - فراهم کردن یک کلاس Database ساده برای استفاده در بقیه برنامه

هیچ بخش دیگری از برنامه نباید مستقیماً sqlite3 را وارد کند؛ همه باید از
طریق کلاس Database این فایل با پایگاه داده کار کنند.
=============================================================================
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


# مسیر پوشه‌ی database (همان پوشه‌ای که این فایل در آن قرار دارد)
BASE_DIR: Path = Path(__file__).resolve().parent

# مسیر فایل پایگاه داده اصلی برنامه
DB_PATH: Path = BASE_DIR / "GHIAS_SECURITY_ASSESSMENT.db"

# مسیر فایل اسکیمای پایگاه داده
SCHEMA_PATH: Path = BASE_DIR / "create_database.sql"


class Database:
    """
    کلاس مدیریت اتصال به پایگاه داده SQLite.

    استفاده:
        db = Database()
        db.initialize()          # ساخت جداول در صورت نبودن
        rows = db.query("SELECT * FROM categories")
    """

    def __init__(self, db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self._connection: sqlite3.Connection | None = None

    # ------------------------------------------------------------ اتصال
    def connect(self) -> sqlite3.Connection:
        """
        برقراری اتصال به پایگاه داده (در صورت نبودن اتصال قبلی).
        Row factory طوری تنظیم شده که هر ردیف مثل دیکشنری قابل دسترسی باشد.
        """
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON;")
        return self._connection

    def close(self) -> None:
        """بستن اتصال جاری، در صورت باز بودن."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    # ------------------------------------------------------------ ساخت جداول
    def initialize(self) -> None:
        """
        اجرای فایل create_database.sql روی پایگاه داده.
        این عملیات کاملاً بی‌خطر است و می‌تواند چندین‌بار اجرا شود؛
        جدول‌های موجود دوباره ساخته نمی‌شوند (به‌خاطر IF NOT EXISTS).
        """
        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"فایل اسکیمای پایگاه داده پیدا نشد:\n{self.schema_path}"
            )

        sql_script = self.schema_path.read_text(encoding="utf-8")
        connection = self.connect()
        connection.executescript(sql_script)
        connection.commit()

    # ------------------------------------------------------------ عملیات پایه
    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        """اجرای یک پرس‌وجوی SELECT و بازگرداندن تمام ردیف‌ها."""
        connection = self.connect()
        cursor = connection.execute(sql, params)
        return cursor.fetchall()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        """اجرای یک پرس‌وجوی SELECT و بازگرداندن فقط اولین ردیف."""
        connection = self.connect()
        cursor = connection.execute(sql, params)
        return cursor.fetchone()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        """
        اجرای یک دستور INSERT/UPDATE/DELETE.
        شناسه ردیف تازه درج‌شده (lastrowid) بازگردانده می‌شود.
        """
        connection = self.connect()
        cursor = connection.execute(sql, params)
        connection.commit()
        return cursor.lastrowid

    # ------------------------------------------------------------ کمکی برای دیباگ
    def table_names(self) -> list[str]:
        """بازگرداندن نام تمام جداول موجود در پایگاه داده (برای بررسی/دیباگ)."""
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [row["name"] for row in rows]


def get_database() -> Database:
    """
    ساخت و آماده‌سازی یک نمونه از کلاس Database.
    این تابع باید در سراسر برنامه برای دسترسی به پایگاه داده استفاده شود.
    """
    db = Database()
    db.initialize()
    return db


# =============================================================================
# اجرای مستقیم این فایل: ساخت اولیه پایگاه داده و نمایش وضعیت آن
# =============================================================================

if __name__ == "__main__":
    database = get_database()
    tables = database.table_names()

    print("پایگاه داده با موفقیت ساخته/بررسی شد.")
    print(f"مسیر فایل: {database.db_path}")
    print(f"تعداد جداول ساخته‌شده: {len(tables)}")
    for table_name in tables:
        print(f"  - {table_name}")

    database.close()

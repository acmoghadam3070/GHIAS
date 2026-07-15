#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
اسکریپت مهاجرت نسخه دوم پایگاه داده: پشتیبانی از چند نوع سازمان (نسخه اصلاح‌شده)
=============================================================================

این نسخه اصلاح‌شده، هر مرحله را جداگانه و با احتیاط بررسی می‌کند، حتی اگر
یک تلاش قبلی برای مهاجرت، ناقص یا ناموفق مانده باشد (مثلاً به‌خاطر اجرای
اشتباهی create_database.sql روی یک پایگاه داده قدیمی).

این اسکریپت هرگز داده‌ای که حداقل یک رکورد دارد را حذف نمی‌کند؛ فقط
جدول‌های ناقص و کاملاً خالی که از یک تلاش نافرجام باقی مانده باشند را
پاک‌سازی می‌کند تا مهاجرت واقعی بتواند به‌درستی انجام شود.
=============================================================================
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH: Path = Path(__file__).resolve().parent / "GHIAS_SECURITY_ASSESSMENT.db"


def table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def column_exists(con: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def row_count(con: sqlite3.Connection, table_name: str) -> int:
    return con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def main() -> None:
    if not DB_PATH.exists():
        print(f"فایل پایگاه داده پیدا نشد: {DB_PATH}")
        return

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA foreign_keys = OFF")

    hospitals_exists = table_exists(con, "hospitals")
    facilities_exists = table_exists(con, "facilities")

    # ------------------------------------------------------------- حالت ۱: مهاجرت کامل قبلاً انجام شده
    if not hospitals_exists and facilities_exists:
        print("این پایگاه داده قبلاً به مدل چند نوع سازمان مهاجرت کرده است.")
        print("نیازی به هیچ تغییری نیست.")
        con.close()
        return

    # ------------------------------------------------------------- حالت ۲: نه hospitals و نه facilities پیدا شد
    if not hospitals_exists and not facilities_exists:
        print("هیچ‌کدام از جدول‌های hospitals یا facilities پیدا نشد.")
        print("این وضعیت غیرمنتظره است؛ لطفاً قبل از ادامه با من هماهنگ کنید.")
        con.close()
        return

    # ------------------------------------------------------------- حالت ۳: پاک‌سازی باقیمانده تلاش ناموفق قبلی
    print("=" * 60)
    print("شروع مهاجرت پایگاه داده به مدل چند نوع سازمان")
    print("=" * 60)

    if facilities_exists:
        count = row_count(con, "facilities")
        if count == 0:
            con.execute("DROP TABLE facilities")
            con.commit()
            print("یک جدول facilities خالی و ناقص (باقی‌مانده از تلاش قبلی) پاک‌سازی شد.")
        else:
            print(
                f"توقف ایمنی: جدول facilities از قبل {count} رکورد دارد و جدول hospitals "
                "هم هنوز وجود دارد. برای جلوگیری از خطر از دست رفتن داده، ادامه نمی‌دهم. "
                "لطفاً این وضعیت را برای من گزارش کنید تا بررسی کنم."
            )
            con.close()
            return

    if table_exists(con, "facility_types"):
        count = row_count(con, "facility_types")
        if count == 0:
            con.execute("DROP TABLE facility_types")
            con.commit()
            print("یک جدول facility_types خالی و ناقص پاک‌سازی شد.")

    # ------------------------------------------------------------- ۱. انواع سازمان
    con.execute(
        """
        CREATE TABLE facility_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_key TEXT UNIQUE NOT NULL,
            type_name TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute(
        "INSERT INTO facility_types (type_key, type_name) VALUES ('hospital', 'بیمارستان')"
    )
    con.commit()
    print("جدول facility_types ساخته شد و نوع «بیمارستان» ثبت شد.")

    hospital_type_id = con.execute(
        "SELECT id FROM facility_types WHERE type_key = 'hospital'"
    ).fetchone()[0]

    # ------------------------------------------------------------- ۲. جدول facilities
    con.execute("ALTER TABLE hospitals RENAME TO facilities")

    if not column_exists(con, "facilities", "facility_name"):
        con.execute("ALTER TABLE facilities RENAME COLUMN hospital_name TO facility_name")
    if not column_exists(con, "facilities", "facility_code"):
        con.execute("ALTER TABLE facilities RENAME COLUMN hospital_code TO facility_code")
    if not column_exists(con, "facilities", "facility_type_id"):
        con.execute(
            "ALTER TABLE facilities ADD COLUMN facility_type_id INTEGER REFERENCES facility_types(id)"
        )
    con.execute(
        "UPDATE facilities SET facility_type_id = ? WHERE facility_type_id IS NULL",
        (hospital_type_id,),
    )
    con.commit()
    print("جدول hospitals با موفقیت به facilities تبدیل شد.")

    # ------------------------------------------------------------- ۳. حوزه‌ها
    if not column_exists(con, "categories", "facility_type_id"):
        con.execute(
            "ALTER TABLE categories ADD COLUMN facility_type_id INTEGER REFERENCES facility_types(id)"
        )
    con.execute(
        "UPDATE categories SET facility_type_id = ? WHERE facility_type_id IS NULL",
        (hospital_type_id,),
    )
    con.commit()
    print("حوزه‌های موجود به نوع «بیمارستان» متصل شدند.")

    # ------------------------------------------------------------- ۴. بازدیدها
    if not column_exists(con, "visits", "facility_id"):
        con.execute("ALTER TABLE visits RENAME COLUMN hospital_id TO facility_id")
    con.commit()
    print("جدول visits به‌روزرسانی شد.")

    con.execute("PRAGMA foreign_keys = ON")
    con.close()

    print("=" * 60)
    print("مهاجرت با موفقیت و بدون از دست رفتن هیچ داده‌ای انجام شد.")
    print("=" * 60)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
اسکریپت مهاجرت نسخه دوم پایگاه داده: پشتیبانی از چند نوع سازمان
=============================================================================

این اسکریپت پایگاه داده موجود شما را از حالت «فقط بیمارستان» به یک مدل
عمومی‌تر تبدیل می‌کند که در آینده می‌تواند کارخانه، اداره و سایر انواع
سازمان را هم پشتیبانی کند.

تغییرات انجام‌شده:
    - ساخت جدول جدید facility_types (انواع سازمان): بیمارستان به‌عنوان
      اولین نوع، به‌طور خودکار ثبت می‌شود.
    - تغییر نام جدول hospitals به facilities.
    - تغییر نام ستون hospital_name به facility_name.
    - افزودن ستون facility_type_id به جدول facilities و categories.
    - تغییر نام ستون hospital_id در جدول visits به facility_id.

نکته مهم: این اسکریپت کاملاً بی‌خطر و قابل اجرای مکرر است. اگر قبلاً
اجرا شده باشد (یعنی جدول facilities از قبل وجود داشته باشد)، دوباره
هیچ تغییری اعمال نمی‌شود و فقط یک پیام اطلاع‌رسانی نمایش می‌دهد.

هیچ داده‌ای (بیمارستان‌ها، سؤالات، بازدیدها، پاسخ‌ها) در این فرآیند
حذف نمی‌شود؛ فقط نام جدول‌ها و ستون‌ها و ارتباط بین آن‌ها تغییر می‌کند.
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


def main() -> None:
    if not DB_PATH.exists():
        print(f"فایل پایگاه داده پیدا نشد: {DB_PATH}")
        print("ابتدا حتماً database/database.py را یک بار اجرا کرده باشید.")
        return

    con = sqlite3.connect(str(DB_PATH))

    if table_exists(con, "facilities"):
        print("این پایگاه داده قبلاً به مدل چند نوع سازمان مهاجرت کرده است.")
        print("نیازی به هیچ تغییری نیست.")
        con.close()
        return

    if not table_exists(con, "hospitals"):
        print("جدول hospitals پیدا نشد؛ این پایگاه داده با نسخه‌ای متفاوت ساخته شده است.")
        print("لطفاً قبل از ادامه، وضعیت را بررسی کنید.")
        con.close()
        return

    print("=" * 60)
    print("شروع مهاجرت پایگاه داده به مدل چند نوع سازمان")
    print("=" * 60)

    con.execute("PRAGMA foreign_keys = OFF")

    # ------------------------------------------------------------- ۱. انواع سازمان
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS facility_types (
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
        "INSERT OR IGNORE INTO facility_types (type_key, type_name) VALUES ('hospital', 'بیمارستان')"
    )
    con.commit()
    print("جدول facility_types ساخته شد و نوع «بیمارستان» ثبت شد.")

    hospital_type_id = con.execute(
        "SELECT id FROM facility_types WHERE type_key = 'hospital'"
    ).fetchone()[0]

    # ------------------------------------------------------------- ۲. جدول facilities
    con.execute("ALTER TABLE hospitals RENAME TO facilities")
    con.execute("ALTER TABLE facilities RENAME COLUMN hospital_name TO facility_name")
    con.execute("ALTER TABLE facilities RENAME COLUMN hospital_code TO facility_code")
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
    con.execute(
        "ALTER TABLE categories ADD COLUMN facility_type_id INTEGER REFERENCES facility_types(id)"
    )
    con.execute(
        "UPDATE categories SET facility_type_id = ? WHERE facility_type_id IS NULL",
        (hospital_type_id,),
    )
    con.commit()
    print("حوزه‌های موجود (نُه حوزه بیمارستانی) به نوع «بیمارستان» متصل شدند.")

    # ------------------------------------------------------------- ۴. بازدیدها
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

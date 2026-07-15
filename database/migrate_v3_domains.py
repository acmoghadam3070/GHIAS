#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه قیاس (GHIAS)
اسکریپت مهاجرت نسخه سوم پایگاه داده: افزودن لایه «حوزه کلان ارزیابی»
=============================================================================

این اسکریپت یک لایه جدید بین «نوع سازمان» و «زیرحوزه» اضافه می‌کند:
حوزه کلان ارزیابی (مثل حفاظت فیزیکی، امنیت اطلاعات، پدافند غیرعامل).

ساختار جدید:
    نوع سازمان → حوزه کلان ارزیابی → زیرحوزه (categories) → سؤال

تغییرات:
    - ساخت جدول assessment_domains
    - ثبت خودکار «حفاظت فیزیکی» به‌عنوان اولین حوزه کلان
    - افزودن ستون domain_id به جدول‌های categories و visits
    - اتصال تمام زیرحوزه‌های موجود (نُه‌تای فعلی) به حوزه «حفاظت فیزیکی»
    - اتصال تمام بازدیدهای موجود به همان حوزه

این اسکریپت باید بعد از migrate_v2_facility_types.py اجرا شود. هیچ داده‌ای
حذف نمی‌شود؛ کاملاً قابل اجرای مکرر و بی‌خطر است، حتی اگر تلاش قبلی نافرجام
مانده باشد.
=============================================================================
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH: Path = Path(__file__).resolve().parent / "GHIAS_SECURITY_ASSESSMENT.db"

PHYSICAL_SECURITY_DOMAIN_KEY = "physical_security"
PHYSICAL_SECURITY_DOMAIN_NAME = "حفاظت فیزیکی"


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

    if not table_exists(con, "facilities"):
        print("جدول facilities پیدا نشد.")
        print("لطفاً ابتدا migrate_v2_facility_types.py را اجرا کنید.")
        con.close()
        return

    already_migrated = (
        table_exists(con, "assessment_domains")
        and column_exists(con, "categories", "domain_id")
        and column_exists(con, "visits", "domain_id")
    )
    if already_migrated:
        print("این پایگاه داده قبلاً به مدل حوزه کلان ارزیابی مهاجرت کرده است.")
        print("نیازی به هیچ تغییری نیست.")
        con.close()
        return

    print("=" * 60)
    print("شروع مهاجرت پایگاه داده به مدل حوزه کلان ارزیابی")
    print("=" * 60)

    # ------------------------------------------------------------- پاک‌سازی باقیمانده تلاش ناموفق احتمالی
    if table_exists(con, "assessment_domains"):
        count = row_count(con, "assessment_domains")
        if count == 0:
            con.execute("DROP TABLE assessment_domains")
            con.commit()
            print("یک جدول assessment_domains خالی و ناقص پاک‌سازی شد.")

    # ------------------------------------------------------------- ۱. جدول حوزه‌های کلان
    if not table_exists(con, "assessment_domains"):
        con.execute(
            """
            CREATE TABLE assessment_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain_key TEXT UNIQUE NOT NULL,
                domain_name TEXT NOT NULL,
                description TEXT,
                display_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        print("جدول assessment_domains ساخته شد.")

    con.execute(
        "INSERT OR IGNORE INTO assessment_domains (domain_key, domain_name, display_order) "
        "VALUES (?, ?, 1)",
        (PHYSICAL_SECURITY_DOMAIN_KEY, PHYSICAL_SECURITY_DOMAIN_NAME),
    )
    con.commit()
    print(f"حوزه کلان «{PHYSICAL_SECURITY_DOMAIN_NAME}» ثبت شد.")

    physical_security_domain_id = con.execute(
        "SELECT id FROM assessment_domains WHERE domain_key = ?",
        (PHYSICAL_SECURITY_DOMAIN_KEY,),
    ).fetchone()[0]

    # ------------------------------------------------------------- ۲. اتصال زیرحوزه‌های موجود
    if not column_exists(con, "categories", "domain_id"):
        con.execute(
            "ALTER TABLE categories ADD COLUMN domain_id INTEGER REFERENCES assessment_domains(id)"
        )
    con.execute(
        "UPDATE categories SET domain_id = ? WHERE domain_id IS NULL",
        (physical_security_domain_id,),
    )
    con.commit()
    print("زیرحوزه‌های موجود به حوزه «حفاظت فیزیکی» متصل شدند.")

    # ------------------------------------------------------------- ۳. اتصال بازدیدهای موجود
    if not column_exists(con, "visits", "domain_id"):
        con.execute(
            "ALTER TABLE visits ADD COLUMN domain_id INTEGER REFERENCES assessment_domains(id)"
        )
    con.execute(
        "UPDATE visits SET domain_id = ? WHERE domain_id IS NULL",
        (physical_security_domain_id,),
    )
    con.commit()
    print("بازدیدهای موجود به حوزه «حفاظت فیزیکی» متصل شدند.")

    con.execute("PRAGMA foreign_keys = ON")
    con.close()

    print("=" * 60)
    print("مهاجرت با موفقیت و بدون از دست رفتن هیچ داده‌ای انجام شد.")
    print("=" * 60)


if __name__ == "__main__":
    main()

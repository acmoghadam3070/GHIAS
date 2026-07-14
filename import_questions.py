#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
اسکریپت وارد کردن بانک سؤالات از فایل‌های JSON به پایگاه داده
=============================================================================

این فایل تمام فایل‌های JSON داخل پوشه questions/ را می‌خواند و محتوای آن‌ها
را داخل جدول questions پایگاه داده SQLite ثبت می‌کند.

نکته مهم: نام هر فایل JSON باید دقیقاً برابر category_key موجود در جدول
categories باشد. برای مثال فایل cctv.json به حوزه‌ای با category_key
برابر با "cctv" وصل می‌شود.

این اسکریپت قابل اجرای مکرر است:
    - اگر سؤالی با همان کد قبلاً ثبت شده باشد، بروزرسانی می‌شود.
    - اگر سؤال جدید باشد، اضافه می‌شود.
    - هیچ رکوردی تکراری ساخته نمی‌شود.
=============================================================================
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# اضافه کردن پوشه database به مسیر جست‌وجوی پایتون تا بتوانیم
# ماژول database را وارد کنیم، مستقل از اینکه اسکریپت از کجا اجرا شود.
BASE_DIR: Path = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "database"))

from database import get_database  # noqa: E402


# مسیر پوشه‌ای که فایل‌های JSON بانک سؤالات در آن قرار دارند
QUESTIONS_DIR: Path = BASE_DIR / "questions"


def load_category_map(db) -> dict[str, int]:
    """
    ساخت نگاشت از category_key به شناسه عددی حوزه (id) در پایگاه داده.
    این نگاشت برای اتصال هر سؤال به حوزه درست استفاده می‌شود.
    """
    rows = db.query("SELECT id, category_key FROM categories")
    return {row["category_key"]: row["id"] for row in rows}


def import_file(db, file_path: Path, category_id: int) -> tuple[int, int]:
    """
    وارد کردن یک فایل JSON به پایگاه داده.
    خروجی: (تعداد رکورد جدید, تعداد رکورد بروزرسانی‌شده)
    """
    with file_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    inserted = 0
    updated = 0

    for record in records:
        code = str(record.get("code", "")).strip()
        title = str(record.get("title", "")).strip()
        weight = int(record.get("weight", 1))
        answer_type = str(record.get("answer_type", "yes_no")).strip()
        standard = str(record.get("standard", "")).strip()
        recommendation = str(record.get("recommendation", "")).strip()
        evaluator_guide = str(record.get("evaluator_guide", "")).strip()

        if not code or not title:
            # رکورد ناقص را نادیده می‌گیریم تا پایگاه داده کثیف نشود
            continue

        existing = db.query_one(
            "SELECT id FROM questions WHERE question_code = ?", (code,)
        )

        if existing is None:
            db.execute(
                """
                INSERT INTO questions (
                    category_id, question_code, question_text, answer_type,
                    weight, standard_reference, recommendation, evaluator_guide
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category_id, code, title, answer_type,
                    weight, standard, recommendation, evaluator_guide,
                ),
            )
            inserted += 1
        else:
            db.execute(
                """
                UPDATE questions
                SET category_id = ?, question_text = ?, answer_type = ?,
                    weight = ?, standard_reference = ?, recommendation = ?,
                    evaluator_guide = ?, updated_at = CURRENT_TIMESTAMP
                WHERE question_code = ?
                """,
                (
                    category_id, title, answer_type, weight,
                    standard, recommendation, evaluator_guide, code,
                ),
            )
            updated += 1

    return inserted, updated


def main() -> None:
    """نقطه ورود اسکریپت: وارد کردن تمام فایل‌های JSON پوشه questions."""
    if not QUESTIONS_DIR.exists():
        print(f"پوشه سؤالات پیدا نشد: {QUESTIONS_DIR}")
        return

    db = get_database()
    category_map = load_category_map(db)

    total_inserted = 0
    total_updated = 0
    total_skipped_files = 0

    print("=" * 60)
    print("شروع وارد کردن بانک سؤالات")
    print("=" * 60)

    for json_file in sorted(QUESTIONS_DIR.glob("*.json")):
        category_key = json_file.stem  # نام فایل بدون پسوند json

        if category_key not in category_map:
            print(f"رد شد: {json_file.name}  (حوزه‌ای با این نام در پایگاه داده تعریف نشده)")
            total_skipped_files += 1
            continue

        category_id = category_map[category_key]
        inserted, updated = import_file(db, json_file, category_id)
        total_inserted += inserted
        total_updated += updated
        print(f"{json_file.name:25s}  جدید: {inserted:3d}   بروزرسانی: {updated:3d}")

    print("=" * 60)
    print(f"جمع کل رکورد جدید:        {total_inserted}")
    print(f"جمع کل رکورد بروزرسانی‌شده: {total_updated}")
    if total_skipped_files:
        print(f"فایل‌های رد شده:          {total_skipped_files}")

    total_in_db = db.query_one("SELECT COUNT(*) AS c FROM questions")["c"]
    print(f"تعداد کل سؤالات موجود در پایگاه داده: {total_in_db}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()

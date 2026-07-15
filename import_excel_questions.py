#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
اسکریپت وارد کردن سؤالات از فایل اکسل
=============================================================================

این اسکریپت یک فایل اکسل (با ساختار مشخص) را می‌خواند و محتوای آن را در
پایگاه داده ثبت می‌کند.

نکته مهم و اصلی این اسکریپت: اگر نوع سازمان، حوزه کلان ارزیابی، یا زیرحوزه‌ای
که در فایل اکسل نوشته شده از قبل در پایگاه داده وجود نداشته باشد، به‌طور
کاملاً خودکار ساخته می‌شود. یعنی می‌توانید مستقیم در اکسل، یک حوزه یا نوع
سازمان کاملاً جدید تعریف کنید، بدون این‌که هیچ‌جای برنامه را باز کنید.

نحوه استفاده:
    python import_excel_questions.py                      (فایل پیش‌فرض)
    python import_excel_questions.py مسیر/فایل.xlsx        (فایل دلخواه)

ساختار مورد انتظار فایل اکسل (شیت اول، به نام Questions):
    نوع سازمان | حوزه کلان ارزیابی | زیرحوزه | کد سؤال | متن سؤال |
    وزن (۱ تا ۵) | نوع پاسخ | حیاتی (بله/خیر) | استاندارد مرجع |
    توصیه اصلاحی | راهنمای ارزیاب

این اسکریپت کاملاً قابل اجرای مکرر است: اگر کد سؤالی تکراری باشد، همان
سؤال بروزرسانی می‌شود، نه این‌که رکورد جدید ساخته شود.
=============================================================================
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Optional

import openpyxl

PROJECT_ROOT: Path = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))

from database import get_database  # noqa: E402


DEFAULT_FILE_NAME = "GHIAS_Question_Import_Template.xlsx"
SHEET_NAME = "Questions"

VALID_ANSWER_TYPES = {"yes_no", "scale_1_5", "percentage", "multiple_choice", "text"}

# ستون‌های مورد انتظار، به همان ترتیب فایل قالب
COLUMNS = [
    "facility_type",
    "domain",
    "category",
    "code",
    "title",
    "weight",
    "answer_type",
    "is_critical",
    "standard",
    "recommendation",
    "evaluator_guide",
]


def slugify(text: str) -> str:
    """ساخت یک کلید ساده (فقط حروف انگلیسی و اعداد) از روی یک نام دلخواه."""
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return ascii_only if ascii_only else "item"


def unique_key(existing_keys: set[str], base: str) -> str:
    """ساخت یک کلید یکتا با افزودن پسوند عددی در صورت تکراری بودن."""
    key = base
    suffix = 1
    while key in existing_keys:
        suffix += 1
        key = f"{base}-{suffix}"
    return key


class ExcelImporter:
    """مسئول خواندن فایل اکسل و ثبت محتوای آن در پایگاه داده."""

    def __init__(self, db):
        self.db = db
        self._facility_type_cache: dict[str, int] = {}
        self._domain_cache: dict[str, int] = {}
        self._category_cache: dict[tuple[int, int, str], int] = {}

        self.stats = {
            "facility_types_created": 0,
            "domains_created": 0,
            "categories_created": 0,
            "questions_inserted": 0,
            "questions_updated": 0,
            "rows_skipped": 0,
        }
        self.skipped_rows: list[tuple[int, str]] = []

    # ------------------------------------------------------------- کمکی‌های ساخت خودکار
    def get_or_create_facility_type(self, name: str) -> int:
        name = name.strip()
        if name in self._facility_type_cache:
            return self._facility_type_cache[name]

        row = self.db.query_one(
            "SELECT id FROM facility_types WHERE type_name = ?", (name,)
        )
        if row is not None:
            self._facility_type_cache[name] = row["id"]
            return row["id"]

        existing_keys = {
            r["type_key"] for r in self.db.query("SELECT type_key FROM facility_types")
        }
        key = unique_key(existing_keys, slugify(name))
        new_id = self.db.execute(
            "INSERT INTO facility_types (type_key, type_name) VALUES (?, ?)", (key, name)
        )
        self.stats["facility_types_created"] += 1
        self._facility_type_cache[name] = new_id
        return new_id

    def get_or_create_domain(self, name: str) -> int:
        name = name.strip()
        if name in self._domain_cache:
            return self._domain_cache[name]

        row = self.db.query_one(
            "SELECT id FROM assessment_domains WHERE domain_name = ?", (name,)
        )
        if row is not None:
            self._domain_cache[name] = row["id"]
            return row["id"]

        existing_keys = {
            r["domain_key"] for r in self.db.query("SELECT domain_key FROM assessment_domains")
        }
        key = unique_key(existing_keys, slugify(name))
        new_id = self.db.execute(
            "INSERT INTO assessment_domains (domain_key, domain_name) VALUES (?, ?)", (key, name)
        )
        self.stats["domains_created"] += 1
        self._domain_cache[name] = new_id
        return new_id

    def get_or_create_category(self, facility_type_id: int, domain_id: int, name: str) -> int:
        name = name.strip()
        cache_key = (facility_type_id, domain_id, name)
        if cache_key in self._category_cache:
            return self._category_cache[cache_key]

        row = self.db.query_one(
            "SELECT id FROM categories WHERE facility_type_id = ? AND domain_id = ? AND category_name = ?",
            (facility_type_id, domain_id, name),
        )
        if row is not None:
            self._category_cache[cache_key] = row["id"]
            return row["id"]

        existing_keys = {
            r["category_key"] for r in self.db.query("SELECT category_key FROM categories")
        }
        key = unique_key(existing_keys, slugify(name))
        new_id = self.db.execute(
            "INSERT INTO categories (facility_type_id, domain_id, category_key, category_name) "
            "VALUES (?, ?, ?, ?)",
            (facility_type_id, domain_id, key, name),
        )
        self.stats["categories_created"] += 1
        self._category_cache[cache_key] = new_id
        return new_id

    # ------------------------------------------------------------- اعتبارسنجی یک ردیف
    def _parse_weight(self, raw: Any) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return 1
        return max(1, min(100, value))

    def _parse_answer_type(self, raw: Any) -> str:
        value = str(raw).strip() if raw is not None else ""
        return value if value in VALID_ANSWER_TYPES else "yes_no"

    def _parse_is_critical(self, raw: Any) -> int:
        value = str(raw).strip() if raw is not None else ""
        return 1 if value in ("بله", "yes", "true", "1") else 0

    # ------------------------------------------------------------- پردازش سؤال
    def upsert_question(self, category_id: int, data: dict[str, Any]) -> None:
        existing = self.db.query_one(
            "SELECT id FROM questions WHERE question_code = ?", (data["code"],)
        )
        if existing is None:
            self.db.execute(
                """
                INSERT INTO questions (
                    category_id, question_code, question_text, answer_type, weight,
                    is_critical, standard_reference, recommendation, evaluator_guide
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category_id, data["code"], data["title"], data["answer_type"],
                    data["weight"], data["is_critical"], data["standard"],
                    data["recommendation"], data["evaluator_guide"],
                ),
            )
            self.stats["questions_inserted"] += 1
        else:
            self.db.execute(
                """
                UPDATE questions
                SET category_id = ?, question_text = ?, answer_type = ?, weight = ?,
                    is_critical = ?, standard_reference = ?, recommendation = ?,
                    evaluator_guide = ?, updated_at = CURRENT_TIMESTAMP
                WHERE question_code = ?
                """,
                (
                    category_id, data["title"], data["answer_type"], data["weight"],
                    data["is_critical"], data["standard"], data["recommendation"],
                    data["evaluator_guide"], data["code"],
                ),
            )
            self.stats["questions_updated"] += 1

    # ------------------------------------------------------------- خواندن فایل اکسل
    def import_file(self, file_path: Path) -> None:
        workbook = openpyxl.load_workbook(file_path, data_only=True)

        if SHEET_NAME not in workbook.sheetnames:
            raise ValueError(
                f"شیتی به نام «{SHEET_NAME}» در فایل پیدا نشد. "
                f"شیت‌های موجود: {workbook.sheetnames}"
            )

        sheet = workbook[SHEET_NAME]
        rows = list(sheet.iter_rows(min_row=2, values_only=True))  # ردیف اول هدر است

        for row_index, raw_row in enumerate(rows, start=2):
            if raw_row is None or all(cell is None for cell in raw_row):
                continue  # ردیف کاملاً خالی

            values = list(raw_row) + [None] * (len(COLUMNS) - len(raw_row))
            row = dict(zip(COLUMNS, values))

            facility_type_name = str(row["facility_type"] or "").strip()
            domain_name = str(row["domain"] or "").strip()
            category_name = str(row["category"] or "").strip()
            code = str(row["code"] or "").strip()
            title = str(row["title"] or "").strip()

            if not (facility_type_name and domain_name and category_name and code and title):
                self.stats["rows_skipped"] += 1
                self.skipped_rows.append((row_index, "یکی از فیلدهای الزامی خالی است"))
                continue

            facility_type_id = self.get_or_create_facility_type(facility_type_name)
            domain_id = self.get_or_create_domain(domain_name)
            category_id = self.get_or_create_category(facility_type_id, domain_id, category_name)

            question_data = {
                "code": code,
                "title": title,
                "weight": self._parse_weight(row["weight"]),
                "answer_type": self._parse_answer_type(row["answer_type"]),
                "is_critical": self._parse_is_critical(row["is_critical"]),
                "standard": str(row["standard"] or "").strip(),
                "recommendation": str(row["recommendation"] or "").strip(),
                "evaluator_guide": str(row["evaluator_guide"] or "").strip(),
            }
            self.upsert_question(category_id, question_data)


def main() -> None:
    file_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE_NAME
    file_path = Path(file_arg)
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    if not file_path.exists():
        print(f"فایل اکسل پیدا نشد: {file_path}")
        print(f"لطفاً فایل را در همین مسیر قرار دهید، یا مسیر را به‌عنوان ورودی بدهید:")
        print(f"    python import_excel_questions.py مسیر/فایل.xlsx")
        return

    db = get_database()
    importer = ExcelImporter(db)

    print("=" * 60)
    print(f"شروع وارد کردن سؤالات از فایل: {file_path.name}")
    print("=" * 60)

    try:
        importer.import_file(file_path)
    except ValueError as exc:
        print(f"خطا: {exc}")
        db.close()
        return

    stats = importer.stats
    print(f"نوع سازمان جدید ساخته‌شده:     {stats['facility_types_created']}")
    print(f"حوزه کلان جدید ساخته‌شده:      {stats['domains_created']}")
    print(f"زیرحوزه جدید ساخته‌شده:        {stats['categories_created']}")
    print(f"سؤال جدید افزوده‌شده:          {stats['questions_inserted']}")
    print(f"سؤال بروزرسانی‌شده:            {stats['questions_updated']}")
    print(f"ردیف رد‌شده (ناقص):            {stats['rows_skipped']}")

    if importer.skipped_rows:
        print()
        print("جزئیات ردیف‌های رد‌شده:")
        for row_number, reason in importer.skipped_rows:
            print(f"  ردیف {row_number}: {reason}")

    total_in_db = db.query_one("SELECT COUNT(*) AS c FROM questions")["c"]
    print()
    print(f"تعداد کل سؤالات موجود در پایگاه داده: {total_in_db}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()

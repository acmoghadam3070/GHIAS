#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه داده ارزیابی میدانی (Assessment Repository)
=============================================================================

این فایل مسئول تمام عملیات پایگاه داده مربوط به موتور ارزیابی است:
    - مدیریت انواع سازمان (بیمارستان، کارخانه، اداره و غیره)
    - مدیریت واحدهای تحت ارزیابی (facilities) و ارزیابان
    - مدیریت بازدیدها (شروع، ادامه، پایان)
    - ثبت و بروزرسانی پاسخ‌های هر سؤال در یک بازدید

این فایل کاملاً مستقل از رابط گرافیکی است و هیچ وابستگی به PySide6 ندارد.
=============================================================================
"""

from __future__ import annotations

import re
from typing import Any, Optional

from database import Database


def slugify(text: str) -> str:
    """
    ساخت یک کلید ساده و یکتا (فقط حروف انگلیسی، اعداد و خط تیره) از روی
    یک نام دلخواه، برای استفاده به‌عنوان type_key. اگر نام کاملاً فارسی
    باشد، از یک شناسه عددی جایگزین استفاده می‌شود.
    """
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return ascii_only if ascii_only else "type"


class AssessmentRepository:
    """مسئول تمام عملیات پایگاه داده مربوط به بازدیدها و پاسخ‌ها."""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------- حوزه‌های کلان ارزیابی
    def list_domains(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, domain_key, domain_name FROM assessment_domains "
            "WHERE is_active = 1 ORDER BY display_order"
        )
        return [dict(row) for row in rows]

    def add_domain(self, domain_name: str) -> int:
        """
        افزودن یک حوزه کلان ارزیابی کاملاً جدید (مثلاً «امنیت اطلاعات»
        یا «پدافند غیرعامل»).
        نکته مهم: بلافاصله بعد از این کار، هیچ زیرحوزه یا سؤالی برای این
        حوزه وجود ندارد؛ باید بعداً از طریق طراح بانک سؤالات اضافه شود.
        """
        base_key = slugify(domain_name)
        key = base_key
        suffix = 1
        existing_keys = {row["domain_key"] for row in self.db.query("SELECT domain_key FROM assessment_domains")}
        while key in existing_keys:
            suffix += 1
            key = f"{base_key}-{suffix}"

        return self.db.execute(
            "INSERT INTO assessment_domains (domain_key, domain_name) VALUES (?, ?)",
            (key, domain_name.strip()),
        )

    # ------------------------------------------------------------- انواع سازمان
    def list_facility_types(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, type_key, type_name FROM facility_types "
            "WHERE is_active = 1 ORDER BY type_name"
        )
        return [dict(row) for row in rows]

    def add_facility_type(self, type_name: str) -> int:
        """
        افزودن یک نوع سازمان کاملاً جدید (مثلاً «کارخانه» یا «اداره»).
        نکته مهم: بلافاصله بعد از این کار، هیچ حوزه یا سؤالی برای این
        نوع سازمان وجود ندارد؛ باید بعداً از طریق طراح بانک سؤالات
        اضافه شود.
        """
        base_key = slugify(type_name)
        key = base_key
        suffix = 1
        existing_keys = {row["type_key"] for row in self.db.query("SELECT type_key FROM facility_types")}
        while key in existing_keys:
            suffix += 1
            key = f"{base_key}-{suffix}"

        return self.db.execute(
            "INSERT INTO facility_types (type_key, type_name) VALUES (?, ?)",
            (key, type_name.strip()),
        )

    # ------------------------------------------------------------- واحدهای تحت ارزیابی
    def list_facilities(self, facility_type_id: int) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, facility_name FROM facilities "
            "WHERE facility_type_id = ? AND is_active = 1 ORDER BY facility_name",
            (facility_type_id,),
        )
        return [dict(row) for row in rows]

    def add_facility(self, facility_name: str, facility_type_id: int) -> int:
        return self.db.execute(
            "INSERT INTO facilities (facility_name, facility_type_id) VALUES (?, ?)",
            (facility_name.strip(), facility_type_id),
        )

    # ------------------------------------------------------------- ارزیابان
    def list_inspectors(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT id, full_name FROM inspectors WHERE is_active = 1 "
            "ORDER BY full_name"
        )
        return [dict(row) for row in rows]

    def add_inspector(self, full_name: str) -> int:
        return self.db.execute(
            "INSERT INTO inspectors (full_name) VALUES (?)",
            (full_name.strip(),),
        )

    # ------------------------------------------------------------- بازدیدها
    def get_open_visit(self, facility_id: int, domain_id: int, inspector_id: int) -> Optional[dict[str, Any]]:
        """
        جست‌وجوی یک بازدید ناتمام (وضعیت IN_PROGRESS) برای همین واحد،
        همین حوزه کلان، و همین ارزیاب، تا کاربر بتواند ارزیابی نیمه‌کاره
        را ادامه دهد.
        """
        row = self.db.query_one(
            """
            SELECT * FROM visits
            WHERE facility_id = ? AND domain_id = ? AND inspector_id = ? AND status = 'IN_PROGRESS'
            ORDER BY id DESC LIMIT 1
            """,
            (facility_id, domain_id, inspector_id),
        )
        return dict(row) if row is not None else None

    def create_visit(self, facility_id: int, domain_id: int, inspector_id: int) -> int:
        return self.db.execute(
            """
            INSERT INTO visits (facility_id, domain_id, inspector_id, visit_date, status)
            VALUES (?, ?, ?, DATE('now'), 'IN_PROGRESS')
            """,
            (facility_id, domain_id, inspector_id),
        )

    def get_visit(self, visit_id: int) -> Optional[dict[str, Any]]:
        row = self.db.query_one(
            """
            SELECT v.*, f.facility_name, f.facility_type_id,
                   ad.domain_name, i.full_name AS inspector_name
            FROM visits v
            JOIN facilities f ON f.id = v.facility_id
            JOIN assessment_domains ad ON ad.id = v.domain_id
            JOIN inspectors i ON i.id = v.inspector_id
            WHERE v.id = ?
            """,
            (visit_id,),
        )
        return dict(row) if row is not None else None

    def finish_visit(self, visit_id: int, overall_score: float, overall_risk_label: str) -> None:
        self.db.execute(
            """
            UPDATE visits
            SET status = 'FINISHED',
                overall_score = ?,
                overall_risk_level = ?,
                finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (overall_score, overall_risk_label, visit_id),
        )

    # ------------------------------------------------------------- حوزه‌ها و سؤالات
    def list_categories(self, facility_type_id: int, domain_id: int) -> list[dict[str, Any]]:
        """
        فهرست زیرحوزه‌های ارزیابی، فقط برای ترکیب (نوع سازمان + حوزه کلان)
        این بازدید (مثلاً فقط زیرحوزه‌های «حفاظت فیزیکی بیمارستان»،
        نه زیرحوزه‌های «امنیت اطلاعات کارخانه»).
        """
        rows = self.db.query(
            "SELECT id, category_key, category_name FROM categories "
            "WHERE facility_type_id = ? AND domain_id = ? AND is_active = 1 "
            "ORDER BY display_order",
            (facility_type_id, domain_id),
        )
        return [dict(row) for row in rows]

    def list_questions(self, category_id: int) -> list[dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT id, question_code, question_text, answer_type, weight,
                   is_critical, recommendation
            FROM questions
            WHERE category_id = ? AND is_active = 1
            ORDER BY id
            """,
            (category_id,),
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------- پاسخ‌ها
    def get_answers_for_visit(self, visit_id: int) -> dict[int, dict[str, Any]]:
        """
        بازگرداندن تمام پاسخ‌های ثبت‌شده یک بازدید، به‌صورت دیکشنری
        که کلید آن question_id است (برای دسترسی سریع هنگام پر کردن فرم).
        """
        rows = self.db.query(
            "SELECT * FROM answers WHERE visit_id = ?", (visit_id,)
        )
        return {row["question_id"]: dict(row) for row in rows}

    def get_deficient_answers(self, visit_id: int) -> list[dict[str, Any]]:
        """
        بازگرداندن تمام پاسخ‌های یک بازدید که به‌عنوان نقص علامت‌گذاری
        شده‌اند (is_deficiency = 1)، همراه با اطلاعات لازم سؤال و حوزه
        برای موتور توصیه اقدامات اصلاحی.
        """
        rows = self.db.query(
            """
            SELECT
                a.id AS answer_id,
                a.score AS score,
                q.id AS question_id,
                q.question_code AS question_code,
                q.weight AS weight,
                q.is_critical AS is_critical,
                q.recommendation AS recommendation_text,
                c.category_name AS category_name
            FROM answers a
            JOIN questions q ON q.id = a.question_id
            JOIN categories c ON c.id = q.category_id
            WHERE a.visit_id = ? AND a.is_deficiency = 1
            """,
            (visit_id,),
        )
        return [dict(row) for row in rows]

    def save_recommendations(self, recommendations: list[dict[str, Any]]) -> None:
        """
        ذخیره فهرست نهایی اقدامات اصلاحی در جدول recommendations.
        قبل از درج، توصیه‌های قبلی همان پاسخ‌ها حذف می‌شوند تا در صورت
        ثبت مجدد (مثلاً بازدید دوباره باز و بسته شود)، تکراری ساخته نشود.
        """
        for rec in recommendations:
            self.db.execute(
                "DELETE FROM recommendations WHERE answer_id = ?", (rec["answer_id"],)
            )
            self.db.execute(
                """
                INSERT INTO recommendations (answer_id, recommendation_text, priority)
                VALUES (?, ?, ?)
                """,
                (rec["answer_id"], rec["recommendation_text"], rec["priority"]),
            )

    def upsert_answer(
        self,
        visit_id: int,
        question_id: int,
        answer_value: str,
        score: Optional[float],
        comment: str,
    ) -> None:
        """
        ثبت یا بروزرسانی پاسخ یک سؤال در یک بازدید.
        اگر پاسخ قبلاً برای همین سؤال و همین بازدید ثبت شده باشد،
        بروزرسانی می‌شود؛ در غیر این صورت رکورد جدید ساخته می‌شود.
        """
        is_deficiency = 1 if (score is not None and score < 50.0) else 0

        self.db.execute(
            """
            INSERT INTO answers (visit_id, question_id, answer_value, score, is_deficiency, comment)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(visit_id, question_id) DO UPDATE SET
                answer_value = excluded.answer_value,
                score = excluded.score,
                is_deficiency = excluded.is_deficiency,
                comment = excluded.comment,
                answered_at = CURRENT_TIMESTAMP
            """,
            (visit_id, question_id, answer_value, score, is_deficiency, comment),
        )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه داده داشبورد (Dashboard Repository)
=============================================================================

این فایل داده‌های لازم برای نمودارهای داشبورد را از پایگاه داده استخراج
می‌کند:
    - فهرست واحدهایی که حداقل یک بازدید تکمیل‌شده دارند
    - فهرست بازدیدهای تکمیل‌شده یک واحد (برای روند زمانی)
    - امتیاز هر حوزه در یک بازدید مشخص (برای نمودار ستونی/دایره‌ای)،
      فقط از میان حوزه‌های متعلق به همان نوع سازمان

امتیاز هر حوزه در پایگاه داده ذخیره نشده (فقط امتیاز کلی بازدید ذخیره
می‌شود)؛ این فایل با استفاده از موتور امتیازدهی، امتیاز هر حوزه را از
روی پاسخ‌های ثبت‌شده، به‌صورت آنی دوباره محاسبه می‌کند.

این فایل مستقل از رابط گرافیکی است.
=============================================================================
"""

from __future__ import annotations

from typing import Any

from database import Database
from scoring_engine import AnswerRecord, CategoryResult, ScoringEngine


class DashboardRepository:
    """مسئول استخراج داده‌های تحلیلی برای نمایش در داشبورد."""

    def __init__(self, db: Database):
        self.db = db
        self.scoring_engine = ScoringEngine()

    # ------------------------------------------------------------- واحدها
    def list_facilities_with_finished_visits(self) -> list[dict[str, Any]]:
        """
        فهرست واحدهایی که حداقل یک بازدید تکمیل‌شده (FINISHED) دارند،
        به همراه نوع سازمان، تعداد بازدید و تاریخ آخرین بازدید.
        """
        rows = self.db.query(
            """
            SELECT
                f.id AS facility_id,
                f.facility_name AS facility_name,
                ft.type_name AS type_name,
                COUNT(v.id) AS visit_count,
                MAX(v.visit_date) AS last_visit_date
            FROM facilities f
            JOIN facility_types ft ON ft.id = f.facility_type_id
            JOIN visits v ON v.facility_id = f.id AND v.status = 'FINISHED'
            GROUP BY f.id
            ORDER BY f.facility_name
            """
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------- بازدیدها
    def list_finished_visits(self, facility_id: int) -> list[dict[str, Any]]:
        """فهرست بازدیدهای تکمیل‌شده یک واحد، از قدیم به جدید."""
        rows = self.db.query(
            """
            SELECT id, visit_date, overall_score, overall_risk_level, finished_at
            FROM visits
            WHERE facility_id = ? AND status = 'FINISHED'
            ORDER BY visit_date, id
            """,
            (facility_id,),
        )
        return [dict(row) for row in rows]

    def get_visit(self, visit_id: int) -> dict[str, Any] | None:
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

    # ------------------------------------------------------------- امتیاز حوزه‌ها
    def get_category_breakdown(self, visit_id: int) -> list[CategoryResult]:
        """
        محاسبه امتیاز هر حوزه مربوط به نوع سازمانِ این بازدید، با استفاده
        از موتور امتیازدهی. حوزه‌هایی که هیچ پاسخی در این بازدید ندارند
        هم در فهرست باقی می‌مانند (با برچسب «بدون داده»).
        """
        visit = self.get_visit(visit_id)
        if visit is None:
            return []

        categories = self.db.query(
            "SELECT id, category_name FROM categories "
            "WHERE facility_type_id = ? AND domain_id = ? AND is_active = 1 "
            "ORDER BY display_order",
            (visit["facility_type_id"], visit["domain_id"]),
        )
        answers_rows = self.db.query("SELECT * FROM answers WHERE visit_id = ?", (visit_id,))
        answers_by_question = {row["question_id"]: dict(row) for row in answers_rows}

        results: list[CategoryResult] = []
        for category in categories:
            questions = self.db.query(
                "SELECT id, weight, answer_type, is_critical FROM questions "
                "WHERE category_id = ? AND is_active = 1",
                (category["id"],),
            )
            records = [
                AnswerRecord(
                    question_id=q["id"],
                    category_id=category["id"],
                    weight=q["weight"],
                    answer_type=q["answer_type"],
                    answer_value=answers_by_question[q["id"]]["answer_value"],
                    is_critical=bool(q["is_critical"]),
                )
                for q in questions
                if q["id"] in answers_by_question
            ]
            result = self.scoring_engine.compute_category(
                category["id"], category["category_name"], records, len(questions)
            )
            results.append(result)

        return results

    # ------------------------------------------------------------- فهرست اقدامات اصلاحی
    def get_recommendations(self, visit_id: int) -> list[dict[str, Any]]:
        """فهرست اقدامات اصلاحی ثبت‌شده برای یک بازدید، مرتب‌شده بر اساس اولویت."""
        rows = self.db.query(
            """
            SELECT r.priority, r.recommendation_text, r.status, q.question_code, c.category_name
            FROM recommendations r
            JOIN answers a ON a.id = r.answer_id
            JOIN questions q ON q.id = a.question_id
            JOIN categories c ON c.id = q.category_id
            WHERE a.visit_id = ?
            ORDER BY
                CASE r.priority WHEN 'بالا' THEN 0 WHEN 'متوسط' THEN 1 ELSE 2 END
            """,
            (visit_id,),
        )
        return [dict(row) for row in rows]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه داده تخصیص ارزیابی (Assignment Repository)
=============================================================================

این فایل مسئول موارد زیر است:
    - ساخت تخصیص جدید توسط ادمین (واحد + حوزه کلان + کاربر مجری)
    - فهرست تخصیص‌های یک کاربر خاص (برای نمایش هنگام ورود ارزیاب/مصاحبه‌شونده)
    - شروع واقعی بازدید مربوط به یک تخصیص (در اولین باری که کاربر آن را باز می‌کند)

نکته فنی مهم: جدول قدیمی «inspectors» (فقط نام) از قبل در پروژه وجود
داشت و جدول visits به آن وصل است. برای این‌که داده‌های قدیمی به‌هم
نریزد، وقتی یک کاربر (ارزیاب) برای اولین بار بازدیدی می‌سازد، یک رکورد
متناظر در همان جدول inspectors پیدا یا ساخته می‌شود و به‌طور شفاف
(بدون نیاز به دخالت کاربر) استفاده می‌شود.
=============================================================================
"""

from __future__ import annotations

from typing import Any, Optional

from database import Database


class AssignmentRepository:
    """مسئول تمام عملیات پایگاه داده مربوط به تخصیص‌ها."""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------- کاربران قابل تخصیص
    def list_assignable_users(self) -> list[dict[str, Any]]:
        """فهرست کاربران با نقش ارزیاب یا مصاحبه‌شونده، برای انتخاب توسط ادمین."""
        rows = self.db.query(
            "SELECT id, username, full_name, role FROM users "
            "WHERE role IN ('inspector', 'interviewee') AND is_active = 1 "
            "ORDER BY full_name"
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------- ساخت تخصیص
    def create_assignment(
        self, facility_id: int, domain_id: int, assigned_user_id: int, assigned_by_user_id: int
    ) -> int:
        return self.db.execute(
            """
            INSERT INTO assignments (facility_id, domain_id, assigned_user_id, assigned_by_user_id)
            VALUES (?, ?, ?, ?)
            """,
            (facility_id, domain_id, assigned_user_id, assigned_by_user_id),
        )

    def list_all_assignments(self) -> list[dict[str, Any]]:
        """فهرست همه تخصیص‌ها، برای نمایش به ادمین."""
        rows = self.db.query(
            """
            SELECT a.id, f.facility_name, ad.domain_name, u.full_name AS assigned_to,
                   u.role, a.status, a.created_at
            FROM assignments a
            JOIN facilities f ON f.id = a.facility_id
            JOIN assessment_domains ad ON ad.id = a.domain_id
            JOIN users u ON u.id = a.assigned_user_id
            ORDER BY a.created_at DESC
            """
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------- تخصیص‌های یک کاربر
    def list_my_assignments(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT a.id, a.facility_id, a.domain_id, a.visit_id, a.status,
                   f.facility_name, ad.domain_name, f.facility_type_id
            FROM assignments a
            JOIN facilities f ON f.id = a.facility_id
            JOIN assessment_domains ad ON ad.id = a.domain_id
            WHERE a.assigned_user_id = ?
            ORDER BY a.created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------- شروع بازدید یک تخصیص
    def get_or_create_inspector_record(self, full_name: str) -> int:
        """
        پیدا کردن یا ساختن رکورد متناظر یک کاربر در جدول قدیمی inspectors
        (که فقط نام دارد)، تا بازدید بتواند به آن وصل شود.
        """
        row = self.db.query_one(
            "SELECT id FROM inspectors WHERE full_name = ?", (full_name,)
        )
        if row is not None:
            return row["id"]
        return self.db.execute(
            "INSERT INTO inspectors (full_name) VALUES (?)", (full_name,)
        )

    def start_assignment(self, assignment_id: int, user_full_name: str) -> int:
        """
        شروع واقعی بازدید یک تخصیص، اگر قبلاً شروع نشده باشد.
        خروجی: شناسه بازدید (visit_id).
        """
        assignment = self.db.query_one(
            "SELECT * FROM assignments WHERE id = ?", (assignment_id,)
        )
        if assignment["visit_id"] is not None:
            return assignment["visit_id"]

        inspector_id = self.get_or_create_inspector_record(user_full_name)
        visit_id = self.db.execute(
            """
            INSERT INTO visits (facility_id, domain_id, inspector_id, visit_date, status)
            VALUES (?, ?, ?, DATE('now'), 'IN_PROGRESS')
            """,
            (assignment["facility_id"], assignment["domain_id"], inspector_id),
        )
        self.db.execute(
            "UPDATE assignments SET visit_id = ?, status = 'IN_PROGRESS' WHERE id = ?",
            (visit_id, assignment_id),
        )
        return visit_id

    def mark_completed(self, assignment_id: int) -> None:
        self.db.execute(
            "UPDATE assignments SET status = 'COMPLETED' WHERE id = ?", (assignment_id,)
        )

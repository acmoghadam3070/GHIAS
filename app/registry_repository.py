#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه داده بانک اطلاعات (Registry Repository)
=============================================================================

این فایل مسئول موارد زیر است:
    - مدیریت کامل اطلاعات هویتی سازمان‌ها (اشخاص حقوقی)
    - مدیریت کامل اطلاعات هویتی افراد (اشخاص حقیقی)
    - مدیریت پیوست‌ها (عکس، نامه، مدرک) برای هرکدام
    - آرشیو/تاریخچه: فهرست کامل بازدیدها و گزارش‌های هر سازمان یا فرد

این فایل مستقل از رابط گرافیکی است.
=============================================================================
"""

from __future__ import annotations

from typing import Any, Optional

from database import Database


class RegistryRepository:
    """مسئول تمام عملیات پایگاه داده مربوط به بانک اطلاعات اشخاص و سازمان‌ها."""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------- سازمان‌ها (اشخاص حقوقی)
    def list_facilities_full(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT f.*, ft.type_name
            FROM facilities f
            JOIN facility_types ft ON ft.id = f.facility_type_id
            ORDER BY f.facility_name
            """
        )
        return [dict(row) for row in rows]

    def get_facility(self, facility_id: int) -> Optional[dict[str, Any]]:
        row = self.db.query_one(
            """
            SELECT f.*, ft.type_name
            FROM facilities f
            JOIN facility_types ft ON ft.id = f.facility_type_id
            WHERE f.id = ?
            """,
            (facility_id,),
        )
        return dict(row) if row is not None else None

    def create_facility(self, data: dict[str, Any]) -> int:
        return self.db.execute(
            """
            INSERT INTO facilities (
                facility_type_id, facility_name, facility_code, national_id,
                economic_code, ceo_name, manager_name, security_manager,
                province, city, address, postal_code, phone, email, website
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["facility_type_id"], data["facility_name"], data.get("facility_code") or None,
                data.get("national_id") or None, data.get("economic_code") or None,
                data.get("ceo_name") or None, data.get("manager_name") or None,
                data.get("security_manager") or None, data.get("province") or None,
                data.get("city") or None, data.get("address") or None,
                data.get("postal_code") or None, data.get("phone") or None,
                data.get("email") or None, data.get("website") or None,
            ),
        )

    def update_facility(self, facility_id: int, data: dict[str, Any]) -> None:
        self.db.execute(
            """
            UPDATE facilities SET
                facility_name = ?, facility_code = ?, national_id = ?, economic_code = ?,
                ceo_name = ?, manager_name = ?, security_manager = ?, province = ?, city = ?,
                address = ?, postal_code = ?, phone = ?, email = ?, website = ?
            WHERE id = ?
            """,
            (
                data["facility_name"], data.get("facility_code") or None,
                data.get("national_id") or None, data.get("economic_code") or None,
                data.get("ceo_name") or None, data.get("manager_name") or None,
                data.get("security_manager") or None, data.get("province") or None,
                data.get("city") or None, data.get("address") or None,
                data.get("postal_code") or None, data.get("phone") or None,
                data.get("email") or None, data.get("website") or None,
                facility_id,
            ),
        )

    def set_facility_logo(self, facility_id: int, logo_path: str) -> None:
        self.db.execute("UPDATE facilities SET logo_path = ? WHERE id = ?", (logo_path, facility_id))

    # ------------------------------------------------------------- اشخاص حقیقی
    def list_persons(self) -> list[dict[str, Any]]:
        rows = self.db.query(
            """
            SELECT p.*, f.facility_name
            FROM persons p
            LEFT JOIN facilities f ON f.id = p.facility_id
            ORDER BY p.first_name, p.last_name
            """
        )
        return [dict(row) for row in rows]

    def get_person(self, person_id: int) -> Optional[dict[str, Any]]:
        row = self.db.query_one(
            """
            SELECT p.*, f.facility_name
            FROM persons p
            LEFT JOIN facilities f ON f.id = p.facility_id
            WHERE p.id = ?
            """,
            (person_id,),
        )
        return dict(row) if row is not None else None

    def create_person(self, data: dict[str, Any]) -> int:
        return self.db.execute(
            """
            INSERT INTO persons (
                national_code, first_name, last_name, father_name, gender,
                birth_date, position, facility_id, phone, mobile, email, address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("national_code") or None, data["first_name"], data["last_name"],
                data.get("father_name") or None, data.get("gender") or None,
                data.get("birth_date") or None, data.get("position") or None,
                data.get("facility_id") or None, data.get("phone") or None,
                data.get("mobile") or None, data.get("email") or None,
                data.get("address") or None,
            ),
        )

    def update_person(self, person_id: int, data: dict[str, Any]) -> None:
        self.db.execute(
            """
            UPDATE persons SET
                national_code = ?, first_name = ?, last_name = ?, father_name = ?,
                gender = ?, birth_date = ?, position = ?, facility_id = ?,
                phone = ?, mobile = ?, email = ?, address = ?
            WHERE id = ?
            """,
            (
                data.get("national_code") or None, data["first_name"], data["last_name"],
                data.get("father_name") or None, data.get("gender") or None,
                data.get("birth_date") or None, data.get("position") or None,
                data.get("facility_id") or None, data.get("phone") or None,
                data.get("mobile") or None, data.get("email") or None,
                data.get("address") or None, person_id,
            ),
        )

    def set_person_photo(self, person_id: int, photo_path: str) -> None:
        self.db.execute("UPDATE persons SET photo_path = ? WHERE id = ?", (photo_path, person_id))

    # ------------------------------------------------------------- پیوست‌ها
    def add_attachment(self, owner_type: str, owner_id: int, title: str, file_path: str) -> int:
        if owner_type not in ("person", "facility"):
            raise ValueError("owner_type باید 'person' یا 'facility' باشد.")
        return self.db.execute(
            "INSERT INTO attachments (owner_type, owner_id, title, file_path) VALUES (?, ?, ?, ?)",
            (owner_type, owner_id, title, file_path),
        )

    def list_attachments(self, owner_type: str, owner_id: int) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT * FROM attachments WHERE owner_type = ? AND owner_id = ? ORDER BY uploaded_at DESC",
            (owner_type, owner_id),
        )
        return [dict(row) for row in rows]

    def delete_attachment(self, attachment_id: int) -> None:
        self.db.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))

    # ------------------------------------------------------------- آرشیو/تاریخچه
    def get_facility_history(self, facility_id: int) -> list[dict[str, Any]]:
        """فهرست کامل بازدیدها و گزارش‌های یک سازمان، از جدید به قدیم."""
        rows = self.db.query(
            """
            SELECT v.id AS visit_id, v.visit_date, v.status, v.overall_score,
                   v.overall_risk_level, ad.domain_name, i.full_name AS inspector_name,
                   (SELECT COUNT(*) FROM reports r WHERE r.visit_id = v.id) AS report_count
            FROM visits v
            JOIN assessment_domains ad ON ad.id = v.domain_id
            JOIN inspectors i ON i.id = v.inspector_id
            WHERE v.facility_id = ?
            ORDER BY v.visit_date DESC, v.id DESC
            """,
            (facility_id,),
        )
        return [dict(row) for row in rows]

    def get_visit_reports(self, visit_id: int) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT * FROM reports WHERE visit_id = ? ORDER BY generated_at DESC", (visit_id,)
        )
        return [dict(row) for row in rows]

    def log_generated_report(self, visit_id: int, report_format: str, file_path: str) -> int:
        return self.db.execute(
            "INSERT INTO reports (visit_id, report_format, file_path) VALUES (?, ?, ?)",
            (visit_id, report_format, file_path),
        )

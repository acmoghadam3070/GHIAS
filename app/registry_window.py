#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره بانک اطلاعات (Registry Window)
=============================================================================

این پنجره مخصوص ادمین است و دو بخش دارد:
    - سازمان‌ها (اشخاص حقوقی): اطلاعات هویتی کامل، لوگو، پیوست‌ها، تاریخچه
    - اشخاص (اشخاص حقیقی): اطلاعات هویتی، عکس، پیوست‌ها

قبل از تخصیص هر ارزیابی، بهتر است ابتدا پروفایل سازمان یا شخص از همین
پنجره ساخته شود.
=============================================================================
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))
sys.path.insert(0, str(APP_DIR))

from registry_repository import RegistryRepository  # noqa: E402

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

UPLOADS_DIR = PROJECT_ROOT / "assets" / "uploads"


def _store_uploaded_file(source_path: str, owner_type: str, owner_id: int) -> str:
    """
    کپی یک فایل انتخاب‌شده به پوشه ذخیره‌سازی داخلی پروژه، و بازگرداندن
    مسیر نسبی آن (برای ذخیره در پایگاه داده).
    """
    source = Path(source_path)
    target_dir = UPLOADS_DIR / owner_type / str(owner_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target_name = f"{timestamp}_{source.name}"
    target_path = target_dir / target_name
    shutil.copy2(source, target_path)

    return str(target_path.relative_to(PROJECT_ROOT))


class RegistryWindow(QMainWindow):
    """پنجره اصلی بانک اطلاعات سازمان‌ها و اشخاص."""

    def __init__(self, repository: RegistryRepository):
        super().__init__()
        self.repository = repository

        self.facilities: list[dict[str, Any]] = []
        self.current_facility_id: Optional[int] = None
        self.persons: list[dict[str, Any]] = []
        self.current_person_id: Optional[int] = None

        self.setWindowTitle("GHIAS | بانک اطلاعات سازمان‌ها و اشخاص")
        self.resize(1300, 780)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()
        self._load_facilities()
        self._load_persons()

    # ------------------------------------------------------------- ساخت رابط
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_facility_tab(), "سازمان‌ها (اشخاص حقوقی)")
        tabs.addTab(self._build_person_tab(), "اشخاص (اشخاص حقیقی)")

    # ------------------------------------------------------------- تب سازمان‌ها
    def _build_facility_tab(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)

        list_panel = QVBoxLayout()
        list_panel.addWidget(QLabel("فهرست سازمان‌ها"))
        self.facility_list = QListWidget()
        self.facility_list.currentRowChanged.connect(self._on_facility_selected)
        list_panel.addWidget(self.facility_list)
        list_container = QWidget()
        list_container.setLayout(list_panel)
        list_container.setFixedWidth(260)
        root.addWidget(list_container)

        form_scroll_container = QFrame()
        form_scroll_container.setObjectName("Card")
        form_outer = QVBoxLayout(form_scroll_container)

        form_outer.addWidget(QLabel("اطلاعات هویتی سازمان"))
        form_layout = QFormLayout()

        self.f_name = QLineEdit()
        form_layout.addRow("نام سازمان:", self.f_name)
        self.f_code = QLineEdit()
        form_layout.addRow("کد داخلی:", self.f_code)
        self.f_national_id = QLineEdit()
        form_layout.addRow("شناسه ملی:", self.f_national_id)
        self.f_economic_code = QLineEdit()
        form_layout.addRow("کد اقتصادی:", self.f_economic_code)
        self.f_ceo = QLineEdit()
        form_layout.addRow("مدیرعامل:", self.f_ceo)
        self.f_manager = QLineEdit()
        form_layout.addRow("مدیر واحد:", self.f_manager)
        self.f_security_manager = QLineEdit()
        form_layout.addRow("مسئول حفاظت/امنیت:", self.f_security_manager)
        self.f_province = QLineEdit()
        form_layout.addRow("استان:", self.f_province)
        self.f_city = QLineEdit()
        form_layout.addRow("شهر:", self.f_city)
        self.f_address = QLineEdit()
        form_layout.addRow("آدرس:", self.f_address)
        self.f_postal_code = QLineEdit()
        form_layout.addRow("کد پستی:", self.f_postal_code)
        self.f_phone = QLineEdit()
        form_layout.addRow("تلفن:", self.f_phone)
        self.f_email = QLineEdit()
        form_layout.addRow("ایمیل:", self.f_email)
        self.f_website = QLineEdit()
        form_layout.addRow("وب‌سایت:", self.f_website)

        form_outer.addLayout(form_layout)

        button_row = QHBoxLayout()
        new_button = QPushButton("سازمان جدید")
        new_button.clicked.connect(self._on_new_facility)
        button_row.addWidget(new_button)

        save_button = QPushButton("ذخیره تغییرات")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._on_save_facility)
        button_row.addWidget(save_button)

        logo_button = QPushButton("بارگذاری لوگو")
        logo_button.clicked.connect(self._on_upload_logo)
        button_row.addWidget(logo_button)
        form_outer.addLayout(button_row)

        form_outer.addWidget(QLabel("پیوست‌ها (نامه معرفی، نامه ارزیابی، مدارک)"))
        att_row = QHBoxLayout()
        self.facility_attachments_list = QListWidget()
        att_row.addWidget(self.facility_attachments_list)
        att_buttons = QVBoxLayout()
        add_att_button = QPushButton("افزودن پیوست")
        add_att_button.clicked.connect(lambda: self._on_add_attachment("facility"))
        att_buttons.addWidget(add_att_button)
        remove_att_button = QPushButton("حذف پیوست انتخاب‌شده")
        remove_att_button.clicked.connect(lambda: self._on_remove_attachment("facility"))
        att_buttons.addWidget(remove_att_button)
        att_buttons.addStretch(1)
        att_row.addLayout(att_buttons)
        form_outer.addLayout(att_row)

        form_outer.addWidget(QLabel("تاریخچه بازدیدها و گزارش‌ها"))
        self.facility_history_table = QTableWidget(0, 6)
        self.facility_history_table.setHorizontalHeaderLabels(
            ["تاریخ", "حوزه", "ارزیاب", "امتیاز", "وضعیت", "تعداد گزارش"]
        )
        self.facility_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        form_outer.addWidget(self.facility_history_table)

        root.addWidget(form_scroll_container, stretch=1)
        return page

    # ------------------------------------------------------------- تب اشخاص
    def _build_person_tab(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)

        list_panel = QVBoxLayout()
        list_panel.addWidget(QLabel("فهرست اشخاص"))
        self.person_list = QListWidget()
        self.person_list.currentRowChanged.connect(self._on_person_selected)
        list_panel.addWidget(self.person_list)
        list_container = QWidget()
        list_container.setLayout(list_panel)
        list_container.setFixedWidth(260)
        root.addWidget(list_container)

        form_card = QFrame()
        form_card.setObjectName("Card")
        form_outer = QVBoxLayout(form_card)

        top_row = QHBoxLayout()
        self.person_photo_label = QLabel()
        self.person_photo_label.setFixedSize(90, 90)
        self.person_photo_label.setStyleSheet("background-color: #e7ebef; border-radius: 8px;")
        self.person_photo_label.setAlignment(Qt.AlignCenter)
        top_row.addWidget(self.person_photo_label)

        photo_button = QPushButton("بارگذاری عکس پرسنلی")
        photo_button.clicked.connect(self._on_upload_photo)
        top_row.addWidget(photo_button)
        top_row.addStretch(1)
        form_outer.addLayout(top_row)

        form_outer.addWidget(QLabel("اطلاعات هویتی شخص"))
        form_layout = QFormLayout()

        self.p_first_name = QLineEdit()
        form_layout.addRow("نام:", self.p_first_name)
        self.p_last_name = QLineEdit()
        form_layout.addRow("نام خانوادگی:", self.p_last_name)
        self.p_father_name = QLineEdit()
        form_layout.addRow("نام پدر:", self.p_father_name)
        self.p_national_code = QLineEdit()
        form_layout.addRow("کد ملی:", self.p_national_code)
        self.p_gender = QComboBox()
        self.p_gender.addItems(["", "مرد", "زن"])
        form_layout.addRow("جنسیت:", self.p_gender)
        self.p_birth_date = QLineEdit()
        self.p_birth_date.setPlaceholderText("مثلاً 1365/03/12")
        form_layout.addRow("تاریخ تولد:", self.p_birth_date)
        self.p_position = QLineEdit()
        form_layout.addRow("سمت:", self.p_position)
        self.p_facility_combo = QComboBox()
        form_layout.addRow("سازمان مرتبط:", self.p_facility_combo)
        self.p_mobile = QLineEdit()
        form_layout.addRow("موبایل:", self.p_mobile)
        self.p_phone = QLineEdit()
        form_layout.addRow("تلفن:", self.p_phone)
        self.p_email = QLineEdit()
        form_layout.addRow("ایمیل:", self.p_email)
        self.p_address = QLineEdit()
        form_layout.addRow("آدرس:", self.p_address)

        form_outer.addLayout(form_layout)

        button_row = QHBoxLayout()
        new_button = QPushButton("شخص جدید")
        new_button.clicked.connect(self._on_new_person)
        button_row.addWidget(new_button)
        save_button = QPushButton("ذخیره تغییرات")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._on_save_person)
        button_row.addWidget(save_button)
        form_outer.addLayout(button_row)

        form_outer.addWidget(QLabel("پیوست‌ها (نامه معرفی، مدارک، گواهینامه)"))
        att_row = QHBoxLayout()
        self.person_attachments_list = QListWidget()
        att_row.addWidget(self.person_attachments_list)
        att_buttons = QVBoxLayout()
        add_att_button = QPushButton("افزودن پیوست")
        add_att_button.clicked.connect(lambda: self._on_add_attachment("person"))
        att_buttons.addWidget(add_att_button)
        remove_att_button = QPushButton("حذف پیوست انتخاب‌شده")
        remove_att_button.clicked.connect(lambda: self._on_remove_attachment("person"))
        att_buttons.addWidget(remove_att_button)
        att_buttons.addStretch(1)
        att_row.addLayout(att_buttons)
        form_outer.addLayout(att_row)
        form_outer.addStretch(1)

        root.addWidget(form_card, stretch=1)
        return page

    # ------------------------------------------------------------- بارگذاری سازمان‌ها
    def _load_facilities(self) -> None:
        self.facilities = self.repository.list_facilities_full()
        self.facility_list.clear()
        for facility in self.facilities:
            self.facility_list.addItem(QListWidgetItem(facility["facility_name"]))

        self.p_facility_combo.clear()
        self.p_facility_combo.addItem("(بدون سازمان)", None)
        for facility in self.facilities:
            self.p_facility_combo.addItem(facility["facility_name"], facility["id"])

        if self.facilities:
            self.facility_list.setCurrentRow(0)

    def _on_facility_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.facilities):
            return
        facility = self.facilities[row]
        self.current_facility_id = facility["id"]
        self._fill_facility_form(facility)
        self._refresh_facility_attachments()
        self._refresh_facility_history()

    def _fill_facility_form(self, facility: dict[str, Any]) -> None:
        self.f_name.setText(facility.get("facility_name") or "")
        self.f_code.setText(facility.get("facility_code") or "")
        self.f_national_id.setText(facility.get("national_id") or "")
        self.f_economic_code.setText(facility.get("economic_code") or "")
        self.f_ceo.setText(facility.get("ceo_name") or "")
        self.f_manager.setText(facility.get("manager_name") or "")
        self.f_security_manager.setText(facility.get("security_manager") or "")
        self.f_province.setText(facility.get("province") or "")
        self.f_city.setText(facility.get("city") or "")
        self.f_address.setText(facility.get("address") or "")
        self.f_postal_code.setText(facility.get("postal_code") or "")
        self.f_phone.setText(facility.get("phone") or "")
        self.f_email.setText(facility.get("email") or "")
        self.f_website.setText(facility.get("website") or "")

    def _clear_facility_form(self) -> None:
        self.current_facility_id = None
        for widget in (
            self.f_name, self.f_code, self.f_national_id, self.f_economic_code, self.f_ceo,
            self.f_manager, self.f_security_manager, self.f_province, self.f_city,
            self.f_address, self.f_postal_code, self.f_phone, self.f_email, self.f_website,
        ):
            widget.clear()
        self.facility_attachments_list.clear()
        self.facility_history_table.setRowCount(0)

    def _on_new_facility(self) -> None:
        if not self.facilities:
            QMessageBox.information(
                self, "توجه",
                "برای ساخت سازمان جدید، ابتدا باید حداقل یک نوع سازمان در پایگاه داده وجود داشته باشد "
                "(از بخش «تخصیص ارزیابی» یک نوع سازمان بسازید)."
            )
            return
        self.facility_list.clearSelection()
        self._clear_facility_form()

    def _on_save_facility(self) -> None:
        if not self.f_name.text().strip():
            QMessageBox.warning(self, "خطا", "نام سازمان الزامی است.")
            return

        data = {
            "facility_name": self.f_name.text().strip(),
            "facility_code": self.f_code.text().strip(),
            "national_id": self.f_national_id.text().strip(),
            "economic_code": self.f_economic_code.text().strip(),
            "ceo_name": self.f_ceo.text().strip(),
            "manager_name": self.f_manager.text().strip(),
            "security_manager": self.f_security_manager.text().strip(),
            "province": self.f_province.text().strip(),
            "city": self.f_city.text().strip(),
            "address": self.f_address.text().strip(),
            "postal_code": self.f_postal_code.text().strip(),
            "phone": self.f_phone.text().strip(),
            "email": self.f_email.text().strip(),
            "website": self.f_website.text().strip(),
        }

        if self.current_facility_id is not None:
            self.repository.update_facility(self.current_facility_id, data)
            QMessageBox.information(self, "موفق", "اطلاعات سازمان بروزرسانی شد.")
        else:
            first_type = self.repository.db.query_one("SELECT id FROM facility_types LIMIT 1")
            if first_type is None:
                QMessageBox.warning(self, "خطا", "هیچ نوع سازمانی در پایگاه داده تعریف نشده است.")
                return
            data["facility_type_id"] = first_type["id"]
            new_id = self.repository.create_facility(data)
            self.current_facility_id = new_id
            QMessageBox.information(self, "موفق", "سازمان جدید ثبت شد.")

        self._load_facilities()

    def _on_upload_logo(self) -> None:
        if self.current_facility_id is None:
            QMessageBox.information(self, "توجه", "ابتدا سازمان را ذخیره کنید.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب لوگو", "", "تصویر (*.png *.jpg *.jpeg)")
        if not file_path:
            return
        relative_path = _store_uploaded_file(file_path, "facility", self.current_facility_id)
        self.repository.set_facility_logo(self.current_facility_id, relative_path)
        QMessageBox.information(self, "موفق", "لوگو بارگذاری شد.")

    def _refresh_facility_attachments(self) -> None:
        self.facility_attachments_list.clear()
        if self.current_facility_id is None:
            return
        for att in self.repository.list_attachments("facility", self.current_facility_id):
            item = QListWidgetItem(f"{att['title']}  —  {att['file_path']}")
            item.setData(Qt.UserRole, att["id"])
            self.facility_attachments_list.addItem(item)

    def _refresh_facility_history(self) -> None:
        self.facility_history_table.setRowCount(0)
        if self.current_facility_id is None:
            return
        history = self.repository.get_facility_history(self.current_facility_id)
        self.facility_history_table.setRowCount(len(history))
        for row_index, item in enumerate(history):
            values = [
                str(item["visit_date"]), item["domain_name"], item["inspector_name"],
                str(item["overall_score"] or "—"), item["status"], str(item["report_count"]),
            ]
            for col_index, value in enumerate(values):
                self.facility_history_table.setItem(row_index, col_index, QTableWidgetItem(value))

    # ------------------------------------------------------------- بارگذاری اشخاص
    def _load_persons(self) -> None:
        self.persons = self.repository.list_persons()
        self.person_list.clear()
        for person in self.persons:
            self.person_list.addItem(QListWidgetItem(f"{person['first_name']} {person['last_name']}"))
        if self.persons:
            self.person_list.setCurrentRow(0)

    def _on_person_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.persons):
            return
        person = self.persons[row]
        self.current_person_id = person["id"]
        self._fill_person_form(person)
        self._refresh_person_attachments()
        self._refresh_person_photo(person.get("photo_path"))

    def _fill_person_form(self, person: dict[str, Any]) -> None:
        self.p_first_name.setText(person.get("first_name") or "")
        self.p_last_name.setText(person.get("last_name") or "")
        self.p_father_name.setText(person.get("father_name") or "")
        self.p_national_code.setText(person.get("national_code") or "")
        index = self.p_gender.findText(person.get("gender") or "")
        self.p_gender.setCurrentIndex(index if index >= 0 else 0)
        self.p_birth_date.setText(person.get("birth_date") or "")
        self.p_position.setText(person.get("position") or "")
        facility_index = self.p_facility_combo.findData(person.get("facility_id"))
        self.p_facility_combo.setCurrentIndex(facility_index if facility_index >= 0 else 0)
        self.p_mobile.setText(person.get("mobile") or "")
        self.p_phone.setText(person.get("phone") or "")
        self.p_email.setText(person.get("email") or "")
        self.p_address.setText(person.get("address") or "")

    def _clear_person_form(self) -> None:
        self.current_person_id = None
        for widget in (
            self.p_first_name, self.p_last_name, self.p_father_name, self.p_national_code,
            self.p_birth_date, self.p_position, self.p_mobile, self.p_phone, self.p_email,
            self.p_address,
        ):
            widget.clear()
        self.p_gender.setCurrentIndex(0)
        self.p_facility_combo.setCurrentIndex(0)
        self.person_attachments_list.clear()
        self.person_photo_label.clear()
        self.person_photo_label.setText("بدون عکس")

    def _on_new_person(self) -> None:
        self.person_list.clearSelection()
        self._clear_person_form()

    def _on_save_person(self) -> None:
        if not self.p_first_name.text().strip() or not self.p_last_name.text().strip():
            QMessageBox.warning(self, "خطا", "نام و نام‌خانوادگی الزامی است.")
            return

        data = {
            "first_name": self.p_first_name.text().strip(),
            "last_name": self.p_last_name.text().strip(),
            "father_name": self.p_father_name.text().strip(),
            "national_code": self.p_national_code.text().strip(),
            "gender": self.p_gender.currentText(),
            "birth_date": self.p_birth_date.text().strip(),
            "position": self.p_position.text().strip(),
            "facility_id": self.p_facility_combo.currentData(),
            "mobile": self.p_mobile.text().strip(),
            "phone": self.p_phone.text().strip(),
            "email": self.p_email.text().strip(),
            "address": self.p_address.text().strip(),
        }

        if self.current_person_id is not None:
            self.repository.update_person(self.current_person_id, data)
            QMessageBox.information(self, "موفق", "اطلاعات شخص بروزرسانی شد.")
        else:
            new_id = self.repository.create_person(data)
            self.current_person_id = new_id
            QMessageBox.information(self, "موفق", "شخص جدید ثبت شد.")

        self._load_persons()

    def _on_upload_photo(self) -> None:
        if self.current_person_id is None:
            QMessageBox.information(self, "توجه", "ابتدا شخص را ذخیره کنید.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب عکس پرسنلی", "", "تصویر (*.png *.jpg *.jpeg)")
        if not file_path:
            return
        relative_path = _store_uploaded_file(file_path, "person", self.current_person_id)
        self.repository.set_person_photo(self.current_person_id, relative_path)
        self._refresh_person_photo(relative_path)
        QMessageBox.information(self, "موفق", "عکس بارگذاری شد.")

    def _refresh_person_photo(self, relative_path: Optional[str]) -> None:
        if relative_path:
            full_path = PROJECT_ROOT / relative_path
            if full_path.exists():
                pixmap = QPixmap(str(full_path)).scaled(90, 90, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.person_photo_label.setPixmap(pixmap)
                return
        self.person_photo_label.clear()
        self.person_photo_label.setText("بدون عکس")

    def _refresh_person_attachments(self) -> None:
        self.person_attachments_list.clear()
        if self.current_person_id is None:
            return
        for att in self.repository.list_attachments("person", self.current_person_id):
            item = QListWidgetItem(f"{att['title']}  —  {att['file_path']}")
            item.setData(Qt.UserRole, att["id"])
            self.person_attachments_list.addItem(item)

    # ------------------------------------------------------------- پیوست‌های عمومی
    def _on_add_attachment(self, owner_type: str) -> None:
        owner_id = self.current_facility_id if owner_type == "facility" else self.current_person_id
        if owner_id is None:
            QMessageBox.information(self, "توجه", "ابتدا رکورد را ذخیره کنید.")
            return

        title, ok = QInputDialog.getText(self, "عنوان پیوست", "این پیوست چیست؟ (مثلاً نامه معرفی):")
        if not ok or not title.strip():
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل پیوست")
        if not file_path:
            return

        relative_path = _store_uploaded_file(file_path, owner_type, owner_id)
        self.repository.add_attachment(owner_type, owner_id, title.strip(), relative_path)

        if owner_type == "facility":
            self._refresh_facility_attachments()
        else:
            self._refresh_person_attachments()

    def _on_remove_attachment(self, owner_type: str) -> None:
        widget = self.facility_attachments_list if owner_type == "facility" else self.person_attachments_list
        selected = widget.currentItem()
        if selected is None:
            QMessageBox.information(self, "توجه", "ابتدا یک پیوست را انتخاب کنید.")
            return
        attachment_id = selected.data(Qt.UserRole)
        self.repository.delete_attachment(attachment_id)

        if owner_type == "facility":
            self._refresh_facility_attachments()
        else:
            self._refresh_person_attachments()

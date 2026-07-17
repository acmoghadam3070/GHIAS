#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره مدیریت کاربران (User Management Window)
=============================================================================

این پنجره فقط برای نقش admin در دسترس است. امکانات:
    - مشاهده فهرست کاربران و نقش و وضعیت آن‌ها
    - افزودن کاربر جدید با یکی از سه نقش
    - فعال/غیرفعال کردن یک کاربر
    - تغییر رمز عبور یک کاربر
=============================================================================
"""

from __future__ import annotations

from typing import Any

from auth_repository import AuthRepository, VALID_ROLES

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

ROLE_LABELS = {
    "admin": "ادمین (دسترسی کامل)",
    "inspector": "ارزیاب",
    "interviewee": "مصاحبه‌شونده",
}


class AddUserDialog(QDialog):
    """دیالوگ افزودن کاربر جدید."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("افزودن کاربر جدید")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(360)

        layout = QFormLayout(self)

        self.username_edit = QLineEdit()
        layout.addRow("نام کاربری:", self.username_edit)

        self.full_name_edit = QLineEdit()
        layout.addRow("نام کامل:", self.full_name_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("رمز عبور:", self.password_edit)

        self.role_combo = QComboBox()
        for role_key, role_label in ROLE_LABELS.items():
            self.role_combo.addItem(role_label, role_key)
        layout.addRow("نقش:", self.role_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("افزودن")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self) -> tuple[str, str, str, str]:
        return (
            self.username_edit.text().strip(),
            self.password_edit.text(),
            self.full_name_edit.text().strip(),
            self.role_combo.currentData(),
        )


class UserManagementWindow(QMainWindow):
    """پنجره اصلی مدیریت کاربران."""

    def __init__(self, repository: AuthRepository):
        super().__init__()
        self.repository = repository

        self.setWindowTitle("GHIAS | مدیریت کاربران")
        self.resize(800, 500)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()
        self._refresh_table()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)

        header = QLabel("مدیریت کاربران")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["نام کاربری", "نام کامل", "نقش", "وضعیت", "آخرین ورود"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()

        add_button = QPushButton("افزودن کاربر جدید")
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self._on_add_user)
        button_row.addWidget(add_button)

        toggle_button = QPushButton("فعال/غیرفعال کردن کاربر انتخاب‌شده")
        toggle_button.clicked.connect(self._on_toggle_active)
        button_row.addWidget(toggle_button)

        change_password_button = QPushButton("تغییر رمز عبور کاربر انتخاب‌شده")
        change_password_button.clicked.connect(self._on_change_password)
        button_row.addWidget(change_password_button)

        layout.addLayout(button_row)

    def _refresh_table(self) -> None:
        users = self.repository.list_users()
        self.table.setRowCount(len(users))
        for row_index, user in enumerate(users):
            self.table.setItem(row_index, 0, QTableWidgetItem(user["username"]))
            item0 = self.table.item(row_index, 0)
            item0.setData(Qt.UserRole, user["id"])
            self.table.setItem(row_index, 1, QTableWidgetItem(user["full_name"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(ROLE_LABELS.get(user["role"], user["role"])))
            self.table.setItem(row_index, 3, QTableWidgetItem("فعال" if user["is_active"] else "غیرفعال"))
            self.table.setItem(row_index, 4, QTableWidgetItem(str(user["last_login_at"] or "—")))

    def _selected_user_id(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "توجه", "ابتدا یک کاربر را از جدول انتخاب کنید.")
            return None
        return self.table.item(selected[0].row(), 0).data(Qt.UserRole)

    def _on_add_user(self) -> None:
        dialog = AddUserDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        username, password, full_name, role = dialog.get_values()
        if not username or not password or not full_name:
            QMessageBox.warning(self, "خطا", "همه فیلدها الزامی هستند.")
            return

        try:
            self.repository.add_user(username, password, full_name, role)
        except ValueError as exc:
            QMessageBox.warning(self, "خطا", str(exc))
            return

        self._refresh_table()
        QMessageBox.information(self, "موفق", f"کاربر «{username}» با موفقیت افزوده شد.")

    def _on_toggle_active(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            return
        users = {u["id"]: u for u in self.repository.list_users()}
        current_status = users[user_id]["is_active"]
        self.repository.set_active(user_id, not current_status)
        self._refresh_table()

    def _on_change_password(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            return
        new_password, ok = QInputDialog.getText(
            self, "تغییر رمز عبور", "رمز عبور جدید را وارد کنید:", QLineEdit.Password
        )
        if ok and new_password:
            self.repository.change_password(user_id, new_password)
            QMessageBox.information(self, "موفق", "رمز عبور با موفقیت تغییر کرد.")

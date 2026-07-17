#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره‌های تخصیص ارزیابی (Assignment Windows)
=============================================================================

این فایل دو پنجره دارد:

    AdminAssignmentWindow
        فقط برای ادمین. ادمین یک واحد، یک حوزه کلان، و یک کاربر (ارزیاب
        یا مصاحبه‌شونده) را انتخاب می‌کند و کار را به او تخصیص می‌دهد.

    MyAssignmentsWindow
        برای ارزیاب و مصاحبه‌شونده. فقط تخصیص‌های خودشان را می‌بینند و
        از همان‌جا وارد فرم پاسخ‌دهی می‌شوند.
=============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))
sys.path.insert(0, str(APP_DIR))

from assignment_repository import AssignmentRepository  # noqa: E402
from assessment_repository import AssessmentRepository  # noqa: E402
from assessment_window import AssessmentWindow  # noqa: E402

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

ROLE_LABELS = {"admin": "ادمین", "inspector": "ارزیاب", "interviewee": "مصاحبه‌شونده"}
STATUS_LABELS = {"PENDING": "شروع‌نشده", "IN_PROGRESS": "در حال انجام", "COMPLETED": "تکمیل‌شده"}


# =============================================================================
# پنجره تخصیص (ادمین)
# =============================================================================

class AdminAssignmentWindow(QMainWindow):
    """پنجره تخصیص ارزیابی به کاربران، مخصوص نقش ادمین."""

    def __init__(
        self,
        assignment_repo: AssignmentRepository,
        assessment_repo: AssessmentRepository,
        current_user: dict[str, Any],
    ):
        super().__init__()
        self.assignment_repo = assignment_repo
        self.assessment_repo = assessment_repo
        self.current_user = current_user

        self.setWindowTitle("GHIAS | تخصیص ارزیابی")
        self.resize(900, 600)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()
        self._load_scope()
        self._refresh_table()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        header = QLabel("تخصیص ارزیابی جدید")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        form_row = QHBoxLayout()

        form_row.addWidget(QLabel("نوع سازمان:"))
        self.type_combo = QComboBox()
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_row.addWidget(self.type_combo)

        form_row.addWidget(QLabel("حوزه کلان:"))
        self.domain_combo = QComboBox()
        form_row.addWidget(self.domain_combo)

        form_row.addWidget(QLabel("واحد:"))
        self.facility_combo = QComboBox()
        form_row.addWidget(self.facility_combo)
        facility_add_button = QPushButton("+ واحد جدید")
        facility_add_button.clicked.connect(self._on_add_facility)
        form_row.addWidget(facility_add_button)

        layout.addLayout(form_row)

        user_row = QHBoxLayout()
        user_row.addWidget(QLabel("تخصیص به کاربر:"))
        self.user_combo = QComboBox()
        user_row.addWidget(self.user_combo, stretch=1)

        assign_button = QPushButton("تخصیص بده")
        assign_button.setObjectName("PrimaryButton")
        assign_button.clicked.connect(self._on_assign)
        user_row.addWidget(assign_button)

        layout.addLayout(user_row)

        history_header = QLabel("تخصیص‌های ثبت‌شده")
        history_header.setObjectName("SectionHeader")
        layout.addWidget(history_header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["واحد", "حوزه", "تخصیص به", "نقش", "وضعیت"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    # ------------------------------------------------------------- بارگذاری
    def _load_scope(self) -> None:
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for facility_type in self.assessment_repo.list_facility_types():
            self.type_combo.addItem(facility_type["type_name"], facility_type["id"])
        self.type_combo.blockSignals(False)

        self.domain_combo.clear()
        for domain in self.assessment_repo.list_domains():
            self.domain_combo.addItem(domain["domain_name"], domain["id"])

        self.user_combo.clear()
        for user in self.assignment_repo.list_assignable_users():
            label = f"{user['full_name']} ({ROLE_LABELS.get(user['role'], user['role'])})"
            self.user_combo.addItem(label, user["id"])

        self._load_facilities()

    def _load_facilities(self, select_id: Optional[int] = None) -> None:
        facility_type_id = self.type_combo.currentData()
        self.facility_combo.clear()
        if facility_type_id is not None:
            for facility in self.assignment_repo.db.query(
                "SELECT id, facility_name FROM facilities WHERE facility_type_id = ? ORDER BY facility_name",
                (facility_type_id,),
            ):
                self.facility_combo.addItem(facility["facility_name"], facility["id"])
        if select_id is not None:
            index = self.facility_combo.findData(select_id)
            if index >= 0:
                self.facility_combo.setCurrentIndex(index)

    def _on_type_changed(self, _index: int) -> None:
        self._load_facilities()

    def _on_add_facility(self) -> None:
        facility_type_id = self.type_combo.currentData()
        if facility_type_id is None:
            QMessageBox.warning(self, "خطا", "ابتدا یک نوع سازمان انتخاب کنید.")
            return
        name, ok = QInputDialog.getText(self, "واحد جدید", "نام واحد را وارد کنید:")
        if ok and name.strip():
            new_id = self.assignment_repo.db.execute(
                "INSERT INTO facilities (facility_name, facility_type_id) VALUES (?, ?)",
                (name.strip(), facility_type_id),
            )
            self._load_facilities(select_id=new_id)

    # ------------------------------------------------------------- تخصیص
    def _on_assign(self) -> None:
        facility_id = self.facility_combo.currentData()
        domain_id = self.domain_combo.currentData()
        user_id = self.user_combo.currentData()

        if facility_id is None or domain_id is None or user_id is None:
            QMessageBox.warning(self, "خطا", "لطفاً واحد، حوزه کلان و کاربر را انتخاب کنید.")
            return

        self.assignment_repo.create_assignment(facility_id, domain_id, user_id, self.current_user["id"])
        self._refresh_table()
        QMessageBox.information(self, "موفق", "تخصیص با موفقیت ثبت شد.")

    def _refresh_table(self) -> None:
        assignments = self.assignment_repo.list_all_assignments()
        self.table.setRowCount(len(assignments))
        for row_index, item in enumerate(assignments):
            self.table.setItem(row_index, 0, QTableWidgetItem(item["facility_name"]))
            self.table.setItem(row_index, 1, QTableWidgetItem(item["domain_name"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(item["assigned_to"]))
            self.table.setItem(row_index, 3, QTableWidgetItem(ROLE_LABELS.get(item["role"], item["role"])))
            self.table.setItem(row_index, 4, QTableWidgetItem(STATUS_LABELS.get(item["status"], item["status"])))


# =============================================================================
# پنجره کارهای من (ارزیاب / مصاحبه‌شونده)
# =============================================================================

class MyAssignmentsWindow(QMainWindow):
    """فهرست تخصیص‌های یک کاربر (ارزیاب یا مصاحبه‌شونده)."""

    def __init__(
        self,
        assignment_repo: AssignmentRepository,
        assessment_repo: AssessmentRepository,
        current_user: dict[str, Any],
    ):
        super().__init__()
        self.assignment_repo = assignment_repo
        self.assessment_repo = assessment_repo
        self.current_user = current_user
        self.assignments: list[dict[str, Any]] = []
        self._child_windows: list[QWidget] = []

        self.setWindowTitle(f"GHIAS | کارهای من — {current_user['full_name']}")
        self.resize(700, 480)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)

        header = QLabel("کارهای تخصیص‌داده‌شده به من")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        open_button = QPushButton("شروع / ادامه")
        open_button.setObjectName("PrimaryButton")
        open_button.clicked.connect(self._on_open_assignment)
        layout.addWidget(open_button)

    def _refresh_list(self) -> None:
        self.assignments = self.assignment_repo.list_my_assignments(self.current_user["id"])
        self.list_widget.clear()
        for item in self.assignments:
            label = (
                f"{item['facility_name']} — {item['domain_name']}   "
                f"[{STATUS_LABELS.get(item['status'], item['status'])}]"
            )
            self.list_widget.addItem(QListWidgetItem(label))

        if not self.assignments:
            self.list_widget.addItem(QListWidgetItem("هنوز هیچ کاری به شما تخصیص داده نشده است."))

    def _on_open_assignment(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.assignments):
            return

        assignment = self.assignments[row]
        visit_id = self.assignment_repo.start_assignment(assignment["id"], self.current_user["full_name"])

        restricted = self.current_user["role"] == "interviewee"
        window = AssessmentWindow(self.assessment_repo, visit_id, restricted=restricted)
        window.show()
        self._child_windows.append(window)
        self._refresh_list()

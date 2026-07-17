#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره ورودی اصلی (Launcher)
=============================================================================

این پنجره بعد از ورود موفق کاربر نمایش داده می‌شود. بخش‌های قابل‌مشاهده
کاملاً بر اساس نقش کاربر (admin / inspector / interviewee) فرق می‌کند:

    admin       - طراح بانک سؤالات، تخصیص ارزیابی، مدیریت کاربران، داشبورد
    inspector   - فقط «کارهای من» (تخصیص‌های داده‌شده به او)
    interviewee - فقط «کارهای من» (با فرم پاسخ‌دهی محدود)
=============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))
sys.path.insert(0, str(APP_DIR))

from database import Database  # noqa: E402
from question_designer import QuestionDesignerWindow, QuestionRepository  # noqa: E402
from assessment_repository import AssessmentRepository  # noqa: E402
from assignment_repository import AssignmentRepository  # noqa: E402
from assignment_window import AdminAssignmentWindow, MyAssignmentsWindow  # noqa: E402
from dashboard_repository import DashboardRepository  # noqa: E402
from dashboard_window import DashboardWindow  # noqa: E402
from auth_repository import AuthRepository  # noqa: E402
from user_management_window import UserManagementWindow  # noqa: E402

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ROLE_LABELS = {"admin": "ادمین", "inspector": "ارزیاب", "interviewee": "مصاحبه‌شونده"}


class LauncherWindow(QMainWindow):
    """پنجره اصلی ورودی نرم‌افزار GHIAS، بر اساس نقش کاربر وارد‌شده."""

    def __init__(self, db: Database, current_user: dict[str, Any]):
        super().__init__()
        self.db = db
        self.current_user = current_user

        self._child_windows: list[QWidget] = []

        role_label = ROLE_LABELS.get(current_user["role"], current_user["role"])
        self.setWindowTitle(f"GHIAS | {current_user['full_name']} ({role_label})")
        self.resize(1000, 440)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("سامانه قیاس (GHIAS)")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        role_label = ROLE_LABELS.get(self.current_user["role"], self.current_user["role"])
        subtitle = QLabel(f"خوش آمدید، {self.current_user['full_name']} ({role_label})")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        card_row = QHBoxLayout()
        card_row.setSpacing(20)

        role = self.current_user["role"]

        if role == "admin":
            card_row.addWidget(self._build_option_card(
                "طراح بانک سؤالات",
                "افزودن، ویرایش و مدیریت سؤالات ارزیابی",
                self._open_question_designer,
            ))
            card_row.addWidget(self._build_option_card(
                "تخصیص ارزیابی",
                "انتخاب واحد و حوزه، و تخصیص کار به ارزیاب یا مصاحبه‌شونده",
                self._open_assignment,
            ))
            card_row.addWidget(self._build_option_card(
                "مدیریت کاربران",
                "افزودن کاربر، تعیین نقش، فعال/غیرفعال کردن",
                self._open_user_management,
            ))
            card_row.addWidget(self._build_option_card(
                "داشبورد و گزارش وضعیت",
                "مشاهده نمودار امتیاز حوزه‌ها، روند زمانی و اقدامات اصلاحی",
                self._open_dashboard,
            ))
        else:
            card_row.addWidget(self._build_option_card(
                "کارهای من",
                "مشاهده و انجام ارزیابی‌هایی که برای شما تخصیص داده شده",
                self._open_my_assignments,
            ))

        layout.addLayout(card_row)
        layout.addStretch(1)

    def _build_option_card(self, title_text: str, description_text: str, on_click) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)

        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        card_layout.addWidget(title_label)

        description_label = QLabel(description_text)
        description_label.setWordWrap(True)
        card_layout.addWidget(description_label)

        card_layout.addStretch(1)

        button = QPushButton("ورود")
        button.setObjectName("PrimaryButton")
        button.clicked.connect(on_click)
        card_layout.addWidget(button)

        return card

    # ------------------------------------------------------------- بازکردن بخش‌ها (ادمین)
    def _open_question_designer(self) -> None:
        repository = QuestionRepository(self.db)
        window = QuestionDesignerWindow(repository)
        window.show()
        self._child_windows.append(window)

    def _open_assignment(self) -> None:
        assignment_repo = AssignmentRepository(self.db)
        assessment_repo = AssessmentRepository(self.db)
        window = AdminAssignmentWindow(assignment_repo, assessment_repo, self.current_user)
        window.show()
        self._child_windows.append(window)

    def _open_user_management(self) -> None:
        repository = AuthRepository(self.db)
        window = UserManagementWindow(repository)
        window.show()
        self._child_windows.append(window)

    def _open_dashboard(self) -> None:
        repository = DashboardRepository(self.db)
        window = DashboardWindow(repository)
        window.show()
        self._child_windows.append(window)

    # ------------------------------------------------------------- بازکردن بخش‌ها (ارزیاب/مصاحبه‌شونده)
    def _open_my_assignments(self) -> None:
        assignment_repo = AssignmentRepository(self.db)
        assessment_repo = AssessmentRepository(self.db)
        window = MyAssignmentsWindow(assignment_repo, assessment_repo, self.current_user)
        window.show()
        self._child_windows.append(window)

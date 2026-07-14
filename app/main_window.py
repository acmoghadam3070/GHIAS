#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره ورودی اصلی (Launcher)
=============================================================================

این فایل اولین پنجره‌ای است که هنگام اجرای برنامه دیده می‌شود.
از اینجا کاربر بین بخش‌های مختلف نرم‌افزار انتخاب می‌کند:
    - طراح بانک سؤالات
    - شروع یا ادامه یک ارزیابی میدانی

با اضافه‌شدن بخش‌های آینده پروژه (داشبورد، گزارش‌ساز و غیره)،
دکمه‌های بیشتری به همین پنجره اضافه خواهد شد.
=============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))
sys.path.insert(0, str(APP_DIR))

from database import Database  # noqa: E402
from question_designer import QuestionDesignerWindow, QuestionRepository  # noqa: E402
from assessment_repository import AssessmentRepository  # noqa: E402
from assessment_window import AssessmentWindow, StartVisitDialog  # noqa: E402
from dashboard_repository import DashboardRepository  # noqa: E402
from dashboard_window import DashboardWindow  # noqa: E402

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


class LauncherWindow(QMainWindow):
    """پنجره اصلی ورودی نرم‌افزار GHIAS."""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db

        # نگه‌داشتن ارجاع به پنجره‌های فرزند، تا Garbage Collector آن‌ها را
        # زودتر از موعد نبندد
        self._child_windows: list[QWidget] = []

        self.setWindowTitle("GHIAS | سامانه ارزیابی هوشمند حفاظت فیزیکی بیمارستان")
        self.resize(980, 440)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("سامانه GHIAS")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("ارزیابی هوشمند حفاظت فیزیکی بیمارستان — یک بخش را انتخاب کنید")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        card_row = QHBoxLayout()
        card_row.setSpacing(20)

        card_row.addWidget(self._build_option_card(
            "طراح بانک سؤالات",
            "افزودن، ویرایش و مدیریت سؤالات ارزیابی",
            self._open_question_designer,
        ))

        card_row.addWidget(self._build_option_card(
            "ارزیابی میدانی جدید",
            "شروع یا ادامه ارزیابی یک واحد (بیمارستان، کارخانه و غیره)",
            self._open_assessment,
        ))

        card_row.addWidget(self._build_option_card(
            "داشبورد و گزارش وضعیت",
            "مشاهده نمودار امتیاز حوزه‌ها، روند زمانی و اقدامات اصلاحی",
            self._open_dashboard,
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

    # ------------------------------------------------------------- بازکردن بخش‌ها
    def _open_question_designer(self) -> None:
        repository = QuestionRepository(self.db)
        window = QuestionDesignerWindow(repository)
        window.show()
        self._child_windows.append(window)

    def _open_assessment(self) -> None:
        repository = AssessmentRepository(self.db)

        dialog = StartVisitDialog(repository, self)
        if dialog.exec() != StartVisitDialog.Accepted:
            return

        facility_id = dialog.selected_facility_id
        inspector_id = dialog.selected_inspector_id

        open_visit = repository.get_open_visit(facility_id, inspector_id)
        if open_visit is not None:
            visit_id = open_visit["id"]
        else:
            visit_id = repository.create_visit(facility_id, inspector_id)

        window = AssessmentWindow(repository, visit_id)
        window.show()
        self._child_windows.append(window)

    def _open_dashboard(self) -> None:
        repository = DashboardRepository(self.db)
        window = DashboardWindow(repository)
        window.show()
        self._child_windows.append(window)

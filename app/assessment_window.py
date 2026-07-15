#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره ارزیابی میدانی (Assessment Window)
=============================================================================

این فایل رابط گرافیکی فرم ارزیابی میدانی را می‌سازد.
ارزیاب از این پنجره برای موارد زیر استفاده می‌کند:
    - انتخاب یا افزودن بیمارستان و ارزیاب
    - شروع بازدید جدید یا ادامه بازدید ناتمام
    - پاسخ‌دهی به سؤالات هر حوزه
    - مشاهده زنده امتیاز و سطح ریسک هر حوزه (با موتور امتیازدهی)
    - پایان‌دادن نهایی به بازدید و ثبت امتیاز کلی
=============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))
sys.path.insert(0, str(PROJECT_ROOT / "engine"))
sys.path.insert(0, str(APP_DIR))

from database import Database  # noqa: E402
from assessment_repository import AssessmentRepository  # noqa: E402
from scoring_engine import AnswerRecord, ScoringEngine  # noqa: E402
from recommendation_engine import DeficientAnswer, RecommendationEngine  # noqa: E402

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


# رنگ نمایش هر سطح ریسک، برای هماهنگی با موتور قوانین
RISK_COLORS: dict[str, str] = {
    "بحرانی": "#eb5757",
    "هشدار": "#f2994a",
    "قابل قبول": "#27ae60",
    "بدون داده": "#9aa5b1",
}


# =============================================================================
# دیالوگ شروع یا ادامه بازدید
# =============================================================================

class StartVisitDialog(QDialog):
    """
    دیالوگی برای انتخاب نوع سازمان، واحد تحت ارزیابی و ارزیاب،
    پیش از شروع یا ادامه یک بازدید.
    """

    def __init__(self, repository: AssessmentRepository, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.repository = repository
        self.facility_types: list[dict[str, Any]] = []
        self.selected_facility_id: Optional[int] = None
        self.selected_domain_id: Optional[int] = None
        self.selected_inspector_id: Optional[int] = None

        self.setWindowTitle("شروع ارزیابی جدید")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("نوع سازمان:"))
        type_row = QHBoxLayout()
        self.type_combo = QComboBox()
        type_row.addWidget(self.type_combo, stretch=1)
        type_add_button = QPushButton("+ افزودن")
        type_add_button.clicked.connect(self._add_new_facility_type)
        type_row.addWidget(type_add_button)
        layout.addLayout(type_row)

        layout.addWidget(QLabel("حوزه کلان ارزیابی:"))
        domain_row = QHBoxLayout()
        self.domain_combo = QComboBox()
        domain_row.addWidget(self.domain_combo, stretch=1)
        domain_add_button = QPushButton("+ افزودن")
        domain_add_button.clicked.connect(self._add_new_domain)
        domain_row.addWidget(domain_add_button)
        layout.addLayout(domain_row)

        layout.addWidget(QLabel("نام واحد (مثلاً نام بیمارستان):"))
        facility_row = QHBoxLayout()
        self.facility_combo = QComboBox()
        facility_row.addWidget(self.facility_combo, stretch=1)
        facility_add_button = QPushButton("+ افزودن")
        facility_add_button.clicked.connect(self._add_new_facility)
        facility_row.addWidget(facility_add_button)
        layout.addLayout(facility_row)

        layout.addWidget(QLabel("ارزیاب:"))
        inspector_row = QHBoxLayout()
        self.inspector_combo = QComboBox()
        inspector_row.addWidget(self.inspector_combo, stretch=1)
        inspector_add_button = QPushButton("+ افزودن")
        inspector_add_button.clicked.connect(self._add_new_inspector)
        inspector_row.addWidget(inspector_add_button)
        layout.addLayout(inspector_row)

        self._load_facility_types()
        self._load_domains()
        self._load_inspectors()
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("شروع / ادامه ارزیابی")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------- بارگذاری
    def _load_facility_types(self, select_id: Optional[int] = None) -> None:
        self.facility_types = self.repository.list_facility_types()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for facility_type in self.facility_types:
            self.type_combo.addItem(facility_type["type_name"], facility_type["id"])
        self.type_combo.blockSignals(False)

        if select_id is not None:
            index = self.type_combo.findData(select_id)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)

        if self.facility_types:
            self._load_facilities(self.type_combo.currentData())

    def _load_facilities(self, facility_type_id: Optional[int], select_id: Optional[int] = None) -> None:
        self.facility_combo.blockSignals(True)
        self.facility_combo.clear()
        if facility_type_id is not None:
            for facility in self.repository.list_facilities(facility_type_id):
                self.facility_combo.addItem(facility["facility_name"], facility["id"])
        self.facility_combo.blockSignals(False)

        if select_id is not None:
            index = self.facility_combo.findData(select_id)
            if index >= 0:
                self.facility_combo.setCurrentIndex(index)

    def _load_domains(self, select_id: Optional[int] = None) -> None:
        self.domain_combo.blockSignals(True)
        self.domain_combo.clear()
        for domain in self.repository.list_domains():
            self.domain_combo.addItem(domain["domain_name"], domain["id"])
        self.domain_combo.blockSignals(False)

        if select_id is not None:
            index = self.domain_combo.findData(select_id)
            if index >= 0:
                self.domain_combo.setCurrentIndex(index)

    def _load_inspectors(self, select_id: Optional[int] = None) -> None:
        self.inspector_combo.blockSignals(True)
        self.inspector_combo.clear()
        for inspector in self.repository.list_inspectors():
            self.inspector_combo.addItem(inspector["full_name"], inspector["id"])
        self.inspector_combo.blockSignals(False)
        if select_id is not None:
            index = self.inspector_combo.findData(select_id)
            if index >= 0:
                self.inspector_combo.setCurrentIndex(index)

    def _on_type_changed(self, _index: int) -> None:
        self._load_facilities(self.type_combo.currentData())

    # ------------------------------------------------------------- افزودن مورد جدید
    def _add_new_facility_type(self) -> None:
        name, ok = QInputDialog.getText(
            self, "نوع سازمان جدید", "نام نوع سازمان را وارد کنید (مثلاً کارخانه، اداره):"
        )
        if ok and name.strip():
            new_id = self.repository.add_facility_type(name.strip())
            self._load_facility_types(select_id=new_id)
            QMessageBox.information(
                self,
                "نوع سازمان اضافه شد",
                f"نوع سازمان «{name.strip()}» ساخته شد.\n\n"
                "توجه: هنوز هیچ حوزه یا سؤالی برای این نوع سازمان تعریف نشده است. "
                "برای ارزیابی واقعی، ابتدا باید از بخش طراح بانک سؤالات، حوزه‌ها و "
                "سؤالات این نوع سازمان را اضافه کنید.",
            )

    def _add_new_domain(self) -> None:
        name, ok = QInputDialog.getText(
            self, "حوزه کلان ارزیابی جدید", "نام حوزه کلان را وارد کنید (مثلاً امنیت اطلاعات، پدافند غیرعامل):"
        )
        if ok and name.strip():
            new_id = self.repository.add_domain(name.strip())
            self._load_domains(select_id=new_id)
            QMessageBox.information(
                self,
                "حوزه کلان اضافه شد",
                f"حوزه کلان «{name.strip()}» ساخته شد.\n\n"
                "توجه: هنوز هیچ زیرحوزه یا سؤالی برای این حوزه تعریف نشده است. "
                "برای ارزیابی واقعی، ابتدا باید از بخش طراح بانک سؤالات، زیرحوزه‌ها و "
                "سؤالات این حوزه را اضافه کنید.",
            )

    def _add_new_facility(self) -> None:
        facility_type_id = self.type_combo.currentData()
        if facility_type_id is None:
            QMessageBox.warning(self, "خطا", "ابتدا یک نوع سازمان انتخاب کنید.")
            return
        name, ok = QInputDialog.getText(self, "واحد جدید", "نام واحد را وارد کنید:")
        if ok and name.strip():
            new_id = self.repository.add_facility(name.strip(), facility_type_id)
            self._load_facilities(facility_type_id, select_id=new_id)

    def _add_new_inspector(self) -> None:
        name, ok = QInputDialog.getText(self, "ارزیاب جدید", "نام ارزیاب را وارد کنید:")
        if ok and name.strip():
            new_id = self.repository.add_inspector(name.strip())
            self._load_inspectors(select_id=new_id)

    # ------------------------------------------------------------- تأیید
    def _on_accept(self) -> None:
        facility_id = self.facility_combo.currentData()
        domain_id = self.domain_combo.currentData()
        inspector_id = self.inspector_combo.currentData()

        if facility_id is None or domain_id is None or inspector_id is None:
            QMessageBox.warning(
                self,
                "خطا",
                "لطفاً یک واحد، یک حوزه کلان ارزیابی، و یک ارزیاب انتخاب کنید.\n"
                "اگر فهرست خالی است، ابتدا با دکمه «+ افزودن» یک مورد جدید بسازید.",
            )
            return

        self.selected_facility_id = facility_id
        self.selected_domain_id = domain_id
        self.selected_inspector_id = inspector_id
        self.accept()


# =============================================================================
# کارت نمایش و پاسخ‌دهی به یک سؤال
# =============================================================================

class QuestionCard(QFrame):
    """
    یک کارت که یک سؤال را نمایش می‌دهد و امکان پاسخ‌دهی به آن را می‌دهد.
    نوع ویجت پاسخ، بسته به answer_type سؤال متفاوت است.
    """

    def __init__(self, question: dict[str, Any], existing_answer: Optional[dict[str, Any]]):
        super().__init__()
        self.setObjectName("Card")
        self.question = question

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QLabel(f"[{question['question_code']}] (وزن {question['weight']})  {question['question_text']}")
        header.setWordWrap(True)
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        answer_row = QHBoxLayout()
        answer_row.addWidget(QLabel("پاسخ:"))

        self.answer_type = question["answer_type"]
        self.answer_widget: QWidget

        if self.answer_type == "yes_no":
            combo = QComboBox()
            combo.addItems(["", "بله", "خیر"])
            if existing_answer is not None:
                idx = combo.findText(str(existing_answer["answer_value"]))
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.answer_widget = combo

        elif self.answer_type == "scale_1_5":
            combo = QComboBox()
            combo.addItems(["", "1", "2", "3", "4", "5"])
            if existing_answer is not None:
                idx = combo.findText(str(existing_answer["answer_value"]))
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.answer_widget = combo

        elif self.answer_type == "percentage":
            edit = QLineEdit()
            edit.setPlaceholderText("عددی بین ۰ تا ۱۰۰")
            if existing_answer is not None:
                edit.setText(str(existing_answer["answer_value"]))
            self.answer_widget = edit

        else:  # multiple_choice یا text
            edit = QLineEdit()
            edit.setPlaceholderText("پاسخ را وارد کنید")
            if existing_answer is not None:
                edit.setText(str(existing_answer["answer_value"]))
            self.answer_widget = edit

        answer_row.addWidget(self.answer_widget, stretch=1)
        layout.addLayout(answer_row)

        comment_row = QHBoxLayout()
        comment_row.addWidget(QLabel("توضیح:"))
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("توضیح اختیاری ارزیاب")
        if existing_answer is not None and existing_answer.get("comment"):
            self.comment_edit.setText(existing_answer["comment"])
        comment_row.addWidget(self.comment_edit, stretch=1)
        layout.addLayout(comment_row)

    def get_answer_value(self) -> str:
        """بازگرداندن مقدار خام پاسخ، مستقل از نوع ویجت."""
        if isinstance(self.answer_widget, QComboBox):
            return self.answer_widget.currentText()
        if isinstance(self.answer_widget, QLineEdit):
            return self.answer_widget.text().strip()
        return ""

    def get_comment(self) -> str:
        return self.comment_edit.text().strip()


# =============================================================================
# پنجره اصلی ارزیابی میدانی
# =============================================================================

class AssessmentWindow(QMainWindow):
    """پنجره اصلی فرم ارزیابی میدانی برای یک بازدید مشخص."""

    def __init__(self, repository: AssessmentRepository, visit_id: int):
        super().__init__()
        self.repository = repository
        self.visit_id = visit_id
        self.scoring_engine = ScoringEngine()
        self.recommendation_engine = RecommendationEngine()

        self.categories: list[dict[str, Any]] = []
        self.current_category_id: Optional[int] = None
        self.question_cards: dict[int, QuestionCard] = {}
        self.category_results: dict[int, Any] = {}

        visit = self.repository.get_visit(visit_id)
        self.facility_type_id = visit["facility_type_id"]
        self.domain_id = visit["domain_id"]
        self.setWindowTitle(
            f"GHIAS | ارزیابی میدانی — {visit['facility_name']} — حوزه: {visit['domain_name']} — ارزیاب: {visit['inspector_name']}"
        )
        self.resize(1300, 780)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()
        self._load_categories()

    # ------------------------------------------------------------- ساخت رابط
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- سایدبار حوزه‌ها -------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 10)

        sidebar_title = QLabel("حوزه‌های ارزیابی")
        sidebar_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.domain_list = QListWidget()
        self.domain_list.setObjectName("DomainList")
        self.domain_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.domain_list.setWordWrap(True)
        self.domain_list.currentRowChanged.connect(self._on_domain_selected)
        sidebar_layout.addWidget(self.domain_list)

        self.finish_button = QPushButton("پایان ارزیابی و ثبت نهایی")
        self.finish_button.setObjectName("DangerButton")
        self.finish_button.clicked.connect(self._on_finish_visit)
        sidebar_layout.addWidget(self.finish_button)

        root_layout.addWidget(sidebar)

        # --- ناحیه اصلی -----------------------------------------------------
        main_panel = QWidget()
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(10)

        self.summary_label = QLabel("امتیاز کلی: بدون داده")
        self.summary_label.setObjectName("SectionHeader")
        main_layout.addWidget(self.summary_label)

        self.header_label = QLabel("یک حوزه را از فهرست کنار صفحه انتخاب کنید")
        main_layout.addWidget(self.header_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch(1)
        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.save_category_button = QPushButton("ذخیره پاسخ‌های این حوزه")
        self.save_category_button.setObjectName("PrimaryButton")
        self.save_category_button.clicked.connect(self._on_save_category)
        main_layout.addWidget(self.save_category_button)

        root_layout.addWidget(main_panel, stretch=1)

        self.statusBar().showMessage("آماده")

    # ------------------------------------------------------------- حوزه‌ها
    def _load_categories(self) -> None:
        self.categories = self.repository.list_categories(self.facility_type_id, self.domain_id)
        self.domain_list.blockSignals(True)
        self.domain_list.clear()
        for category in self.categories:
            self.domain_list.addItem(QListWidgetItem(category["category_name"]))
        self.domain_list.blockSignals(False)

        if self.categories:
            self.domain_list.setCurrentRow(0)

        self._recompute_overall()

    def _on_domain_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.categories):
            return
        category = self.categories[row]
        self.current_category_id = category["id"]
        self.header_label.setText(f"حوزه: {category['category_name']}")
        self._render_questions(category["id"])

    def _render_questions(self, category_id: int) -> None:
        # پاک‌سازی کارت‌های قبلی
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.question_cards.clear()

        questions = self.repository.list_questions(category_id)
        answers_map = self.repository.get_answers_for_visit(self.visit_id)

        for question in questions:
            existing = answers_map.get(question["id"])
            card = QuestionCard(question, existing)
            self.question_cards[question["id"]] = card
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    # ------------------------------------------------------------- ذخیره پاسخ‌ها
    def _on_save_category(self) -> None:
        if self.current_category_id is None or not self.question_cards:
            return

        from rule_engine import compute_answer_score

        for question_id, card in self.question_cards.items():
            raw_value = card.get_answer_value()
            if raw_value == "":
                continue  # سؤال هنوز پاسخ داده نشده، رد می‌شود
            score = compute_answer_score(card.answer_type, raw_value)
            self.repository.upsert_answer(
                self.visit_id, question_id, raw_value, score, card.get_comment()
            )

        self._update_category_result(self.current_category_id)
        self._recompute_overall()

        QMessageBox.information(self, "ذخیره موفق", "پاسخ‌های این حوزه ذخیره شد.")

    def _update_category_result(self, category_id: int) -> None:
        category = next(c for c in self.categories if c["id"] == category_id)
        questions = self.repository.list_questions(category_id)
        answers_map = self.repository.get_answers_for_visit(self.visit_id)

        records = [
            AnswerRecord(
                question_id=q["id"],
                category_id=category_id,
                weight=q["weight"],
                answer_type=q["answer_type"],
                answer_value=answers_map[q["id"]]["answer_value"],
                is_critical=bool(q["is_critical"]),
            )
            for q in questions
            if q["id"] in answers_map
        ]

        result = self.scoring_engine.compute_category(
            category_id, category["category_name"], records, len(questions)
        )
        self.category_results[category_id] = result

        # بروزرسانی متن ردیف حوزه در سایدبار، همراه با رنگ متناظر با وضعیت ریسک
        row_index = self.categories.index(category)
        color = RISK_COLORS.get(result.risk_label, "#d7dee6")
        item = self.domain_list.item(row_index)
        item.setText(
            f"{category['category_name']}   ({result.answered_count}/{result.total_questions})"
        )
        item.setToolTip(f"امتیاز: {result.score}   وضعیت: {result.risk_label}")
        item.setForeground(QBrush(QColor(color)))

    def _recompute_overall(self) -> None:
        if not self.category_results:
            # اگر هنوز هیچ حوزه‌ای ذخیره نشده، امتیاز هر حوزه‌ای که از قبل
            # پاسخ دارد را بازسازی می‌کنیم تا بعد از «ادامه ارزیابی» هم
            # وضعیت واقعی نمایش داده شود.
            for category in self.categories:
                self._update_category_result(category["id"])

        overall = self.scoring_engine.compute_overall(list(self.category_results.values()))
        color = RISK_COLORS.get(overall.overall_risk_label, "#9aa5b1")
        self.summary_label.setText(
            f"امتیاز کلی: {overall.overall_score}   |   وضعیت کلی: {overall.overall_risk_label}"
        )
        self.summary_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 16px;")

    # ------------------------------------------------------------- پایان ارزیابی
    def _on_finish_visit(self) -> None:
        confirm = QMessageBox.question(
            self,
            "پایان ارزیابی",
            "آیا از ثبت نهایی این ارزیابی اطمینان دارید؟\n"
            "بعد از این مرحله، بازدید به‌عنوان «تکمیل‌شده» علامت‌گذاری می‌شود.",
        )
        if confirm != QMessageBox.Yes:
            return

        for category in self.categories:
            self._update_category_result(category["id"])

        overall = self.scoring_engine.compute_overall(list(self.category_results.values()))
        self.repository.finish_visit(self.visit_id, overall.overall_score, overall.overall_risk_label)

        # ساخت اقدامات اصلاحی از روی پاسخ‌های ناقص این بازدید
        deficient_rows = self.repository.get_deficient_answers(self.visit_id)
        deficient_answers = [
            DeficientAnswer(
                answer_id=row["answer_id"],
                question_id=row["question_id"],
                question_code=row["question_code"],
                category_name=row["category_name"],
                weight=row["weight"],
                is_critical=bool(row["is_critical"]),
                score=row["score"],
                recommendation_text=row["recommendation_text"] or "",
            )
            for row in deficient_rows
        ]
        recommendations = self.recommendation_engine.generate(deficient_answers)

        if recommendations:
            self.repository.save_recommendations(
                [
                    {
                        "answer_id": r.answer_id,
                        "recommendation_text": r.recommendation_text,
                        "priority": r.priority,
                    }
                    for r in recommendations
                ]
            )

        self._show_finish_summary(overall, recommendations)
        self.close()

    def _show_finish_summary(self, overall, recommendations: list) -> None:
        """نمایش خلاصه نهایی ارزیابی، شامل امتیاز کلی و مهم‌ترین اقدامات اصلاحی."""
        lines = [
            f"امتیاز کلی: {overall.overall_score}",
            f"وضعیت کلی: {overall.overall_risk_label}",
            "",
        ]

        if recommendations:
            lines.append(f"تعداد اقدامات اصلاحی پیشنهادی: {len(recommendations)}")
            lines.append("")
            lines.append("مهم‌ترین موارد:")
            for rec in recommendations[:5]:
                lines.append(f"  • [{rec.priority}] {rec.question_code}: {rec.recommendation_text}")
            if len(recommendations) > 5:
                lines.append(f"  ... و {len(recommendations) - 5} مورد دیگر")
        else:
            lines.append("هیچ نقص قابل‌توجهی ثبت نشد.")

        QMessageBox.information(self, "ثبت نهایی شد", "\n".join(lines))

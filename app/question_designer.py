#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
ماژول: طراح بانک سؤالات (نسخه دوم - مبتنی بر PySide6 و پایگاه داده SQLite)
=============================================================================

این فایل جایگزین کامل نسخه قدیمی (Tkinter و فایل JSON) است.

تفاوت اصلی با نسخه قبلی:
    - رابط کاربری با PySide6 (Qt) ساخته شده، نه Tkinter.
    - داده‌ها مستقیم از پایگاه داده SQLite خوانده و نوشته می‌شوند،
      نه از فایل JSON.
    - شماره‌گذاری شناسه سؤالات کاملاً به‌صورت خودکار توسط خود پایگاه داده
      انجام می‌شود.
    - هر عملیات ذخیره، بلافاصله و مستقیم در پایگاه داده ثبت می‌شود؛
      نیازی به دکمه جداگانه «ذخیره در فایل» نیست.

قابلیت‌ها:
    - نمایش حوزه‌های ارزیابی (خوانده‌شده از جدول categories)
    - نمایش بانک سؤالات هر حوزه در جدول
    - جستجوی سؤالات بر اساس کد یا متن سؤال
    - انتخاب سؤال و نمایش کامل اطلاعات آن در فرم
    - ویرایش واقعی رکورد انتخاب‌شده
    - افزودن سؤال جدید
    - حذف سؤال
    - جلوگیری از ثبت کد سؤال تکراری در کل بانک سؤالات
=============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

# افزودن پوشه database به مسیر جست‌وجوی پایتون تا ماژول database
# مستقل از محل اجرای برنامه، قابل وارد کردن باشد.
APP_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "database"))

from database import Database, get_database  # noqa: E402
from import_excel_questions import ExcelImporter  # noqa: E402

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# =============================================================================
# ثابت‌های رابط کاربری
# =============================================================================

ANSWER_TYPES: list[str] = [
    "yes_no",
    "scale_1_5",
    "percentage",
    "multiple_choice",
    "text",
]

WINDOW_TITLE = "GHIAS | طراح بانک سؤالات ارزیابی حفاظت فیزیکی بیمارستان"

# صفحه‌آرایی و رنگ‌بندی برنامه (Design System واحد پروژه GHIAS)
STYLE_SHEET = """
QWidget {
    background-color: #f4f6f8;
    color: #1f2d3d;
    font-family: "Tahoma";
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #1c2b3a;
}

QLabel#SidebarTitle {
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    padding: 14px 10px 8px 10px;
}

QListWidget#DomainList {
    background-color: #1c2b3a;
    border: none;
    color: #d7dee6;
    font-size: 12px;
    outline: none;
}

QListWidget#DomainList::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 3px 8px;
    min-height: 34px;
}

QListWidget#DomainList::item:selected {
    background-color: #2f80ed;
    color: #ffffff;
}

QListWidget#DomainList::item:hover:!selected {
    background-color: #26374a;
}

QLabel#SectionHeader {
    font-size: 16px;
    font-weight: bold;
    color: #1c2b3a;
    padding: 4px 0px;
}

QFrame#Card {
    background-color: #ffffff;
    border: 1px solid #e1e6ea;
    border-radius: 10px;
}

QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #d3dae1;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: #2f80ed;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #2f80ed;
}

QPushButton {
    background-color: #e7ebef;
    color: #1c2b3a;
    border: none;
    border-radius: 6px;
    padding: 9px 14px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #dce2e8;
}

QPushButton#PrimaryButton {
    background-color: #2f80ed;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    background-color: #2568c4;
}

QPushButton#DangerButton {
    background-color: #eb5757;
    color: #ffffff;
}

QPushButton#DangerButton:hover {
    background-color: #c94444;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e1e6ea;
    border-radius: 8px;
    gridline-color: #eef1f4;
    selection-background-color: #dce9fd;
    selection-color: #1c2b3a;
}

QHeaderView::section {
    background-color: #f0f3f6;
    color: #1c2b3a;
    padding: 8px;
    border: none;
    font-weight: bold;
}

QStatusBar {
    background-color: #eef1f4;
    color: #444d56;
}
"""


# =============================================================================
# لایه دسترسی به داده مخصوص سؤالات
# =============================================================================

class QuestionRepository:
    """
    مسئول تمام عملیات مربوط به جدول‌های categories و questions.
    این کلاس هیچ وابستگی به رابط گرافیکی ندارد.
    """

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------- حوزه‌ها
    def list_categories(self) -> list[dict[str, Any]]:
        """بازگرداندن لیست حوزه‌ها به ترتیب نمایش تعریف‌شده."""
        rows = self.db.query(
            "SELECT id, category_key, category_name FROM categories "
            "WHERE is_active = 1 ORDER BY display_order"
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------- سؤالات
    def list_questions(self, category_id: int, keyword: str = "") -> list[dict[str, Any]]:
        """
        بازگرداندن سؤالات یک حوزه، با فیلتر اختیاری بر اساس کد یا متن سؤال.
        """
        if keyword.strip():
            pattern = f"%{keyword.strip()}%"
            rows = self.db.query(
                """
                SELECT * FROM questions
                WHERE category_id = ?
                  AND (question_code LIKE ? OR question_text LIKE ?)
                ORDER BY id
                """,
                (category_id, pattern, pattern),
            )
        else:
            rows = self.db.query(
                "SELECT * FROM questions WHERE category_id = ? ORDER BY id",
                (category_id,),
            )
        return [dict(row) for row in rows]

    def get_question(self, question_id: int) -> Optional[dict[str, Any]]:
        row = self.db.query_one("SELECT * FROM questions WHERE id = ?", (question_id,))
        return dict(row) if row is not None else None

    def is_duplicate_code(self, code: str, exclude_id: Optional[int] = None) -> bool:
        """
        بررسی یکتا بودن کد سؤال در کل بانک سؤالات (نه فقط یک حوزه)،
        چون کد سؤال در پایگاه داده به‌صورت سراسری یکتا تعریف شده است.
        """
        if exclude_id is None:
            row = self.db.query_one(
                "SELECT id FROM questions WHERE question_code = ?", (code,)
            )
        else:
            row = self.db.query_one(
                "SELECT id FROM questions WHERE question_code = ? AND id != ?",
                (code, exclude_id),
            )
        return row is not None

    def insert_question(self, data: dict[str, Any]) -> int:
        """درج یک سؤال جدید. خروجی، شناسه (id) رکورد تازه‌ساخته‌شده است."""
        return self.db.execute(
            """
            INSERT INTO questions (
                category_id, question_code, question_text, answer_type,
                weight, standard_reference, recommendation, evaluator_guide
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["category_id"], data["code"], data["title"], data["answer_type"],
                data["weight"], data["standard"], data["recommendation"],
                data["evaluator_guide"],
            ),
        )

    def update_question(self, question_id: int, data: dict[str, Any]) -> None:
        """بروزرسانی یک رکورد موجود؛ هیچ رکورد جدیدی ساخته نمی‌شود."""
        self.db.execute(
            """
            UPDATE questions
            SET category_id = ?, question_code = ?, question_text = ?,
                answer_type = ?, weight = ?, standard_reference = ?,
                recommendation = ?, evaluator_guide = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                data["category_id"], data["code"], data["title"], data["answer_type"],
                data["weight"], data["standard"], data["recommendation"],
                data["evaluator_guide"], question_id,
            ),
        )

    def delete_question(self, question_id: int) -> None:
        self.db.execute("DELETE FROM questions WHERE id = ?", (question_id,))


# =============================================================================
# رابط گرافیکی اصلی
# =============================================================================

class QuestionDesignerWindow(QMainWindow):
    """پنجره اصلی طراح بانک سؤالات."""

    def __init__(self, repository: QuestionRepository):
        super().__init__()
        self.repository = repository

        self.categories: list[dict[str, Any]] = []
        self.current_category_id: Optional[int] = None
        self.selected_question_id: Optional[int] = None

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1320, 780)
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
        sidebar.setFixedWidth(290)
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

        root_layout.addWidget(sidebar)

        # --- ناحیه میانی: جستجو + جدول سؤالات ----------------------------
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(16, 16, 16, 16)
        center_layout.setSpacing(10)

        self.header_label = QLabel("انتخاب یک حوزه از فهرست کنار صفحه")
        self.header_label.setObjectName("SectionHeader")
        center_layout.addWidget(self.header_label)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("جستجو بر اساس کد یا متن سؤال...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_edit, stretch=1)

        import_button = QPushButton("درون‌ریزی از اکسل")
        import_button.setObjectName("PrimaryButton")
        import_button.clicked.connect(self._on_import_excel)
        search_row.addWidget(import_button)

        center_layout.addLayout(search_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["کد", "متن سؤال", "وزن", "نوع پاسخ"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        center_layout.addWidget(self.table)

        root_layout.addWidget(center_panel, stretch=1)

        # --- پنل فرم سمت چپ ------------------------------------------------
        form_card = QFrame()
        form_card.setObjectName("Card")
        form_card.setFixedWidth(420)
        form_outer = QVBoxLayout(form_card)
        form_outer.setContentsMargins(18, 18, 18, 18)
        form_outer.setSpacing(10)

        form_title = QLabel("اطلاعات سؤال")
        form_title.setObjectName("SectionHeader")
        form_outer.addWidget(form_title)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.id_display = QLineEdit()
        self.id_display.setReadOnly(True)
        self.id_display.setAlignment(Qt.AlignCenter)
        form_layout.addRow("شناسه:", self.id_display)

        self.code_edit = QLineEdit()
        form_layout.addRow("کد سؤال:", self.code_edit)

        self.title_edit = QTextEdit()
        self.title_edit.setFixedHeight(70)
        form_layout.addRow("متن سؤال:", self.title_edit)

        self.category_combo = QComboBox()
        form_layout.addRow("دسته‌بندی:", self.category_combo)

        self.weight_spin = QSpinBox()
        self.weight_spin.setRange(1, 100)
        self.weight_spin.setValue(1)
        form_layout.addRow("وزن:", self.weight_spin)

        self.answer_type_combo = QComboBox()
        self.answer_type_combo.addItems(ANSWER_TYPES)
        form_layout.addRow("نوع پاسخ:", self.answer_type_combo)

        self.standard_edit = QTextEdit()
        self.standard_edit.setFixedHeight(50)
        form_layout.addRow("استاندارد مرجع:", self.standard_edit)

        self.recommendation_edit = QTextEdit()
        self.recommendation_edit.setFixedHeight(70)
        form_layout.addRow("توصیه اصلاحی:", self.recommendation_edit)

        self.evaluator_guide_edit = QTextEdit()
        self.evaluator_guide_edit.setFixedHeight(70)
        form_layout.addRow("راهنمای ارزیاب:", self.evaluator_guide_edit)

        form_outer.addLayout(form_layout)
        form_outer.addStretch(1)

        # --- دکمه‌ها --------------------------------------------------------
        button_row_1 = QHBoxLayout()
        self.new_button = QPushButton("سؤال جدید")
        self.new_button.clicked.connect(self._on_new_question)
        button_row_1.addWidget(self.new_button)

        self.delete_button = QPushButton("حذف سؤال")
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self._on_delete_question)
        button_row_1.addWidget(self.delete_button)
        form_outer.addLayout(button_row_1)

        self.save_button = QPushButton("ذخیره تغییرات در پایگاه داده")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self._on_save_question)
        form_outer.addWidget(self.save_button)

        root_layout.addWidget(form_card)

        self.statusBar().showMessage("آماده")

    # ------------------------------------------------------------- حوزه‌ها
    def _load_categories(self) -> None:
        self.categories = self.repository.list_categories()

        self.domain_list.blockSignals(True)
        self.domain_list.clear()
        self.category_combo.clear()

        for category in self.categories:
            self.domain_list.addItem(QListWidgetItem(category["category_name"]))
            self.category_combo.addItem(category["category_name"], category["id"])

        self.domain_list.blockSignals(False)

        if self.categories:
            self.domain_list.setCurrentRow(0)

    def _on_domain_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.categories):
            return
        category = self.categories[row]
        self.current_category_id = category["id"]
        self.header_label.setText(f"حوزه: {category['category_name']}")
        self.search_edit.clear()
        self._clear_form()
        self._refresh_table()

    # ------------------------------------------------------------- جدول
    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        if self.current_category_id is None:
            return

        keyword = self.search_edit.text()
        questions = self.repository.list_questions(self.current_category_id, keyword)

        self.table.setRowCount(len(questions))
        for row_index, question in enumerate(questions):
            code_item = QTableWidgetItem(question["question_code"])
            code_item.setData(Qt.UserRole, question["id"])
            self.table.setItem(row_index, 0, code_item)
            self.table.setItem(row_index, 1, QTableWidgetItem(question["question_text"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(str(question["weight"])))
            self.table.setItem(row_index, 3, QTableWidgetItem(question["answer_type"]))

        self.statusBar().showMessage(f"تعداد سؤالات نمایش داده‌شده: {len(questions)}")

    def _on_import_excel(self) -> None:
        """باز کردن دیالوگ انتخاب فایل اکسل و اجرای Import روی پایگاه داده."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل اکسل سؤالات", "", "فایل اکسل (*.xlsx)"
        )
        if not file_path:
            return

        importer = ExcelImporter(self.repository.db)
        try:
            importer.import_file(Path(file_path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "خطا در درون‌ریزی", f"درون‌ریزی فایل اکسل با خطا مواجه شد:\n{exc}"
            )
            return

        stats = importer.stats
        summary_lines = [
            f"نوع سازمان جدید ساخته‌شده:   {stats['facility_types_created']}",
            f"حوزه کلان جدید ساخته‌شده:    {stats['domains_created']}",
            f"زیرحوزه جدید ساخته‌شده:      {stats['categories_created']}",
            f"سؤال جدید افزوده‌شده:        {stats['questions_inserted']}",
            f"سؤال بروزرسانی‌شده:          {stats['questions_updated']}",
            f"ردیف رد‌شده (ناقص):          {stats['rows_skipped']}",
        ]
        if importer.skipped_rows:
            summary_lines.append("")
            summary_lines.append("ردیف‌های رد‌شده:")
            for row_number, reason in importer.skipped_rows:
                summary_lines.append(f"  ردیف {row_number}: {reason}")

        QMessageBox.information(self, "نتیجه درون‌ریزی از اکسل", "\n".join(summary_lines))

        # بازخوانی کامل حوزه‌ها، چون ممکن است زیرحوزه‌های تازه اضافه شده باشند
        self._load_categories()

    def _on_search_changed(self, _text: str) -> None:
        self._refresh_table()

    def _on_row_selected(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        code_item = self.table.item(row, 0)
        question_id = code_item.data(Qt.UserRole)

        question = self.repository.get_question(question_id)
        if question is None:
            return

        self.selected_question_id = question_id
        self._fill_form(question)

    # ------------------------------------------------------------- فرم
    def _clear_form(self) -> None:
        self.selected_question_id = None
        self.table.clearSelection()

        self.id_display.setText("")
        self.code_edit.setText("")
        self.title_edit.setPlainText("")
        self.weight_spin.setValue(1)
        self.answer_type_combo.setCurrentIndex(0)
        self.standard_edit.setPlainText("")
        self.recommendation_edit.setPlainText("")
        self.evaluator_guide_edit.setPlainText("")

        if self.current_category_id is not None:
            index = self.category_combo.findData(self.current_category_id)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)

    def _fill_form(self, question: dict[str, Any]) -> None:
        self.id_display.setText(str(question["id"]))
        self.code_edit.setText(question["question_code"])
        self.title_edit.setPlainText(question["question_text"])

        index = self.category_combo.findData(question["category_id"])
        if index >= 0:
            self.category_combo.setCurrentIndex(index)

        self.weight_spin.setValue(int(question["weight"]))

        type_index = self.answer_type_combo.findText(question["answer_type"])
        self.answer_type_combo.setCurrentIndex(type_index if type_index >= 0 else 0)

        self.standard_edit.setPlainText(question["standard_reference"] or "")
        self.recommendation_edit.setPlainText(question["recommendation"] or "")
        self.evaluator_guide_edit.setPlainText(question["evaluator_guide"] or "")

    def _read_form(self) -> dict[str, Any]:
        return {
            "code": self.code_edit.text().strip(),
            "title": self.title_edit.toPlainText().strip(),
            "category_id": self.category_combo.currentData(),
            "weight": self.weight_spin.value(),
            "answer_type": self.answer_type_combo.currentText(),
            "standard": self.standard_edit.toPlainText().strip(),
            "recommendation": self.recommendation_edit.toPlainText().strip(),
            "evaluator_guide": self.evaluator_guide_edit.toPlainText().strip(),
        }

    def _validate_form(self, data: dict[str, Any]) -> bool:
        if not data["code"]:
            QMessageBox.warning(self, "خطای اعتبارسنجی", "کد سؤال نمی‌تواند خالی باشد.")
            return False

        if not data["title"]:
            QMessageBox.warning(self, "خطای اعتبارسنجی", "متن سؤال نمی‌تواند خالی باشد.")
            return False

        if data["category_id"] is None:
            QMessageBox.warning(self, "خطای اعتبارسنجی", "دسته‌بندی انتخاب نشده است.")
            return False

        if self.repository.is_duplicate_code(data["code"], exclude_id=self.selected_question_id):
            QMessageBox.warning(
                self,
                "کد تکراری",
                f"کد سؤال «{data['code']}» قبلاً در بانک سؤالات ثبت شده است.\n"
                "لطفاً کد دیگری وارد کنید.",
            )
            return False

        return True

    # ------------------------------------------------------------- عملیات
    def _on_new_question(self) -> None:
        if self.current_category_id is None:
            QMessageBox.information(self, "توجه", "ابتدا یک حوزه را از فهرست کنار صفحه انتخاب کنید.")
            return
        self._clear_form()
        self.statusBar().showMessage("در حال افزودن سؤال جدید — پس از تکمیل فرم، دکمه ذخیره را بزنید.")

    def _on_save_question(self) -> None:
        data = self._read_form()
        if not self._validate_form(data):
            return

        if self.selected_question_id is not None:
            self.repository.update_question(self.selected_question_id, data)
            message = f"سؤال «{data['code']}» با موفقیت بروزرسانی شد."
        else:
            new_id = self.repository.insert_question(data)
            self.selected_question_id = new_id
            message = f"سؤال «{data['code']}» با موفقیت به پایگاه داده افزوده شد."

        self.statusBar().showMessage(message)
        self._refresh_table()
        self._reselect_current_question()

        QMessageBox.information(self, "ذخیره موفق", message)

    def _on_delete_question(self) -> None:
        if self.selected_question_id is None:
            QMessageBox.information(self, "حذف سؤال", "ابتدا یک سؤال را از جدول انتخاب کنید.")
            return

        code = self.code_edit.text()
        confirm = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف سؤال با کد «{code}» اطمینان دارید؟\nاین عملیات غیرقابل بازگشت است.",
        )
        if confirm != QMessageBox.Yes:
            return

        self.repository.delete_question(self.selected_question_id)
        message = f"سؤال «{code}» با موفقیت حذف شد."
        self.statusBar().showMessage(message)
        self._clear_form()
        self._refresh_table()

        QMessageBox.information(self, "حذف موفق", message)

    def _reselect_current_question(self) -> None:
        """بعد از ذخیره، همان ردیف را در جدول دوباره انتخاب می‌کند."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.data(Qt.UserRole) == self.selected_question_id:
                self.table.selectRow(row)
                break


# =============================================================================
# نقطه ورود مستقل (اجرای این فایل به‌تنهایی برای تست)
# =============================================================================

def main() -> None:
    database = get_database()
    repository = QuestionRepository(database)

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLE_SHEET)
    app.setFont(QFont("Tahoma", 10))

    window = QuestionDesignerWindow(repository)
    window.show()

    exit_code = app.exec()
    database.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

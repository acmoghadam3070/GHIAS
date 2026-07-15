#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
موتور گزارش‌ساز (Report Engine)
=============================================================================

این فایل مسئول تولید یک فایل Word رسمی و ساده از نتایج یک ارزیابی تکمیل‌شده
است. خروجی شامل:
    - اطلاعات کلی بازدید (واحد، نوع سازمان، حوزه، ارزیاب، تاریخ)
    - امتیاز کلی و وضعیت ریسک کلی
    - جدول امتیاز هر زیرحوزه
    - جدول اقدامات اصلاحی پیشنهادی، مرتب‌شده بر اساس اولویت

طبق تصمیم اولیه پروژه، این خروجی عمداً ساده و رسمی است و شامل نمودار
نمی‌شود؛ نمودارها فقط در داشبورد داخل نرم‌افزار نمایش داده می‌شوند.

این فایل مستقل از رابط گرافیکی است و فقط به کتابخانه python-docx نیاز دارد.
=============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# رنگ متناظر با هر سطح ریسک، برای هماهنگی با بقیه بخش‌های نرم‌افزار
RISK_COLORS: dict[str, RGBColor] = {
    "بحرانی": RGBColor(0xEB, 0x57, 0x57),
    "هشدار": RGBColor(0xF2, 0x99, 0x14),
    "قابل قبول": RGBColor(0x27, 0xAE, 0x60),
    "بدون داده": RGBColor(0x9A, 0xA5, 0xB1),
}

PRIORITY_COLORS: dict[str, RGBColor] = {
    "بالا": RGBColor(0xEB, 0x57, 0x57),
    "متوسط": RGBColor(0xF2, 0x99, 0x14),
    "پایین": RGBColor(0x27, 0xAE, 0x60),
}


def _set_rtl(paragraph) -> None:
    """فعال‌سازی جهت راست‌به‌چپ برای یک پاراگراف (سازگار با ورد فارسی)."""
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.makeelement(qn("w:bidi"), {})
    p_pr.append(bidi)


def _set_cell_rtl(cell) -> None:
    for paragraph in cell.paragraphs:
        _set_rtl(paragraph)


class ReportEngine:
    """موتور تولید فایل گزارش Word از داده‌های یک ارزیابی."""

    def generate_visit_report(
        self,
        visit: dict[str, Any],
        category_breakdown: list[Any],
        recommendations: list[dict[str, Any]],
        output_path: Path,
    ) -> Path:
        """
        ساخت فایل گزارش Word و ذخیره آن در مسیر output_path.

        visit: دیکشنری اطلاعات بازدید (خروجی get_visit از repository)
        category_breakdown: لیست CategoryResult از موتور امتیازدهی
        recommendations: لیست اقدامات اصلاحی (خروجی get_recommendations)
        """
        document = Document()

        # تنظیم جهت پیش‌فرض سند به راست‌به‌چپ
        section = document.sections[0]
        section.page_height = Cm(29.7)
        section.page_width = Cm(21.0)

        self._add_title_block(document, visit)
        self._add_summary_block(document, visit)
        self._add_category_table(document, category_breakdown)
        self._add_recommendations_table(document, recommendations)
        self._add_footer_note(document)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(output_path))
        return output_path

    # ------------------------------------------------------------- بخش‌های سند
    def _add_title_block(self, document: Document, visit: dict[str, Any]) -> None:
        title = document.add_heading("گزارش ارزیابی حفاظت فیزیکی", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_rtl(title)

        subtitle = document.add_paragraph("سامانه قیاس (GHIAS)")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_rtl(subtitle)
        subtitle.runs[0].font.size = Pt(13)
        subtitle.runs[0].font.color.rgb = RGBColor(0x1C, 0x2B, 0x3A)

        document.add_paragraph()

        info_rows = [
            ("واحد تحت ارزیابی:", visit.get("facility_name", "")),
            ("حوزه ارزیابی:", visit.get("domain_name", "")),
            ("ارزیاب:", visit.get("inspector_name", "")),
            ("تاریخ بازدید:", str(visit.get("visit_date", ""))),
            ("تاریخ ثبت نهایی:", str(visit.get("finished_at", "") or "—")),
        ]
        table = document.add_table(rows=0, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for label, value in info_rows:
            row = table.add_row()
            row.cells[0].text = label
            row.cells[1].text = str(value)
            for cell in row.cells:
                _set_cell_rtl(cell)
                cell.paragraphs[0].runs[0].font.size = Pt(11)
            row.cells[0].paragraphs[0].runs[0].font.bold = True

        document.add_paragraph()

    def _add_summary_block(self, document: Document, visit: dict[str, Any]) -> None:
        heading = document.add_heading("خلاصه نتیجه ارزیابی", level=1)
        _set_rtl(heading)

        score = visit.get("overall_score")
        risk_label = visit.get("overall_risk_level", "بدون داده")

        paragraph = document.add_paragraph()
        _set_rtl(paragraph)
        run_label = paragraph.add_run("امتیاز کلی: ")
        run_label.font.bold = True
        run_label.font.size = Pt(13)
        run_value = paragraph.add_run(f"{score if score is not None else '—'}")
        run_value.font.size = Pt(13)

        paragraph2 = document.add_paragraph()
        _set_rtl(paragraph2)
        run_label2 = paragraph2.add_run("وضعیت کلی: ")
        run_label2.font.bold = True
        run_label2.font.size = Pt(13)
        run_value2 = paragraph2.add_run(risk_label)
        run_value2.font.size = Pt(13)
        run_value2.font.bold = True
        run_value2.font.color.rgb = RISK_COLORS.get(risk_label, RGBColor(0, 0, 0))

        document.add_paragraph()

    def _add_category_table(self, document: Document, category_breakdown: list[Any]) -> None:
        heading = document.add_heading("امتیاز به تفکیک زیرحوزه", level=1)
        _set_rtl(heading)

        table = document.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        header_cells = table.rows[0].cells
        headers = ["زیرحوزه", "امتیاز", "وضعیت", "پاسخ‌داده‌شده"]
        for cell, text in zip(header_cells, headers):
            cell.text = text
            _set_cell_rtl(cell)
            cell.paragraphs[0].runs[0].font.bold = True

        for result in category_breakdown:
            row = table.add_row()
            row.cells[0].text = result.category_name
            row.cells[1].text = str(result.score)
            row.cells[2].text = result.risk_label
            row.cells[3].text = f"{result.answered_count}/{result.total_questions}"
            for cell in row.cells:
                _set_cell_rtl(cell)
            status_run = row.cells[2].paragraphs[0].runs[0]
            status_run.font.color.rgb = RISK_COLORS.get(result.risk_label, RGBColor(0, 0, 0))
            status_run.font.bold = True

        document.add_paragraph()

    def _add_recommendations_table(
        self, document: Document, recommendations: list[dict[str, Any]]
    ) -> None:
        heading = document.add_heading("اقدامات اصلاحی پیشنهادی", level=1)
        _set_rtl(heading)

        if not recommendations:
            paragraph = document.add_paragraph("هیچ اقدام اصلاحی برای این ارزیابی ثبت نشده است.")
            _set_rtl(paragraph)
            return

        table = document.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        header_cells = table.rows[0].cells
        headers = ["اولویت", "کد سؤال", "زیرحوزه", "اقدام پیشنهادی"]
        for cell, text in zip(header_cells, headers):
            cell.text = text
            _set_cell_rtl(cell)
            cell.paragraphs[0].runs[0].font.bold = True

        for rec in recommendations:
            row = table.add_row()
            row.cells[0].text = rec.get("priority", "")
            row.cells[1].text = rec.get("question_code", "")
            row.cells[2].text = rec.get("category_name", "")
            row.cells[3].text = rec.get("recommendation_text", "")
            for cell in row.cells:
                _set_cell_rtl(cell)
            priority_run = row.cells[0].paragraphs[0].runs[0]
            priority_run.font.color.rgb = PRIORITY_COLORS.get(rec.get("priority", ""), RGBColor(0, 0, 0))
            priority_run.font.bold = True

        document.add_paragraph()

    def _add_footer_note(self, document: Document) -> None:
        paragraph = document.add_paragraph(
            "این گزارش به‌صورت خودکار توسط سامانه قیاس (GHIAS) تولید شده است."
        )
        _set_rtl(paragraph)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.runs[0].font.size = Pt(9)
        paragraph.runs[0].font.color.rgb = RGBColor(0x9A, 0xA5, 0xB1)

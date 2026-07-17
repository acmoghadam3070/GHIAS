#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
موتور گزارش‌ساز (Report Engine) - نسخه دوم
=============================================================================

این فایل مسئول تولید یک فایل Word رسمی از نتایج یک ارزیابی تکمیل‌شده است.

امکانات این نسخه:
    - فونت تیترها: B Titr / فونت بدنه: B Nazanin
    - تاریخ و ساعت شمسی (بدون نیاز به کتابخانه جانبی)
    - نام کاربری که گزارش را تولید کرده
    - هدر با جای لوگو و شماره صفحه
    - فوتر با عبارت تخصیص گزارش (برای کدام واحد تهیه شده)
    - کد پیگیری یکتای گزارش
    - بخش امضا برای ارزیاب و تأیید مدیر حفاظت فیزیکی
    - یک پاراگراف سلب مسئولیت رسمی

طبق تصمیم اولیه پروژه، این خروجی عمداً ساده و رسمی است و شامل نمودار
نمی‌شود؛ نمودارها فقط در داشبورد داخل نرم‌افزار نمایش داده می‌شوند.
=============================================================================
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HEADING_FONT = "B Titr"
BODY_FONT = "B Nazanin"

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
LOGO_PATH: Path = PROJECT_ROOT / "assets" / "images" / "logo.png"

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


# =============================================================================
# تبدیل تاریخ میلادی به شمسی (بدون وابستگی به کتابخانه جانبی)
# =============================================================================

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """تبدیل یک تاریخ میلادی به تاریخ شمسی. الگوریتم استاندارد و متن‌باز."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        + gd
        + g_d_m[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + (days % 31)
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def format_jalali_date(dt: datetime) -> str:
    """قالب‌بندی تاریخ شمسی به‌صورت «۲۴ تیر ۱۴۰۵» با اعداد فارسی."""
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    text = f"{jd} {JALALI_MONTHS[jm - 1]} {jy}"
    return text.translate(PERSIAN_DIGITS)


def format_jalali_datetime(dt: datetime) -> str:
    """قالب‌بندی کامل تاریخ و ساعت شمسی."""
    date_part = format_jalali_date(dt)
    time_part = dt.strftime("%H:%M").translate(PERSIAN_DIGITS)
    return f"{date_part} - ساعت {time_part}"


def parse_visit_date(raw_value: Any) -> datetime:
    """تبدیل مقدار تاریخ ذخیره‌شده در پایگاه داده (رشته yyyy-mm-dd) به datetime."""
    try:
        return datetime.strptime(str(raw_value)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.now()


# =============================================================================
# کمکی‌های سطح پایین Word (فونت، جهت راست‌به‌چپ، شماره صفحه)
# =============================================================================

def _set_rtl(paragraph) -> None:
    """فعال‌سازی جهت راست‌به‌چپ برای یک پاراگراف."""
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.makeelement(qn("w:bidi"), {})
    p_pr.append(bidi)


def _set_cell_rtl(cell) -> None:
    for paragraph in cell.paragraphs:
        _set_rtl(paragraph)


def _set_run_font(run, font_name: str, size: Optional[int] = None,
                   bold: Optional[bool] = None, color: Optional[RGBColor] = None) -> None:
    """
    تنظیم کامل فونت یک Run، هم برای حروف لاتین و هم برای حروف فارسی/عربی
    (Complex Script)، چون ورد این دو را جدا از هم نگه می‌دارد.
    """
    run.font.name = font_name
    r_pr = run._r.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:ascii"), font_name)
    r_fonts.set(qn("w:hAnsi"), font_name)
    r_fonts.set(qn("w:cs"), font_name)

    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _add_page_number_field(paragraph) -> None:
    """افزودن فیلد خودکار شماره صفحه به یک پاراگراف (هدر یا فوتر)."""
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_end)
    _set_run_font(run, BODY_FONT, size=10)


class ReportEngine:
    """موتور تولید فایل گزارش Word از داده‌های یک ارزیابی."""

    def generate_visit_report(
        self,
        visit: dict[str, Any],
        category_breakdown: list[Any],
        recommendations: list[dict[str, Any]],
        output_path: Path,
        generated_by: str = "کاربر ناشناس",
    ) -> Path:
        document = Document()

        self._set_base_styles(document)

        section = document.sections[0]
        section.page_height = Cm(29.7)
        section.page_width = Cm(21.0)
        section.header_distance = Cm(1.0)
        section.footer_distance = Cm(1.0)

        report_code = f"GHIAS-{visit.get('id', '0')}-{datetime.now().strftime('%Y%m%d%H%M')}"

        self._build_header(section, visit)
        self._build_footer(section, visit)

        self._add_title_block(document, visit, report_code, generated_by)
        self._add_summary_block(document, visit)
        self._add_category_table(document, category_breakdown)
        self._add_recommendations_table(document, recommendations)
        self._add_disclaimer(document)
        self._add_signature_block(document)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(output_path))
        return output_path

    # ------------------------------------------------------------- استایل پایه سند
    def _set_base_styles(self, document: Document) -> None:
        normal_style = document.styles["Normal"]
        normal_style.font.name = BODY_FONT
        r_pr = normal_style.element.get_or_add_rPr()
        r_fonts = r_pr.find(qn("w:rFonts"))
        if r_fonts is None:
            r_fonts = OxmlElement("w:rFonts")
            r_pr.append(r_fonts)
        r_fonts.set(qn("w:ascii"), BODY_FONT)
        r_fonts.set(qn("w:hAnsi"), BODY_FONT)
        r_fonts.set(qn("w:cs"), BODY_FONT)
        normal_style.font.size = Pt(11)

        for heading_name in ["Heading 1", "Heading 2", "Title"]:
            try:
                heading_style = document.styles[heading_name]
            except KeyError:
                continue
            heading_style.font.name = HEADING_FONT
            h_r_pr = heading_style.element.get_or_add_rPr()
            h_r_fonts = h_r_pr.find(qn("w:rFonts"))
            if h_r_fonts is None:
                h_r_fonts = OxmlElement("w:rFonts")
                h_r_pr.append(h_r_fonts)
            h_r_fonts.set(qn("w:ascii"), HEADING_FONT)
            h_r_fonts.set(qn("w:hAnsi"), HEADING_FONT)
            h_r_fonts.set(qn("w:cs"), HEADING_FONT)
            heading_style.font.color.rgb = RGBColor(0x1C, 0x2B, 0x3A)

    # ------------------------------------------------------------- هدر
    def _build_header(self, section, visit: dict[str, Any]) -> None:
        header = section.header
        paragraph = header.paragraphs[0]
        _set_rtl(paragraph)

        tab_stops = paragraph.paragraph_format.tab_stops
        tab_stops.add_tab_stop(Cm(0))

        if LOGO_PATH.exists():
            run_logo = paragraph.add_run()
            run_logo.add_picture(str(LOGO_PATH), width=Cm(2.0))
        else:
            run_logo = paragraph.add_run("[ محل درج لوگوی سامانه قیاس ]")
            _set_run_font(run_logo, BODY_FONT, size=9, color=RGBColor(0x9A, 0xA5, 0xB1))

        paragraph.add_run("\t")
        title_run = paragraph.add_run("سامانه قیاس (GHIAS)")
        _set_run_font(title_run, HEADING_FONT, size=12, bold=True, color=RGBColor(0x1C, 0x2B, 0x3A))

        page_paragraph = header.add_paragraph()
        _set_rtl(page_paragraph)
        page_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        label_run = page_paragraph.add_run("شماره صفحه: ")
        _set_run_font(label_run, BODY_FONT, size=9, color=RGBColor(0x66, 0x6E, 0x77))
        _add_page_number_field(page_paragraph)

        # خط جداکننده زیر هدر
        border_paragraph = header.add_paragraph()
        p_pr = border_paragraph._p.get_or_add_pPr()
        p_bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "1C2B3A")
        p_bdr.append(bottom)
        p_pr.append(p_bdr)

    # ------------------------------------------------------------- فوتر
    def _build_footer(self, section, visit: dict[str, Any]) -> None:
        footer = section.footer
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_rtl(paragraph)

        facility_name = visit.get("facility_name", "نامشخص")
        run = paragraph.add_run(
            f"این گزارش اختصاصاً برای «{facility_name}» تهیه شده و صرفاً جهت استفاده "
            "مدیریت حفاظت فیزیکی و امنیت همان واحد معتبر است."
        )
        _set_run_font(run, BODY_FONT, size=9, color=RGBColor(0x66, 0x6E, 0x77))

    # ------------------------------------------------------------- عنوان و اطلاعات کلی
    def _add_title_block(
        self, document: Document, visit: dict[str, Any], report_code: str, generated_by: str
    ) -> None:
        title = document.add_heading("گزارش ارزیابی حفاظت فیزیکی", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_rtl(title)
        for run in title.runs:
            _set_run_font(run, HEADING_FONT, size=22, bold=True, color=RGBColor(0x1C, 0x2B, 0x3A))

        document.add_paragraph()

        now = datetime.now()
        info_rows = [
            ("واحد تحت ارزیابی:", visit.get("facility_name", "")),
            ("حوزه ارزیابی:", visit.get("domain_name", "")),
            ("ارزیاب مسئول:", visit.get("inspector_name", "")),
            ("تاریخ بازدید:", format_jalali_date(parse_visit_date(visit.get("visit_date")))),
            ("کد پیگیری گزارش:", report_code),
            ("تهیه‌شده توسط:", generated_by),
            ("تاریخ و ساعت تولید گزارش:", format_jalali_datetime(now)),
        ]
        table = document.add_table(rows=0, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for label, value in info_rows:
            row = table.add_row()
            row.cells[0].text = ""
            row.cells[1].text = ""
            _set_run_font(row.cells[0].paragraphs[0].add_run(label), BODY_FONT, size=11, bold=True)
            _set_run_font(row.cells[1].paragraphs[0].add_run(str(value)), BODY_FONT, size=11)
            _set_cell_rtl(row.cells[0])
            _set_cell_rtl(row.cells[1])

        document.add_paragraph()

    # ------------------------------------------------------------- خلاصه نتیجه
    def _add_summary_block(self, document: Document, visit: dict[str, Any]) -> None:
        heading = document.add_heading("خلاصه نتیجه ارزیابی", level=1)
        _set_rtl(heading)
        for run in heading.runs:
            _set_run_font(run, HEADING_FONT, size=15, bold=True, color=RGBColor(0x1C, 0x2B, 0x3A))

        score = visit.get("overall_score")
        risk_label = visit.get("overall_risk_level", "بدون داده")

        paragraph = document.add_paragraph()
        _set_rtl(paragraph)
        run_label = paragraph.add_run("امتیاز کلی: ")
        _set_run_font(run_label, BODY_FONT, size=13, bold=True)
        run_value = paragraph.add_run(f"{score if score is not None else '—'}")
        _set_run_font(run_value, BODY_FONT, size=13)

        paragraph2 = document.add_paragraph()
        _set_rtl(paragraph2)
        run_label2 = paragraph2.add_run("وضعیت کلی: ")
        _set_run_font(run_label2, BODY_FONT, size=13, bold=True)
        run_value2 = paragraph2.add_run(risk_label)
        _set_run_font(run_value2, BODY_FONT, size=13, bold=True,
                      color=RISK_COLORS.get(risk_label, RGBColor(0, 0, 0)))

        document.add_paragraph()

    # ------------------------------------------------------------- جدول زیرحوزه‌ها
    def _add_category_table(self, document: Document, category_breakdown: list[Any]) -> None:
        heading = document.add_heading("امتیاز به تفکیک زیرحوزه", level=1)
        _set_rtl(heading)
        for run in heading.runs:
            _set_run_font(run, HEADING_FONT, size=15, bold=True, color=RGBColor(0x1C, 0x2B, 0x3A))

        table = document.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = ["زیرحوزه", "امتیاز", "وضعیت", "پاسخ‌داده‌شده"]
        for cell, text in zip(table.rows[0].cells, headers):
            _set_run_font(cell.paragraphs[0].add_run(text), BODY_FONT, size=11, bold=True)
            _set_cell_rtl(cell)

        for result in category_breakdown:
            row = table.add_row()
            values = [
                result.category_name, str(result.score), result.risk_label,
                f"{result.answered_count}/{result.total_questions}",
            ]
            for cell, value in zip(row.cells, values):
                _set_run_font(cell.paragraphs[0].add_run(value), BODY_FONT, size=10)
                _set_cell_rtl(cell)
            status_run = row.cells[2].paragraphs[0].runs[0]
            status_run.font.color.rgb = RISK_COLORS.get(result.risk_label, RGBColor(0, 0, 0))
            status_run.font.bold = True

        document.add_paragraph()

    # ------------------------------------------------------------- جدول اقدامات اصلاحی
    def _add_recommendations_table(
        self, document: Document, recommendations: list[dict[str, Any]]
    ) -> None:
        heading = document.add_heading("اقدامات اصلاحی پیشنهادی", level=1)
        _set_rtl(heading)
        for run in heading.runs:
            _set_run_font(run, HEADING_FONT, size=15, bold=True, color=RGBColor(0x1C, 0x2B, 0x3A))

        if not recommendations:
            paragraph = document.add_paragraph()
            _set_rtl(paragraph)
            _set_run_font(
                paragraph.add_run("هیچ اقدام اصلاحی برای این ارزیابی ثبت نشده است."),
                BODY_FONT, size=11,
            )
            return

        table = document.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = ["اولویت", "کد سؤال", "زیرحوزه", "اقدام پیشنهادی"]
        for cell, text in zip(table.rows[0].cells, headers):
            _set_run_font(cell.paragraphs[0].add_run(text), BODY_FONT, size=11, bold=True)
            _set_cell_rtl(cell)

        for rec in recommendations:
            row = table.add_row()
            values = [
                rec.get("priority", ""), rec.get("question_code", ""),
                rec.get("category_name", ""), rec.get("recommendation_text", ""),
            ]
            for cell, value in zip(row.cells, values):
                _set_run_font(cell.paragraphs[0].add_run(value), BODY_FONT, size=10)
                _set_cell_rtl(cell)
            priority_run = row.cells[0].paragraphs[0].runs[0]
            priority_run.font.color.rgb = PRIORITY_COLORS.get(rec.get("priority", ""), RGBColor(0, 0, 0))
            priority_run.font.bold = True

        document.add_paragraph()

    # ------------------------------------------------------------- سلب مسئولیت
    def _add_disclaimer(self, document: Document) -> None:
        paragraph = document.add_paragraph()
        _set_rtl(paragraph)
        run = paragraph.add_run(
            "این گزارش صرفاً بر اساس پاسخ‌های ثبت‌شده توسط ارزیاب در زمان بازدید تهیه "
            "شده و باید پیش از اجرای هرگونه تصمیم مدیریتی، توسط مدیر حفاظت فیزیکی واحد "
            "بررسی و تأیید شود."
        )
        _set_run_font(run, BODY_FONT, size=9, color=RGBColor(0x66, 0x6E, 0x77))
        document.add_paragraph()

    # ------------------------------------------------------------- بخش امضا
    def _add_signature_block(self, document: Document) -> None:
        table = document.add_table(rows=2, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        labels = ["امضای ارزیاب", "تأیید مدیر حفاظت فیزیکی"]
        for cell, label in zip(table.rows[0].cells, labels):
            run = cell.paragraphs[0].add_run(label)
            _set_run_font(run, BODY_FONT, size=11, bold=True)
            _set_cell_rtl(cell)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for cell in table.rows[1].cells:
            run = cell.paragraphs[0].add_run("......................................")
            _set_run_font(run, BODY_FONT, size=11)
            _set_cell_rtl(cell)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

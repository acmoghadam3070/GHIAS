#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
موتور گزارش‌ساز (Report Engine) - نسخه سوم
=============================================================================

نسخه‌ای که ظاهر آن مطابق طرح گرافیکی رسمی سامانه قیاس ساخته شده است:
    - واترمارک لوگو در پس‌زمینه تمام صفحات
    - سربرگ با شماره/تاریخ/نسخه/سطح محرمانگی گزارش + لوگو
    - عنوان دوزبانه
    - خلاصه مدیریتی روایی
    - ردیف کارت‌های KPI همراه با گیج دایره‌ای سطح آمادگی کلی
    - جدول نتایج تفصیلی با نشان‌های رنگی وضعیت
    - جدول اقدامات اصلاحی با اولویت رنگی و زمان‌بندی پیشنهادی
    - بخش امضا
    - فوتر تیره با لوگو، شماره صفحه، و نشان سطح محرمانگی

محدودیت صادقانه: بعضی جلوه‌های گرافیکی پیچیده (سایه سه‌بعدی روی خود
لوگو) در Word قابل بازتولید پیکسل‌به‌پیکسل نیست؛ معادل حرفه‌ای آن با
جدول‌بندی، رنگ، و تصویر گیج واقعی ساخته شده است.
=============================================================================
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
WATERMARK_PATH: Path = PROJECT_ROOT / "assets" / "images" / "watermark.png"

NAVY = RGBColor(0x1C, 0x2B, 0x3A)
GOLD = RGBColor(0xC9, 0xA0, 0x4A)
GRAY_TEXT = RGBColor(0x66, 0x6E, 0x77)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

RISK_COLORS: dict[str, RGBColor] = {
    "بحرانی": RGBColor(0xEB, 0x57, 0x57),
    "هشدار": RGBColor(0xF2, 0x99, 0x14),
    "قابل قبول": RGBColor(0x27, 0xAE, 0x60),
    "بدون داده": RGBColor(0x9A, 0xA5, 0xB1),
}
RISK_HEX: dict[str, str] = {
    "بحرانی": "EB5757",
    "هشدار": "F2994A",
    "قابل قبول": "27AE60",
    "بدون داده": "9AA5B1",
}

PRIORITY_COLORS: dict[str, RGBColor] = {
    "بالا": RGBColor(0xEB, 0x57, 0x57),
    "متوسط": RGBColor(0xF2, 0x99, 0x14),
    "پایین": RGBColor(0x27, 0xAE, 0x60),
}
PRIORITY_HEX: dict[str, str] = {"بالا": "EB5757", "متوسط": "F2994A", "پایین": "27AE60"}
PRIORITY_TIMELINE: dict[str, str] = {"بالا": "۱ ماه", "متوسط": "۳ ماه", "پایین": "۶ ماه"}


# =============================================================================
# تبدیل تاریخ میلادی به شمسی
# =============================================================================

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]
PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
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


def format_jalali_date_numeric(dt: datetime) -> str:
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jy}/{jm:02d}/{jd:02d}".translate(PERSIAN_DIGITS)


def format_jalali_date(dt: datetime) -> str:
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jd} {JALALI_MONTHS[jm - 1]} {jy}".translate(PERSIAN_DIGITS)


def format_jalali_datetime(dt: datetime) -> str:
    return f"{format_jalali_date(dt)} - ساعت {dt.strftime('%H:%M').translate(PERSIAN_DIGITS)}"


def parse_visit_date(raw_value: Any) -> datetime:
    try:
        return datetime.strptime(str(raw_value)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.now()


def to_persian_digits(value: Any) -> str:
    return str(value).translate(PERSIAN_DIGITS)


# =============================================================================
# کمکی‌های سطح پایین Word
# =============================================================================

PPR_CHILD_ORDER = [
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl",
    "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens",
    "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
    "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
    "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
    "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange",
]


def _insert_in_schema_order(parent, new_element, tag_name: str, order_list: list[str]) -> None:
    """
    افزودن یک عنصر فرزند به parent، دقیقاً در جایگاه درستی که استاندارد
    OOXML مشخص کرده است. اگر ترتیب رعایت نشود، ورد فایل را «خراب» تشخیص
    می‌دهد. این تابع محل درست را بر اساس فهرست ترتیب استاندارد پیدا می‌کند.
    """
    target_index = order_list.index(tag_name)
    for child in parent:
        child_tag = child.tag.split("}")[-1]
        if child_tag in order_list and order_list.index(child_tag) > target_index:
            child.addprevious(new_element)
            return
    parent.append(new_element)


def _set_rtl(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.makeelement(qn("w:bidi"), {})
    _insert_in_schema_order(p_pr, bidi, "bidi", PPR_CHILD_ORDER)


def _set_cell_rtl(cell) -> None:
    for paragraph in cell.paragraphs:
        _set_rtl(paragraph)


def _set_run_font(run, font_name: str, size: Optional[int] = None,
                   bold: Optional[bool] = None, color: Optional[RGBColor] = None) -> None:
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


TCPR_CHILD_ORDER = [
    "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
    "textDirection", "tcFitText", "vAlign", "hideMark", "headers", "cellIns",
    "cellDel", "cellMerge", "tcPrChange",
]


def _set_cell_shading(cell, hex_color: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr = cell._tc.get_or_add_tcPr()
    _insert_in_schema_order(tc_pr, shd, "shd", TCPR_CHILD_ORDER)


def _set_cell_vertical_center(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    v_align = OxmlElement("w:vAlign")
    v_align.set(qn("w:val"), "center")
    _insert_in_schema_order(tc_pr, v_align, "vAlign", TCPR_CHILD_ORDER)


TBLPR_CHILD_ORDER = [
    "tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
    "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
    "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription", "tblPrChange",
]


def _remove_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        el.set(qn("w:space"), "0")
        borders.append(el)
    _insert_in_schema_order(tbl_pr, borders, "tblBorders", TBLPR_CHILD_ORDER)


def _add_page_number_fields(paragraph, total: bool = False) -> None:
    run = paragraph.add_run()

    def _field(instr: str):
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr_el = OxmlElement("w:instrText")
        instr_el.set(qn("xml:space"), "preserve")
        instr_el.text = instr
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(begin)
        run._r.append(instr_el)
        run._r.append(end)

    _field("PAGE")
    if total:
        sep_run = paragraph.add_run(" از ")
        _set_run_font(sep_run, BODY_FONT, size=9, color=WHITE)
        run2 = paragraph.add_run()
        begin2 = OxmlElement("w:fldChar")
        begin2.set(qn("w:fldCharType"), "begin")
        instr2 = OxmlElement("w:instrText")
        instr2.set(qn("xml:space"), "preserve")
        instr2.text = "NUMPAGES"
        end2 = OxmlElement("w:fldChar")
        end2.set(qn("w:fldCharType"), "end")
        run2._r.append(begin2)
        run2._r.append(instr2)
        run2._r.append(end2)
        _set_run_font(run2, BODY_FONT, size=9, color=WHITE)
    _set_run_font(run, BODY_FONT, size=9, color=WHITE)


def _make_gauge_image(percent: float, color_hex: str) -> str:
    """ساخت یک تصویر گیج دایره‌ای موقت و بازگرداندن مسیر فایل آن."""
    percent = max(0, min(100, percent))
    fig, ax = plt.subplots(figsize=(1.3, 1.3), dpi=200)
    ax.pie(
        [percent, 100 - percent],
        colors=[f"#{color_hex}", "#eef1f4"],
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.28, edgecolor="white", linewidth=1),
    )
    ax.text(0, 0, f"{percent:.0f}%", ha="center", va="center",
            fontsize=19, fontweight="bold", color="#1c2b3a")
    ax.set_aspect("equal")
    plt.axis("off")
    tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    plt.savefig(tmp_file.name, transparent=True, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return tmp_file.name


class ReportEngine:
    """موتور تولید فایل گزارش Word رسمی از داده‌های یک ارزیابی."""

    def generate_visit_report(
        self,
        visit: dict[str, Any],
        category_breakdown: list[Any],
        recommendations: list[dict[str, Any]],
        output_path: Path,
        generated_by: str = "کاربر ناشناس",
        confidentiality: str = "خیلی محرمانه",
        deficient_count: Optional[int] = None,
    ) -> Path:
        document = Document()
        self._set_base_styles(document)

        section = document.sections[0]
        section.page_height = Cm(29.7)
        section.page_width = Cm(21.0)
        section.left_margin = Cm(1.8)
        section.right_margin = Cm(1.8)
        section.header_distance = Cm(0.8)
        section.footer_distance = Cm(0.8)

        report_code = f"GHIAS-{visit.get('id', '0')}-{datetime.now().strftime('%Y%m%d%H%M')}"

        self._build_watermark(section)
        self._build_footer(section, visit, confidentiality)

        self._build_cover_block(document, visit, report_code, confidentiality)
        self._build_executive_summary(document, visit, category_breakdown, recommendations, deficient_count)
        self._build_category_table(document, category_breakdown)
        self._build_recommendations_table(document, recommendations)
        self._build_signature_block(document, visit, generated_by)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(output_path))
        return output_path

    # ------------------------------------------------------------- استایل پایه
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

    # ------------------------------------------------------------- واترمارک
    def _build_watermark(self, section) -> None:
        if not WATERMARK_PATH.exists():
            return

        header = section.header
        paragraph = header.paragraphs[0]
        run = paragraph.add_run()
        picture = run.add_picture(str(WATERMARK_PATH), width=Cm(11))
        inline = picture._inline

        extent = inline.extent
        graphic = inline.graphic

        anchor = OxmlElement("wp:anchor")
        for attr, value in {
            "distT": "0", "distB": "0", "distL": "0", "distR": "0",
            "simplePos": "0", "relativeHeight": "1", "behindDoc": "1",
            "locked": "0", "layoutInCell": "1", "allowOverlap": "1",
        }.items():
            anchor.set(attr, value)

        simple_pos = OxmlElement("wp:simplePos")
        simple_pos.set("x", "0")
        simple_pos.set("y", "0")

        pos_h = OxmlElement("wp:positionH")
        pos_h.set("relativeFrom", "page")
        align_h = OxmlElement("wp:align")
        align_h.text = "center"
        pos_h.append(align_h)

        pos_v = OxmlElement("wp:positionV")
        pos_v.set("relativeFrom", "page")
        align_v = OxmlElement("wp:align")
        align_v.text = "center"
        pos_v.append(align_v)

        wrap_none = OxmlElement("wp:wrapNone")
        doc_pr = OxmlElement("wp:docPr")
        doc_pr.set("id", "1")
        doc_pr.set("name", "GHIAS-Watermark")
        c_nv_graphic_pr = OxmlElement("wp:cNvGraphicFramePr")

        anchor.append(simple_pos)
        anchor.append(pos_h)
        anchor.append(pos_v)
        anchor.append(extent)
        anchor.append(wrap_none)
        anchor.append(doc_pr)
        anchor.append(c_nv_graphic_pr)
        anchor.append(graphic)

        drawing = inline.getparent()
        drawing.remove(inline)
        drawing.append(anchor)

    # ------------------------------------------------------------- فوتر
    def _build_footer(self, section, visit: dict[str, Any], confidentiality: str) -> None:
        footer = section.footer
        footer.paragraphs[0].text = ""

        table = footer.add_table(rows=1, cols=3, width=Cm(17.4))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _remove_table_borders(table)

        for cell in table.rows[0].cells:
            _set_cell_shading(cell, "1C2B3A")
            _set_cell_vertical_center(cell)

        left_cell, center_cell, right_cell = table.rows[0].cells

        left_paragraph = left_cell.paragraphs[0]
        _set_rtl(left_paragraph)
        left_run = left_paragraph.add_run("قیاس (GHIAS) — Governance & Holistic Intelligent Assessment System")
        _set_run_font(left_run, BODY_FONT, size=8, color=WHITE)

        center_paragraph = center_cell.paragraphs[0]
        center_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_rtl(center_paragraph)
        label_run = center_paragraph.add_run("صفحه ")
        _set_run_font(label_run, BODY_FONT, size=9, color=WHITE)
        _add_page_number_fields(center_paragraph, total=True)

        right_paragraph = right_cell.paragraphs[0]
        right_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _set_rtl(right_paragraph)
        right_run = right_paragraph.add_run(f" {confidentiality} ")
        _set_run_font(right_run, BODY_FONT, size=8, bold=True, color=RGBColor(0xF2, 0xC9, 0x4C))

    # ------------------------------------------------------------- بلوک روی جلد
    def _build_cover_block(self, document: Document, visit: dict[str, Any],
                            report_code: str, confidentiality: str) -> None:
        info_table = document.add_table(rows=1, cols=2)
        info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        left_cell, right_cell = info_table.rows[0].cells

        meta_rows = [
            ("شماره گزارش:", report_code),
            ("تاریخ گزارش:", format_jalali_date_numeric(datetime.now())),
            ("نسخه گزارش:", "۱.۰"),
            ("سطح محرمانگی:", confidentiality),
        ]
        left_cell.paragraphs[0].text = ""
        for label, value in meta_rows:
            p = left_cell.add_paragraph()
            _set_rtl(p)
            _set_run_font(p.add_run(f"{label} "), BODY_FONT, size=9, bold=True, color=NAVY)
            _set_run_font(p.add_run(value), BODY_FONT, size=9, color=GRAY_TEXT)

        right_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        if LOGO_PATH.exists():
            run_logo = right_cell.paragraphs[0].add_run()
            run_logo.add_picture(str(LOGO_PATH), width=Cm(4.2))
        else:
            placeholder = right_cell.paragraphs[0].add_run("[ لوگوی قیاس ]")
            _set_run_font(placeholder, BODY_FONT, size=9, color=GRAY_TEXT)

        document.add_paragraph()

        rule_paragraph = document.add_paragraph()
        rule_p_pr = rule_paragraph._p.get_or_add_pPr()
        p_bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "18")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "C9A04A")
        p_bdr.append(bottom)
        rule_p_pr.append(p_bdr)

        title = document.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_rtl(title)
        _set_run_font(
            title.add_run("گزارش ارزیابی جامع سامانه هوشمند قیاس (GHIAS)"),
            HEADING_FONT, size=20, bold=True, color=NAVY,
        )

        subtitle = document.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_run_font(
            subtitle.add_run("Governance & Holistic Intelligent Assessment System"),
            BODY_FONT, size=11, color=GOLD,
        )

        document.add_paragraph()

        detail_heading = document.add_heading("۱. اطلاعات کلی گزارش", level=1)
        _set_rtl(detail_heading)
        for run in detail_heading.runs:
            _set_run_font(run, HEADING_FONT, size=14, bold=True, color=NAVY)

        detail_table = document.add_table(rows=0, cols=2)
        detail_table.style = "Light Grid Accent 1"
        rows = [
            ("نام واحد", visit.get("facility_name", "")),
            ("عنوان ارزیابی", f"ارزیابی {visit.get('domain_name', '')}"),
            ("حوزه ارزیابی", visit.get("domain_name", "")),
            ("تاریخ بازدید", format_jalali_date(parse_visit_date(visit.get("visit_date")))),
            ("ارزیاب(ها)", visit.get("inspector_name", "")),
        ]
        for label, value in rows:
            row = detail_table.add_row()
            _set_run_font(row.cells[0].paragraphs[0].add_run(label), BODY_FONT, size=10, bold=True)
            _set_run_font(row.cells[1].paragraphs[0].add_run(str(value)), BODY_FONT, size=10)
            _set_cell_rtl(row.cells[0])
            _set_cell_rtl(row.cells[1])

        document.add_paragraph()

    # ------------------------------------------------------------- خلاصه مدیریتی + KPI
    def _build_executive_summary(
        self, document: Document, visit: dict[str, Any], category_breakdown: list[Any],
        recommendations: list[dict[str, Any]], deficient_count: Optional[int],
    ) -> None:
        heading = document.add_heading("۲. خلاصه مدیریتی", level=1)
        _set_rtl(heading)
        for run in heading.runs:
            _set_run_font(run, HEADING_FONT, size=14, bold=True, color=NAVY)

        overall_score = visit.get("overall_score") or 0
        overall_risk = visit.get("overall_risk_level", "بدون داده")
        answered_categories = [c for c in category_breakdown if c.answered_count > 0]
        total_answered = sum(c.answered_count for c in category_breakdown)
        deficiencies = deficient_count if deficient_count is not None else len(recommendations)
        compliant = max(total_answered - deficiencies, 0)

        summary_paragraph = document.add_paragraph()
        _set_rtl(summary_paragraph)
        summary_text = (
            f"این گزارش نتایج ارزیابی «{visit.get('domain_name', '')}» واحد «{visit.get('facility_name', '')}» "
            f"را بر اساس استانداردها و بهترین تجارب مرتبط ارائه می‌دهد. ارزیابی در "
            f"{to_persian_digits(len(answered_categories))} زیرحوزه از مجموع {to_persian_digits(len(category_breakdown))} "
            f"زیرحوزه تعریف‌شده انجام شده است. بر اساس نتایج، سطح آمادگی کلی واحد "
            f"{to_persian_digits(round(overall_score, 1))} درصد ارزیابی گردید که نشان‌دهنده وضعیت «{overall_risk}» است. "
            f"پیشنهاد می‌شود اقدامات اصلاحی ارائه‌شده در این گزارش در برنامه بهبود مستمر واحد قرار گیرد."
        )
        _set_run_font(summary_paragraph.add_run(summary_text), BODY_FONT, size=11)

        document.add_paragraph()

        kpi_table = document.add_table(rows=2, cols=5)
        kpi_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _remove_table_borders(kpi_table)

        kpi_items = [
            (to_persian_digits(total_answered), "کنترل‌های ارزیابی‌شده", "1C2B3A"),
            (to_persian_digits(deficiencies), "عدم انطباق‌ها", "EB5757"),
            (None, "سطح آمادگی کلی", RISK_HEX.get(overall_risk, "9AA5B1")),
            (to_persian_digits(compliant), "انطباق‌ها", "27AE60"),
            (to_persian_digits(len(recommendations)), "فرصت‌های بهبود", "F2994A"),
        ]

        for col_index, (value, label, color_hex) in enumerate(kpi_items):
            value_cell = kpi_table.rows[0].cells[col_index]
            _set_cell_shading(value_cell, "F4F6F8")
            _set_cell_vertical_center(value_cell)
            value_paragraph = value_cell.paragraphs[0]
            value_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

            if value is None:
                gauge_path = _make_gauge_image(overall_score, color_hex)
                run = value_paragraph.add_run()
                run.add_picture(gauge_path, width=Cm(2.1))
            else:
                _set_run_font(value_paragraph.add_run(value), HEADING_FONT, size=22, bold=True,
                              color=RGBColor.from_string(color_hex))

            label_cell = kpi_table.rows[1].cells[col_index]
            _set_cell_shading(label_cell, "F4F6F8")
            label_paragraph = label_cell.paragraphs[0]
            label_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_rtl(label_paragraph)
            _set_run_font(label_paragraph.add_run(label), BODY_FONT, size=9, color=GRAY_TEXT)

        document.add_paragraph()

    # ------------------------------------------------------------- جدول زیرحوزه‌ها
    def _build_category_table(self, document: Document, category_breakdown: list[Any]) -> None:
        heading = document.add_heading("۳. نتایج تفصیلی ارزیابی", level=1)
        _set_rtl(heading)
        for run in heading.runs:
            _set_run_font(run, HEADING_FONT, size=14, bold=True, color=NAVY)

        table = document.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = ["ردیف", "زیرحوزه ارزیابی", "امتیاز (%)", "پاسخ‌داده‌شده", "وضعیت"]
        for cell, text in zip(table.rows[0].cells, headers):
            _set_cell_shading(cell, "1C2B3A")
            _set_run_font(cell.paragraphs[0].add_run(text), BODY_FONT, size=10, bold=True, color=WHITE)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_cell_rtl(cell)

        total_score = 0.0
        counted = 0
        for row_index, result in enumerate(category_breakdown, start=1):
            row = table.add_row()
            values = [
                to_persian_digits(row_index), result.category_name,
                to_persian_digits(result.score), f"{to_persian_digits(result.answered_count)}/{to_persian_digits(result.total_questions)}",
            ]
            for cell, value in zip(row.cells[:4], values):
                _set_run_font(cell.paragraphs[0].add_run(value), BODY_FONT, size=10)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                _set_cell_rtl(cell)

            status_cell = row.cells[4]
            _set_cell_shading(status_cell, RISK_HEX.get(result.risk_label, "9AA5B1"))
            status_paragraph = status_cell.paragraphs[0]
            status_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_rtl(status_paragraph)
            _set_run_font(status_paragraph.add_run(result.risk_label), BODY_FONT, size=9, bold=True, color=WHITE)

            if result.answered_count > 0:
                total_score += result.score
                counted += 1

        overall_average = round(total_score / counted, 1) if counted else 0.0
        total_row = table.add_row()
        _set_cell_shading(total_row.cells[0], "F4F6F8")
        total_row.cells[0].merge(total_row.cells[1])
        _set_run_font(total_row.cells[0].paragraphs[0].add_run("میانگین کل"), BODY_FONT, size=10, bold=True)
        total_row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_cell_rtl(total_row.cells[0])
        for c in (total_row.cells[2], total_row.cells[3], total_row.cells[4]):
            _set_cell_shading(c, "F4F6F8")
        _set_run_font(total_row.cells[2].paragraphs[0].add_run(to_persian_digits(overall_average)),
                      BODY_FONT, size=10, bold=True)
        total_row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        document.add_paragraph()

    # ------------------------------------------------------------- جدول اقدامات اصلاحی
    def _build_recommendations_table(self, document: Document, recommendations: list[dict[str, Any]]) -> None:
        heading = document.add_heading("۴. مهم‌ترین اقدامات اصلاحی پیشنهادی", level=1)
        _set_rtl(heading)
        for run in heading.runs:
            _set_run_font(run, HEADING_FONT, size=14, bold=True, color=NAVY)

        if not recommendations:
            paragraph = document.add_paragraph()
            _set_rtl(paragraph)
            _set_run_font(paragraph.add_run("هیچ اقدام اصلاحی برای این ارزیابی ثبت نشده است."), BODY_FONT, size=11)
            return

        table = document.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = ["ردیف", "زیرحوزه", "اقدام پیشنهادی", "اولویت", "زمان‌بندی پیشنهادی"]
        for cell, text in zip(table.rows[0].cells, headers):
            _set_cell_shading(cell, "1C2B3A")
            _set_run_font(cell.paragraphs[0].add_run(text), BODY_FONT, size=10, bold=True, color=WHITE)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_cell_rtl(cell)

        for row_index, rec in enumerate(recommendations, start=1):
            row = table.add_row()
            priority = rec.get("priority", "")
            values = [to_persian_digits(row_index), rec.get("category_name", ""), rec.get("recommendation_text", "")]
            for cell, value in zip(row.cells[:3], values):
                _set_run_font(cell.paragraphs[0].add_run(value), BODY_FONT, size=10)
                _set_cell_rtl(cell)

            priority_cell = row.cells[3]
            _set_cell_shading(priority_cell, PRIORITY_HEX.get(priority, "9AA5B1"))
            priority_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_rtl(priority_cell.paragraphs[0])
            _set_run_font(priority_cell.paragraphs[0].add_run(priority), BODY_FONT, size=9, bold=True, color=WHITE)

            timeline_cell = row.cells[4]
            timeline_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_rtl(timeline_cell.paragraphs[0])
            _set_run_font(
                timeline_cell.paragraphs[0].add_run(PRIORITY_TIMELINE.get(priority, "—")),
                BODY_FONT, size=10,
            )

        document.add_paragraph()

    # ------------------------------------------------------------- امضا
    def _build_signature_block(self, document: Document, visit: dict[str, Any], generated_by: str) -> None:
        heading = document.add_heading("۵. اطلاعات ارزیاب و تأیید گزارش", level=1)
        _set_rtl(heading)
        for run in heading.runs:
            _set_run_font(run, HEADING_FONT, size=14, bold=True, color=NAVY)

        info_table = document.add_table(rows=2, cols=2)
        info_table.style = "Table Grid"
        pairs = [
            ("نام و نام‌خانوادگی ارزیاب:", visit.get("inspector_name", "")),
            ("تهیه‌شده در سامانه توسط:", generated_by),
        ]
        for row, (label, value) in zip(info_table.rows, pairs):
            _set_run_font(row.cells[1].paragraphs[0].add_run(label), BODY_FONT, size=10, bold=True)
            _set_run_font(row.cells[0].paragraphs[0].add_run(value), BODY_FONT, size=10)
            _set_cell_rtl(row.cells[0])
            _set_cell_rtl(row.cells[1])

        document.add_paragraph()

        sign_table = document.add_table(rows=2, cols=2)
        sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _remove_table_borders(sign_table)

        labels = ["امضای ارزیاب", "تأیید مدیر حفاظت فیزیکی"]
        for cell, label in zip(sign_table.rows[0].cells, labels):
            _set_run_font(cell.paragraphs[0].add_run(label), BODY_FONT, size=11, bold=True)
            _set_cell_rtl(cell)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for cell in sign_table.rows[1].cells:
            _set_run_font(cell.paragraphs[0].add_run("......................................"), BODY_FONT, size=11)
            _set_cell_rtl(cell)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        disclaimer = document.add_paragraph()
        _set_rtl(disclaimer)
        _set_run_font(
            disclaimer.add_run(
                "این گزارش صرفاً بر اساس پاسخ‌های ثبت‌شده توسط ارزیاب در زمان بازدید تهیه شده و "
                "باید پیش از اجرای هرگونه تصمیم مدیریتی، توسط مدیر حفاظت فیزیکی واحد بررسی و تأیید شود."
            ),
            BODY_FONT, size=9, color=GRAY_TEXT,
        )

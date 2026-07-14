#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
پنجره داشبورد (Dashboard Window)
=============================================================================

این پنجره وضعیت یک واحد تحت ارزیابی را به‌صورت تصویری نمایش می‌دهد:
    - نمودار ستونی امتیاز هر یک از نُه حوزه ارزیابی، برای یک بازدید مشخص
    - نمودار دایره‌ای توزیع سطح ریسک حوزه‌ها
    - نمودار خطی روند امتیاز کلی واحد در طول زمان (بین بازدیدهای مختلف)
    - فهرست اقدامات اصلاحی همان بازدید

این پنجره فقط بازدیدهای «تکمیل‌شده» (FINISHED) را نمایش می‌دهد، چون
بازدیدهای ناتمام هنوز امتیاز نهایی معتبر ندارند.
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
from dashboard_repository import DashboardRepository  # noqa: E402

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtCharts import (
        QBarCategoryAxis,
        QBarSeries,
        QBarSet,
        QChart,
        QChartView,
        QDateTimeAxis,
        QLineSeries,
        QPieSeries,
        QValueAxis,
    )
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False


RISK_COLORS: dict[str, str] = {
    "بحرانی": "#eb5757",
    "هشدار": "#f2994a",
    "قابل قبول": "#27ae60",
    "بدون داده": "#9aa5b1",
}


class DashboardWindow(QMainWindow):
    """پنجره اصلی داشبورد وضعیت واحدهای ارزیابی‌شده."""

    def __init__(self, repository: DashboardRepository):
        super().__init__()
        self.repository = repository

        self.facilities: list[dict[str, Any]] = []
        self.visits: list[dict[str, Any]] = []
        self.current_facility_id: Optional[int] = None
        self.current_visit_id: Optional[int] = None

        self.setWindowTitle("GHIAS | داشبورد وضعیت واحدهای ارزیابی‌شده")
        self.resize(1300, 800)
        self.setLayoutDirection(Qt.RightToLeft)

        self._build_ui()
        self._load_facilities()

    # ------------------------------------------------------------- ساخت رابط
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- سایدبار واحدها -------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 10)

        sidebar_title = QLabel("واحدهای ارزیابی‌شده")
        sidebar_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.facility_list = QListWidget()
        self.facility_list.setObjectName("DomainList")
        self.facility_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.facility_list.setWordWrap(True)
        self.facility_list.currentRowChanged.connect(self._on_facility_selected)
        sidebar_layout.addWidget(self.facility_list)

        root_layout.addWidget(sidebar)

        # --- ناحیه اصلی -------------------------------------------------
        main_panel = QWidget()
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.header_label = QLabel("یک واحد را از فهرست کنار صفحه انتخاب کنید")
        self.header_label.setObjectName("SectionHeader")
        top_row.addWidget(self.header_label, stretch=1)

        top_row.addWidget(QLabel("بازدید:"))
        self.visit_combo = QComboBox()
        self.visit_combo.setMinimumWidth(160)
        self.visit_combo.currentIndexChanged.connect(self._on_visit_changed)
        top_row.addWidget(self.visit_combo)
        main_layout.addLayout(top_row)

        self.summary_label = QLabel("امتیاز کلی: —")
        self.summary_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        main_layout.addWidget(self.summary_label)

        if not CHARTS_AVAILABLE:
            warning = QLabel(
                "ماژول نمودار (QtCharts) روی این سیستم نصب نیست.\n"
                "برای فعال‌شدن نمودارها، این دستور را اجرا کنید: pip install PySide6-Addons"
            )
            warning.setStyleSheet("color: #eb5757; font-weight: bold;")
            main_layout.addWidget(warning)

        splitter = QSplitter(Qt.Vertical)

        charts_row = QSplitter(Qt.Horizontal)
        self.bar_chart_view = self._create_chart_view()
        self.pie_chart_view = self._create_chart_view()
        charts_row.addWidget(self.bar_chart_view)
        charts_row.addWidget(self.pie_chart_view)
        splitter.addWidget(charts_row)

        bottom_row = QSplitter(Qt.Horizontal)
        self.trend_chart_view = self._create_chart_view()
        bottom_row.addWidget(self.trend_chart_view)

        recommendations_panel = QFrame()
        recommendations_panel.setObjectName("Card")
        rec_layout = QVBoxLayout(recommendations_panel)
        rec_title = QLabel("اقدامات اصلاحی این بازدید")
        rec_title.setStyleSheet("font-weight: bold;")
        rec_layout.addWidget(rec_title)
        self.recommendations_list = QListWidget()
        rec_layout.addWidget(self.recommendations_list)
        bottom_row.addWidget(recommendations_panel)

        splitter.addWidget(bottom_row)
        main_layout.addWidget(splitter, stretch=1)

        root_layout.addWidget(main_panel, stretch=1)
        self.statusBar().showMessage("آماده")

    def _create_chart_view(self):
        if not CHARTS_AVAILABLE:
            placeholder = QLabel("نمودار در دسترس نیست")
            placeholder.setAlignment(Qt.AlignCenter)
            return placeholder

        chart = QChart()
        chart.legend().setVisible(True)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view

    # ------------------------------------------------------------- واحدها
    def _load_facilities(self) -> None:
        self.facilities = self.repository.list_facilities_with_finished_visits()
        self.facility_list.clear()
        for facility in self.facilities:
            label = f"{facility['facility_name']}   ({facility['visit_count']} بازدید)"
            self.facility_list.addItem(QListWidgetItem(label))

        if self.facilities:
            self.facility_list.setCurrentRow(0)
        else:
            self.header_label.setText("هنوز هیچ بازدید تکمیل‌شده‌ای در پایگاه داده ثبت نشده است.")

    def _on_facility_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.facilities):
            return
        facility = self.facilities[row]
        self.current_facility_id = facility["facility_id"]
        self.header_label.setText(f"واحد: {facility['facility_name']}")

        self.visits = self.repository.list_finished_visits(self.current_facility_id)
        self.visit_combo.blockSignals(True)
        self.visit_combo.clear()
        for visit in self.visits:
            self.visit_combo.addItem(str(visit["visit_date"]), visit["id"])
        self.visit_combo.blockSignals(False)

        if self.visits:
            self.visit_combo.setCurrentIndex(len(self.visits) - 1)  # آخرین بازدید
            self._on_visit_changed(self.visit_combo.currentIndex())

        self._render_trend_chart()

    # ------------------------------------------------------------- بازدید انتخابی
    def _on_visit_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.visits):
            return
        visit = self.visits[index]
        self.current_visit_id = visit["id"]

        color = RISK_COLORS.get(visit["overall_risk_level"], "#9aa5b1")
        self.summary_label.setText(
            f"امتیاز کلی: {visit['overall_score']}   |   وضعیت: {visit['overall_risk_level']}   |   تاریخ: {visit['visit_date']}"
        )
        self.summary_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 16px;")

        self._render_category_charts(visit["id"])
        self._render_recommendations(visit["id"])

    # ------------------------------------------------------------- نمودار ستونی و دایره‌ای
    def _render_category_charts(self, visit_id: int) -> None:
        breakdown = self.repository.get_category_breakdown(visit_id)

        if not CHARTS_AVAILABLE:
            return

        # --- نمودار ستونی امتیاز حوزه‌ها ---------------------------------
        bar_chart = QChart()
        bar_chart.setTitle("امتیاز هر حوزه")
        bar_set = QBarSet("امتیاز")
        bar_set.append([c.score for c in breakdown])
        bar_set.setColor(QColor("#2f80ed"))

        series = QBarSeries()
        series.append(bar_set)
        bar_chart.addSeries(series)

        categories_axis = QBarCategoryAxis()
        categories_axis.append([c.category_name for c in breakdown])
        bar_chart.addAxis(categories_axis, Qt.AlignBottom)
        series.attachAxis(categories_axis)

        value_axis = QValueAxis()
        value_axis.setRange(0, 100)
        bar_chart.addAxis(value_axis, Qt.AlignLeft)
        series.attachAxis(value_axis)

        bar_chart.legend().setVisible(False)
        self.bar_chart_view.setChart(bar_chart)

        # --- نمودار دایره‌ای توزیع سطح ریسک -------------------------------
        pie_chart = QChart()
        pie_chart.setTitle("توزیع وضعیت ریسک حوزه‌ها")
        pie_series = QPieSeries()

        counts: dict[str, int] = {}
        for c in breakdown:
            counts[c.risk_label] = counts.get(c.risk_label, 0) + 1

        for label, count in counts.items():
            slice_ = pie_series.append(f"{label} ({count})", count)
            slice_.setBrush(QColor(RISK_COLORS.get(label, "#9aa5b1")))
            slice_.setLabelVisible(True)

        pie_chart.addSeries(pie_series)
        self.pie_chart_view.setChart(pie_chart)

    # ------------------------------------------------------------- نمودار روند زمانی
    def _render_trend_chart(self) -> None:
        if not CHARTS_AVAILABLE:
            return

        chart = QChart()
        chart.setTitle("روند امتیاز کلی در طول زمان")

        line_series = QLineSeries()
        line_series.setName("امتیاز کلی")

        for visit in self.visits:
            date_time = QDateTime.fromString(str(visit["visit_date"]), "yyyy-MM-dd")
            line_series.append(date_time.toMSecsSinceEpoch(), visit["overall_score"])

        chart.addSeries(line_series)

        date_axis = QDateTimeAxis()
        date_axis.setFormat("yyyy-MM-dd")
        chart.addAxis(date_axis, Qt.AlignBottom)
        line_series.attachAxis(date_axis)

        value_axis = QValueAxis()
        value_axis.setRange(0, 100)
        chart.addAxis(value_axis, Qt.AlignLeft)
        line_series.attachAxis(value_axis)

        self.trend_chart_view.setChart(chart)

    # ------------------------------------------------------------- اقدامات اصلاحی
    def _render_recommendations(self, visit_id: int) -> None:
        self.recommendations_list.clear()
        recommendations = self.repository.get_recommendations(visit_id)

        if not recommendations:
            self.recommendations_list.addItem("هیچ اقدام اصلاحی برای این بازدید ثبت نشده است.")
            return

        for rec in recommendations:
            text = f"[{rec['priority']}] {rec['question_code']} ({rec['category_name']}): {rec['recommendation_text']}"
            item = QListWidgetItem(text)
            color = {"بالا": "#eb5757", "متوسط": "#f2994a", "پایین": "#27ae60"}.get(rec["priority"], "#1f2d3d")
            item.setForeground(QColor(color))
            self.recommendations_list.addItem(item)

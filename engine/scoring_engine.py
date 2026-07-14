#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
موتور امتیازدهی (Scoring Engine)
=============================================================================

این فایل بر پایه موتور قوانین (rule_engine.py) ساخته شده و مسئول موارد
زیر است:

    ۱) محاسبه امتیاز یک حوزه ارزیابی، بر اساس پاسخ‌های ثبت‌شده برای
       سؤالات آن حوزه (میانگین وزن‌دار بر اساس وزن هر سؤال).

    ۲) اعمال قانون شکست حیاتی: اگر سؤالی حیاتی (is_critical) با
       امتیاز پایین پاسخ داده شده باشد، کل حوزه «بحرانی» می‌شود.

    ۳) محاسبه امتیاز کلی یک بازدید، بر اساس امتیاز تمام حوزه‌ها.

این فایل مستقل از پایگاه داده و رابط گرافیکی است؛ ورودی آن فقط داده‌های
ساده پایتونی (نه شیء پایگاه داده) است، تا کاملاً قابل تست باشد.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rule_engine import (
    apply_critical_override,
    classify_risk,
    compute_answer_score,
)


# =============================================================================
# ساختارهای داده ورودی و خروجی
# =============================================================================

@dataclass
class AnswerRecord:
    """یک پاسخ ثبت‌شده برای یک سؤال، به همراه اطلاعات لازم برای امتیازدهی."""

    question_id: int
    category_id: int
    weight: int
    answer_type: str
    answer_value: object
    is_critical: bool = False


@dataclass
class CategoryResult:
    """نتیجه محاسبه‌شده برای یک حوزه ارزیابی."""

    category_id: int
    category_name: str
    score: float
    risk_label: str
    has_critical_failure: bool
    answered_count: int
    total_questions: int


@dataclass
class OverallResult:
    """نتیجه نهایی و کلی یک بازدید، شامل نتیجه تمام حوزه‌ها."""

    overall_score: float
    overall_risk_label: str
    categories: list[CategoryResult] = field(default_factory=list)


# =============================================================================
# موتور امتیازدهی
# =============================================================================

class ScoringEngine:
    """
    کلاس اصلی محاسبه امتیاز. این کلاس هیچ حالت داخلی نگه نمی‌دارد؛
    تمام متدها بر اساس ورودی‌ای که دریافت می‌کنند محاسبه انجام می‌دهند.
    """

    def compute_category(
        self,
        category_id: int,
        category_name: str,
        answers: list[AnswerRecord],
        total_questions: int,
    ) -> CategoryResult:
        """
        محاسبه امتیاز یک حوزه بر اساس لیست پاسخ‌های ثبت‌شده برای آن حوزه.

        total_questions: تعداد کل سؤالات فعال آن حوزه در بانک سؤالات
        (برای محاسبه درصد پیشرفت پاسخ‌دهی، مستقل از امتیاز).
        """
        scored_items: list[tuple[float, int]] = []
        has_critical_failure = False

        for answer in answers:
            score = compute_answer_score(answer.answer_type, answer.answer_value)
            if score is None:
                continue

            scored_items.append((score, answer.weight))

            from rule_engine import CRITICAL_FAILURE_THRESHOLD

            if answer.is_critical and score < CRITICAL_FAILURE_THRESHOLD:
                has_critical_failure = True

        if not scored_items:
            return CategoryResult(
                category_id=category_id,
                category_name=category_name,
                score=0.0,
                risk_label="بدون داده",
                has_critical_failure=False,
                answered_count=0,
                total_questions=total_questions,
            )

        total_weight = sum(weight for _, weight in scored_items)
        weighted_sum = sum(score * weight for score, weight in scored_items)
        category_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        category_score = round(category_score, 1)

        base_risk = classify_risk(category_score)
        final_label = apply_critical_override(base_risk.label, has_critical_failure)

        return CategoryResult(
            category_id=category_id,
            category_name=category_name,
            score=category_score,
            risk_label=final_label,
            has_critical_failure=has_critical_failure,
            answered_count=len(scored_items),
            total_questions=total_questions,
        )

    def compute_overall(self, category_results: list[CategoryResult]) -> OverallResult:
        """
        محاسبه امتیاز کلی یک بازدید، بر اساس میانگین ساده امتیاز حوزه‌هایی
        که حداقل یک پاسخ ثبت‌شده دارند. حوزه‌های بدون پاسخ در محاسبه
        میانگین کلی لحاظ نمی‌شوند (تا امتیاز کلی به‌طور مصنوعی پایین نیاید).
        """
        answered_categories = [c for c in category_results if c.answered_count > 0]

        if not answered_categories:
            return OverallResult(
                overall_score=0.0,
                overall_risk_label="بدون داده",
                categories=category_results,
            )

        overall_score = sum(c.score for c in answered_categories) / len(answered_categories)
        overall_score = round(overall_score, 1)

        has_any_critical_failure = any(c.has_critical_failure for c in answered_categories)
        base_risk = classify_risk(overall_score)
        overall_label = apply_critical_override(base_risk.label, has_any_critical_failure)

        return OverallResult(
            overall_score=overall_score,
            overall_risk_label=overall_label,
            categories=category_results,
        )

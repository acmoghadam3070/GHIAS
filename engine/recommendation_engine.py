#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
موتور توصیه اقدامات اصلاحی (Recommendation Engine)
=============================================================================

این فایل بر اساس پاسخ‌های ناقص یک بازدید (سؤالاتی که امتیاز پایین
گرفته‌اند)، فهرستی از اقدامات اصلاحی پیشنهادی می‌سازد و آن‌ها را بر اساس
اهمیت اولویت‌بندی می‌کند.

منبع متن هر پیشنهاد، همان فیلد recommendation است که از قبل برای هر
سؤال در بانک سؤالات نوشته شده است؛ این فایل فقط تصمیم می‌گیرد کدام
پیشنهادها باید نمایش داده شوند و با چه اولویتی.

این فایل کاملاً مستقل از پایگاه داده و رابط گرافیکی است.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


# آستانه‌ای که پایین‌تر از آن، یک پاسخ «نقص» (Deficiency) محسوب می‌شود
DEFICIENCY_THRESHOLD = 50.0

PRIORITY_HIGH = "بالا"
PRIORITY_MEDIUM = "متوسط"
PRIORITY_LOW = "پایین"

# ترتیب اولویت‌ها برای مرتب‌سازی (عدد کمتر یعنی اولویت بالاتر)
PRIORITY_ORDER: dict[str, int] = {
    PRIORITY_HIGH: 0,
    PRIORITY_MEDIUM: 1,
    PRIORITY_LOW: 2,
}


@dataclass
class DeficientAnswer:
    """یک پاسخ ناقص که باید برایش اقدام اصلاحی تعیین شود."""

    answer_id: int
    question_id: int
    question_code: str
    category_name: str
    weight: int
    is_critical: bool
    score: float
    recommendation_text: str


@dataclass
class Recommendation:
    """یک اقدام اصلاحی پیشنهادی، آماده برای نمایش یا ذخیره در پایگاه داده."""

    answer_id: int
    question_code: str
    category_name: str
    priority: str
    recommendation_text: str
    score: float


class RecommendationEngine:
    """موتور تولید و اولویت‌بندی اقدامات اصلاحی."""

    def determine_priority(self, weight: int, is_critical: bool) -> str:
        """
        تعیین اولویت یک اقدام اصلاحی بر اساس وزن سؤال و حیاتی‌بودن آن.

        قانون:
            - اگر سؤال حیاتی باشد یا وزن آن پنج یا بیشتر باشد: اولویت بالا
            - اگر وزن بین سه تا چهار باشد: اولویت متوسط
            - در غیر این صورت: اولویت پایین
        """
        if is_critical or weight >= 5:
            return PRIORITY_HIGH
        if weight >= 3:
            return PRIORITY_MEDIUM
        return PRIORITY_LOW

    def generate(self, deficient_answers: list[DeficientAnswer]) -> list[Recommendation]:
        """
        تولید فهرست اقدامات اصلاحی از روی پاسخ‌های ناقص، مرتب‌شده از
        بالاترین اولویت به پایین‌ترین. اگر یک سؤال متن توصیه اصلاحی
        نداشته باشد، از فهرست حذف می‌شود (چیزی برای پیشنهاد دادن نیست).
        """
        recommendations: list[Recommendation] = []

        for answer in deficient_answers:
            if answer.score >= DEFICIENCY_THRESHOLD:
                continue  # این پاسخ اصلاً نقص محسوب نمی‌شود

            if not answer.recommendation_text.strip():
                continue  # سؤالی که توصیه اصلاحی برایش تعریف نشده

            priority = self.determine_priority(answer.weight, answer.is_critical)

            recommendations.append(
                Recommendation(
                    answer_id=answer.answer_id,
                    question_code=answer.question_code,
                    category_name=answer.category_name,
                    priority=priority,
                    recommendation_text=answer.recommendation_text,
                    score=answer.score,
                )
            )

        recommendations.sort(key=lambda r: (PRIORITY_ORDER[r.priority], r.score))
        return recommendations

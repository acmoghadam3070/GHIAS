#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
موتور قوانین (Rule Engine)
=============================================================================

این فایل مسئول دو موضوع اصلی است:

    ۱) تبدیل پاسخ خام ارزیاب (مثلاً "بله"، یا عدد ۳ از ۵) به یک امتیاز
       عددی استاندارد بین صفر تا صد.

    ۲) طبقه‌بندی یک امتیاز عددی به یکی از سطوح ریسک تعریف‌شده پروژه
       (بحرانی، هشدار، قابل قبول).

این فایل هیچ وابستگی به پایگاه داده یا رابط گرافیکی ندارد و کاملاً
مستقل قابل تست است.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


# =============================================================================
# سطوح ریسک
# =============================================================================

@dataclass(frozen=True)
class RiskThreshold:
    """یک سطح ریسک، همراه با حداقل امتیازی که برای رسیدن به آن لازم است."""

    label: str
    min_score: float
    color_hex: str


# آستانه‌های ریسک پروژه GHIAS.
# ترتیب از کم به زیاد بر اساس min_score اهمیت دارد.
RISK_THRESHOLDS: list[RiskThreshold] = [
    RiskThreshold(label="بحرانی", min_score=0.0, color_hex="#eb5757"),
    RiskThreshold(label="هشدار", min_score=60.0, color_hex="#f2994a"),
    RiskThreshold(label="قابل قبول", min_score=85.0, color_hex="#27ae60"),
]

CRITICAL_LABEL = "بحرانی"

# اگر امتیاز یک پاسخ حیاتی (is_critical) کمتر از این مقدار باشد،
# کل حوزه مربوطه صرف‌نظر از میانگین امتیاز، به‌صورت خودکار «بحرانی» می‌شود.
CRITICAL_FAILURE_THRESHOLD = 50.0


def classify_risk(score: float) -> RiskThreshold:
    """
    بازگرداندن سطح ریسک متناظر با یک امتیاز عددی بین صفر تا صد.
    اگر امتیاز خارج از بازه معتبر باشد، به نزدیک‌ترین مرز محدود می‌شود.
    """
    bounded_score = max(0.0, min(100.0, score))
    applicable = [t for t in RISK_THRESHOLDS if bounded_score >= t.min_score]
    return max(applicable, key=lambda t: t.min_score)


def apply_critical_override(base_label: str, has_critical_failure: bool) -> str:
    """
    اگر در یک حوزه، حداقل یک سؤال حیاتی با شکست مواجه شده باشد،
    برچسب ریسک آن حوزه صرف‌نظر از امتیاز محاسبه‌شده، «بحرانی» می‌شود.
    """
    if has_critical_failure:
        return CRITICAL_LABEL
    return base_label


# =============================================================================
# تبدیل پاسخ خام به امتیاز عددی (صفر تا صد)
# =============================================================================

# نگاشت مقادیر متنی رایج برای سؤالات بله/خیر به امتیاز عددی.
# هم مقادیر فارسی و هم مقادیر انگلیسی پشتیبانی می‌شوند تا با ورودی‌های
# مختلف رابط کاربری سازگار باشد.
YES_NO_SCORE_MAP: dict[str, float] = {
    "بله": 100.0,
    "خیر": 0.0,
    "yes": 100.0,
    "no": 0.0,
    "true": 100.0,
    "false": 0.0,
    "1": 100.0,
    "0": 0.0,
}


def score_yes_no(raw_value: str) -> float:
    """تبدیل پاسخ بله/خیر به امتیاز صفر یا صد."""
    key = str(raw_value).strip().lower()
    if key in YES_NO_SCORE_MAP:
        return YES_NO_SCORE_MAP[key]
    # مقدار فارسی بدون تبدیل به حروف کوچک هم بررسی شود
    key_fa = str(raw_value).strip()
    return YES_NO_SCORE_MAP.get(key_fa, 0.0)


def score_scale_1_5(raw_value: float | int | str) -> float:
    """تبدیل پاسخ مقیاسی یک تا پنج به امتیاز صفر تا صد."""
    value = float(raw_value)
    value = max(1.0, min(5.0, value))
    return (value - 1.0) / 4.0 * 100.0


def score_percentage(raw_value: float | int | str) -> float:
    """اعتبارسنجی و محدودسازی یک مقدار درصدی به بازه صفر تا صد."""
    value = float(raw_value)
    return max(0.0, min(100.0, value))


def score_manual(raw_value: float | int | str) -> float | None:
    """
    برای انواع پاسخ چندگزینه‌ای یا متنی، امتیاز باید مستقیماً توسط
    ارزیاب در حین ارزیابی وارد شده باشد. این تابع فقط آن مقدار را
    اعتبارسنجی و محدود می‌کند.
    """
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(100.0, value))


def compute_answer_score(answer_type: str, raw_value: object) -> float | None:
    """
    نقطه ورود اصلی موتور قوانین: تبدیل یک پاسخ خام (بسته به نوع سؤال)
    به یک امتیاز استاندارد صفر تا صد.
    اگر مقدار خالی یا نامعتبر باشد، None بازگردانده می‌شود (یعنی سؤال
    هنوز پاسخ داده نشده یا قابل محاسبه نیست).
    """
    if raw_value is None or str(raw_value).strip() == "":
        return None

    if answer_type == "yes_no":
        return score_yes_no(raw_value)  # type: ignore[arg-type]

    if answer_type == "scale_1_5":
        try:
            return score_scale_1_5(raw_value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    if answer_type == "percentage":
        try:
            return score_percentage(raw_value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    # multiple_choice و text
    return score_manual(raw_value)  # type: ignore[arg-type]

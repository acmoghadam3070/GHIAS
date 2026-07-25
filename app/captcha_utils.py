#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
تولید کپچای تصویری (Captcha Utils)
=============================================================================

این فایل یک کپچای تصویری کاملاً آفلاین تولید می‌کند (بدون نیاز به
اینترنت یا سرویس بیرونی مثل گوگل). یک رشته تصادفی همراه با خطوط نویز
و کمی چرخش تصادفی روی هر حرف رسم می‌شود.

این فایل کاملاً مستقل از رابط گرافیکی است تا در آینده، همین منطق برای
نسخه وب هم (پشت یک API) قابل استفاده مجدد باشد.
=============================================================================
"""

from __future__ import annotations

import io
import random
import string

from PIL import Image, ImageDraw, ImageFont

CAPTCHA_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # بدون ارقام/حروف شبیه به هم (0/O, 1/I)
CAPTCHA_LENGTH = 5
IMAGE_SIZE = (180, 60)


def generate_captcha_text(length: int = CAPTCHA_LENGTH) -> str:
    """تولید یک رشته تصادفی برای کپچا."""
    return "".join(random.choices(CAPTCHA_CHARSET, k=length))


def render_captcha_image(text: str, size: tuple[int, int] = IMAGE_SIZE) -> bytes:
    """
    رسم متن کپچا روی یک تصویر، همراه با نویز، و بازگرداندن آن به‌صورت
    بایت‌های PNG (برای نمایش مستقیم در رابط گرافیکی یا ارسال در آینده
    از طریق API وب).
    """
    width, height = size
    image = Image.new("RGB", size, color=(244, 246, 248))
    draw = ImageDraw.Draw(image)

    # خطوط نویز پس‌زمینه
    for _ in range(6):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        color = (
            random.randint(180, 210), random.randint(180, 210), random.randint(180, 210),
        )
        draw.line([start, end], fill=color, width=1)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
    except OSError:
        font = ImageFont.load_default()

    char_spacing = width // (len(text) + 1)
    for index, char in enumerate(text):
        char_image = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_image)
        color = (
            random.randint(28, 60), random.randint(40, 70), random.randint(70, 110),
        )
        char_draw.text((10, 5), char, font=font, fill=color)
        angle = random.randint(-25, 25)
        rotated = char_image.rotate(angle, expand=True)

        x = char_spacing * index + random.randint(-5, 5) + 10
        y = random.randint(2, 12)
        image.paste(rotated, (x, y), rotated)

    # نقاط نویز پراکنده
    for _ in range(80):
        point = (random.randint(0, width - 1), random.randint(0, height - 1))
        draw.point(point, fill=(200, 205, 210))

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_captcha() -> tuple[str, bytes]:
    """
    نقطه ورود اصلی: تولید یک کپچای تازه.
    خروجی: (متن صحیح کپچا، بایت‌های تصویر PNG)
    """
    text = generate_captcha_text()
    image_bytes = render_captcha_image(text)
    return text, image_bytes


def verify_captcha(user_input: str, expected_text: str) -> bool:
    """بررسی درست بودن کپچای واردشده (بدون توجه به بزرگی/کوچکی حروف)."""
    return user_input.strip().upper() == expected_text.strip().upper()

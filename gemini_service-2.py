"""
سرویس پردازش متن با Google Gemini.

مسئولیت این سرویس فقط «پردازش متن» است:
- ترجمه خلاصه داستان به فارسی روان
- تولید متن معرفی حرفه‌ای برای کانال تلگرام
- ترجمه ژانرها به فارسی

Gemini هرگز منبع اطلاعات واقعی (اسم، سال، بازیگر و ...) نیست؛
تمام داده‌های واقعی از TMDB می‌آیند و فقط برای پردازش متن به Gemini
ارسال می‌شوند.

نکته مهم درباره مدل: مدل‌های قدیمی مثل gemini-1.5-flash منقضی/غیرفعال
شده‌اند. مدل پیش‌فرض این سرویس از config.GEMINI_MODEL خوانده می‌شود
(پیش‌فرض یک مدل فعال و پشتیبانی‌شده است) تا با تغییر یک متغیر محیطی
بتوان بدون تغییر کد به مدل جدیدتر مهاجرت کرد.

در صورت هرگونه خطا (کلید نامعتبر، قطعی سرویس، مدل منقضی، خطای شبکه و ...)
این سرویس هرگز Exception بیرون نمی‌اندازد و ربات را متوقف نمی‌کند؛ به‌جای
آن از حالت جایگزین (فallback روی متن انگلیسی/فارسی خام TMDB) استفاده می‌شود.
"""
import json
import logging
from typing import Any

import google.generativeai as genai

from config import config

logger = logging.getLogger(__name__)

genai.configure(api_key=config.GEMINI_API_KEY)


def _get_model():
    """مدل هر بار تازه ساخته می‌شود تا اگر GEMINI_MODEL در زمان اجرا عوض شود
    (مثلاً بعد از ری‌استارت با متغیر محیطی جدید) بدون نیاز به تغییر کد اعمال شود."""
    return genai.GenerativeModel(config.GEMINI_MODEL)


_MOVIE_PROMPT_TEMPLATE = """
تو یک ویراستار حرفه‌ای محتوای فارسی برای یک کانال تلگرامی فیلم و سریال هستی.

اطلاعات زیر همگی واقعی و از TMDB گرفته شده‌اند. وظیفه‌ی تو فقط «پردازش متن»
است؛ هیچ اطلاعات جدیدی اضافه نکن و در واقعیت‌ها (اسم افراد، سال، اعداد و ...)
هیچ تغییری نده.

نوع محتوا: {media_type_fa}
عنوان: {title}
سال: {year}
ژانرها (انگلیسی): {genres}
کارگردان/سازنده: {director}
بازیگران: {actors}
خلاصه داستان اصلی: {description}

وظایف تو:
۱. خلاصه داستان را به فارسی روان و طبیعی برگردان (ترجمه کلمه‌به‌کلمه نباشد).
۲. یک متن معرفی کوتاه و حرفه‌ای (۲ تا ۴ جمله) مناسب انتشار در کانال تلگرام بنویس.
۳. ژانرها را به معادل رایج فارسی در سینما و تلویزیون ترجمه کن.

خروجی را دقیقاً و فقط به‌صورت یک JSON با این ساختار بده،
بدون هیچ متن، توضیح یا Markdown اضافه قبل یا بعد از آن:

{{
  "description_fa": "...",
  "channel_intro_fa": "...",
  "genres_fa": "..."
}}
"""


def _fallback_result(details: dict[str, Any]) -> dict[str, Any]:
    """در صورت خطای Gemini، از خلاصه فارسی TMDB (اگر موجود بود) یا متن انگلیسی استفاده می‌شود."""
    return {
        "description_fa": details.get("description_fa_raw") or details.get("description_en") or "",
        "channel_intro_fa": "",
        "genres_fa": details.get("genres") or "",
    }


def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[len("json"):]
    return text.strip()


async def process_movie_text(details: dict[str, Any]) -> dict[str, Any]:
    """پردازش متن برای فیلم سینمایی یا سریال (هر دو از همین تابع استفاده می‌کنند)."""
    media_type_fa = "سریال" if details.get("media_type") == "series" else "فیلم سینمایی"
    prompt = _MOVIE_PROMPT_TEMPLATE.format(
        media_type_fa=media_type_fa,
        title=details.get("title") or "",
        year=details.get("year") or "نامشخص",
        genres=details.get("genres") or "نامشخص",
        director=details.get("director") or "نامشخص",
        actors=details.get("actors") or "نامشخص",
        description=details.get("description_fa_raw") or details.get("description_en") or "",
    )

    try:
        model = _get_model()
        response = await model.generate_content_async(prompt)
        cleaned = _clean_json_text(response.text)
        parsed = json.loads(cleaned)

        return {
            "description_fa": parsed.get("description_fa") or _fallback_result(details)["description_fa"],
            "channel_intro_fa": parsed.get("channel_intro_fa") or "",
            "genres_fa": parsed.get("genres_fa") or details.get("genres") or "",
        }
    except Exception:
        # هر خطایی (کلید نامعتبر، مدل منقضی، قطعی شبکه، JSON نامعتبر و ...)
        # نباید کل فرآیند افزودن محتوا را متوقف کند.
        logger.exception("خطا در پردازش متن با Gemini؛ استفاده از حالت جایگزین.")
        return _fallback_result(details)

import httpx

from config import GEMINI_API_KEY

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


async def process_with_gemini(data: dict) -> dict:
    """فقط پردازش متن: ترجمه خلاصه، ژانر فارسی، متن معرفی کانال.
    Gemini منبع اطلاعات نیست، فقط متن ورودی از TMDB رو پردازش می‌کنه."""
    if not GEMINI_API_KEY:
        # اگه کلید تنظیم نشده بود، بدون ترجمه ادامه بده (به‌جای کرش کردن)
        return {
            "genre_fa": data.get("genre", ""),
            "summary_fa": data.get("description_raw", ""),
            "intro": "",
        }

    prompt = _build_prompt(data)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            resp.raise_for_status()
            result = resp.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (httpx.HTTPError, KeyError, IndexError):
        text = ""

    return _parse_gemini_output(text, data)


def _build_prompt(data: dict) -> str:
    content_label = "سریال" if data.get("content_type") == "tv" else "فیلم"
    return f"""اطلاعات زیر درباره یک {content_label} است. فقط وظیفه تو پردازش متنه، نه اضافه کردن اطلاعات جدید:

عنوان: {data.get('title')}
ژانر (انگلیسی): {data.get('genre')}
خلاصه داستان (انگلیسی): {data.get('description_raw')}

وظایف تو:
1. خلاصه داستان بالا رو به فارسیِ روان و طبیعی ترجمه کن (نه ترجمه تحت‌اللفظی کلمه به کلمه).
2. ژانرهای بالا رو به فارسی برگردون.
3. یک متن معرفی کوتاه و حرفه‌ای (۲ تا ۳ جمله) برای پست کانال تلگرام بنویس که برای مخاطب جذاب باشه.

خروجی رو دقیقاً و فقط به همین فرمت بده، بدون هیچ توضیح اضافه یا مقدمه:
ژانر_فارسی: <ژانرهای فارسی با کاما جدا شده>
خلاصه_فارسی: <ترجمه روان خلاصه داستان>
معرفی: <متن معرفی کانال>
"""


def _parse_gemini_output(text: str, fallback_data: dict) -> dict:
    genre_fa = fallback_data.get("genre", "")
    summary_fa = fallback_data.get("description_raw", "")
    intro = ""

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("ژانر_فارسی:"):
            genre_fa = line.split(":", 1)[1].strip()
        elif line.startswith("خلاصه_فارسی:"):
            summary_fa = line.split(":", 1)[1].strip()
        elif line.startswith("معرفی:"):
            intro = line.split(":", 1)[1].strip()

    return {"genre_fa": genre_fa, "summary_fa": summary_fa, "intro": intro}
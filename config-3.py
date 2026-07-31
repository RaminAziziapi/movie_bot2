"""
تنظیمات پروژه - تمام مقادیر از متغیرهای محیطی (Environment Variables) خوانده می‌شوند.
هیچ مقدار حساسی نباید مستقیم در کد نوشته شود.

نکته درباره ادمین‌ها:
ADMIN_IDS در Environment فقط «ادمین‌های اصلی/بوت‌استرپ» هستند که همیشه دسترسی
کامل دارند (حتی اگر دیتابیس خالی یا در دسترس نباشد). ادمین‌های اضافه‌شده از
داخل ربات (پنل مدیریت) در جدول admins دیتابیس ذخیره می‌شوند - نگاه کنید به
admin_service.py برای منطق ترکیب این دو منبع.
"""
import os


def _get_required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"متغیر محیطی «{name}» تنظیم نشده است.")
    return value


def _parse_chat_id(raw: str):
    """CHANNEL_ID می‌تواند عدد (مثل -1001234567890) یا یوزرنیم (مثل @mychannel) باشد."""
    raw = raw.strip()
    if raw.lstrip("-").isdigit():
        return int(raw)
    return raw


class Config:
    # --- تلگرام ---
    BOT_TOKEN: str = _get_required("BOT_TOKEN")
    # ادمین‌های اصلی (بوت‌استرپ) - همیشه دسترسی کامل دارند، مستقل از دیتابیس.
    ADMIN_IDS: list[int] = [
        int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()
    ]

    # --- دیتابیس (PostgreSQL) ---
    DATABASE_URL: str = _get_required("DATABASE_URL")
    DB_SSL: bool = os.environ.get("DB_SSL", "true").lower() != "false"

    # --- API های خارجی ---
    TMDB_API_KEY: str = _get_required("TMDB_API_KEY")
    GEMINI_API_KEY: str = _get_required("GEMINI_API_KEY")
    # مدل پیش‌فرض یک مدل معتبر و فعال Gemini است (نسخه‌های قدیمی مثل
    # gemini-1.5-flash منقضی شده‌اند). در صورت نیاز با متغیر محیطی
    # GEMINI_MODEL می‌توانید مدل جدیدتری (مثلاً gemini-3.5-flash) را تنظیم کنید.
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # --- کانال انتشار پست (فیلم/سریال) ---
    CHANNEL_ID = _parse_chat_id(_get_required("CHANNEL_ID"))
    CHANNEL_LINK: str = os.environ.get("CHANNEL_LINK", "")

    # --- وبهوک (Render Web Service) ---
    WEBHOOK_URL: str = _get_required("WEBHOOK_URL")  # مثال: https://your-app.onrender.com
    WEBHOOK_PATH: str = os.environ.get("WEBHOOK_PATH", "/webhook")
    PORT: int = int(os.environ.get("PORT", 10000))

    # --- سایر تنظیمات ---
    AUTO_DELETE_SECONDS: int = int(os.environ.get("AUTO_DELETE_SECONDS", 60))


config = Config()

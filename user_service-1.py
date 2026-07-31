"""
مدیریت کاربران عادی ربات: ثبت/به‌روزرسانی هنگام /start و آمار کلی.
"""
import logging

from telegram import Update

from repository import count_content, count_pending_requests, count_users, upsert_user
from texts import texts

logger = logging.getLogger(__name__)


async def register_user(update: Update) -> None:
    user = update.effective_user
    if user is None:
        return
    try:
        await upsert_user(user.id, user.username, user.first_name)
    except Exception:
        logger.exception("خطا در ثبت/به‌روزرسانی کاربر %s در دیتابیس", user.id)


async def get_stats_text() -> str:
    try:
        users_count = await count_users()
        movies_count = await count_content(media_type="movie")
        series_count = await count_content(media_type="series")
        pending_requests = await count_pending_requests()
    except Exception:
        logger.exception("خطا در دریافت آمار")
        return texts.GENERIC_ERROR

    lines = [
        texts.USER_STATS.format(count=users_count),
        f"🎬 تعداد فیلم‌های ثبت‌شده: {movies_count}",
        f"📺 تعداد سریال‌های ثبت‌شده: {series_count}",
        f"📥 درخواست‌های در انتظار بررسی: {pending_requests}",
    ]
    return "\n".join(lines)

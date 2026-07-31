"""
حذف خودکار پیام‌های حاوی فایل تحویل‌داده‌شده به کاربر، بعد از مدت زمان
مشخص‌شده در config.AUTO_DELETE_SECONDS.

در صورت وجود JobQueue (حالت معمول Application در python-telegram-bot)
از آن استفاده می‌شود؛ در غیر این صورت (مثلاً محیط تست بدون JobQueue) از
یک Task ناهمزمان ساده به‌عنوان جایگزین استفاده می‌شود.

حذف پیام هرگز نباید کل فرآیند تحویل فایل را با خطا متوقف کند: اگر پیام
قبلاً توسط کاربر حذف شده باشد یا ربات دسترسی کافی نداشته باشد، خطا فقط
لاگ می‌شود.
"""
import asyncio
import logging

from telegram.ext import ContextTypes

from config import config

logger = logging.getLogger(__name__)


async def _delete_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except Exception:
        logger.debug(
            "پیام %s در چت %s قابل حذف نبود (احتمالاً قبلاً حذف شده).",
            data["message_id"], data["chat_id"],
        )


async def _delayed_delete(bot, chat_id: int, message_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        logger.debug("پیام %s در چت %s قابل حذف نبود.", message_id, chat_id)


def schedule_deletion(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int | None = None
) -> None:
    """زمان‌بندی حذف یک پیام؛ delay بر حسب ثانیه (پیش‌فرض از config)."""
    delay = delay if delay is not None else config.AUTO_DELETE_SECONDS

    if getattr(context, "job_queue", None) is not None:
        context.job_queue.run_once(
            _delete_job, when=delay, data={"chat_id": chat_id, "message_id": message_id}
        )
    else:
        asyncio.create_task(_delayed_delete(context.bot, chat_id, message_id, delay))

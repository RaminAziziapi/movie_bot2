import asyncio
import logging

from telegram.error import TelegramError

import database as db
from config import AUTO_DELETE_SECONDS

logger = logging.getLogger(__name__)


async def send_movie_to_user(chat_id: int, context, movie_id: str) -> None:
    movie = db.get_movie(movie_id)
    if not movie:
        await context.bot.send_message(chat_id=chat_id, text="❗️ فیلم مورد نظر پیدا نشد.")
        return

    _, name, season, episode, file_id = movie
    caption = f"🎬 {name}\n📁 فصل {season} | قسمت {episode}\n\n⚠️ این ویدیو تا {AUTO_DELETE_SECONDS} ثانیه دیگر حذف می‌شود."
    await _send_and_schedule_delete(chat_id, context, file_id, caption)


async def send_episode_to_user(chat_id: int, context, code: str) -> None:
    episode = db.get_episode_by_code(code)
    if not episode:
        await context.bot.send_message(chat_id=chat_id, text="❗️ قسمت مورد نظر پیدا نشد.")
        return

    _, series_id, episode_number, file_id, name, season = episode
    caption = (
        f"🎬 {name}\n📺 فصل {season} | قسمت {episode_number:02d}\n\n"
        f"⚠️ این ویدیو تا {AUTO_DELETE_SECONDS} ثانیه دیگر حذف می‌شود."
    )
    await _send_and_schedule_delete(chat_id, context, file_id, caption)


async def _send_and_schedule_delete(chat_id: int, context, file_id: str, caption: str) -> None:
    try:
        sent_message = await context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
    except TelegramError as exc:
        logger.warning("خطا در ارسال ویدیو: %s", exc)
        await context.bot.send_message(chat_id=chat_id, text="❗️ ارسال ویدیو با خطا مواجه شد.")
        return

    asyncio.create_task(_delete_video_later(context, chat_id, sent_message.message_id))


async def _delete_video_later(context, chat_id: int, message_id: int) -> None:
    await asyncio.sleep(AUTO_DELETE_SECONDS)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError as exc:
        logger.warning("خطا در حذف پیام ویدیو: %s", exc)
        return

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🗑 ویدیو حذف شد. برای دریافت مجدد از لینک اختصاصی استفاده کنید.",
        )
    except TelegramError as exc:
        logger.warning("خطا در ارسال پیام اطلاع‌رسانی: %s", exc)

"""
انتشار پست فیلم/سریال در کانال + تحویل فایل به کاربر از داخل ربات.

انتشار:
    فقط بعد از تأیید صریح ادمین (دکمه «✅ انتشار» در پیش‌نمایش نهایی، یا
    دکمه «📢 انتشار در کانال» در پنل مدیریت محتوا) این ماژول فراخوانی
    می‌شود. این ماژول هرگز خودش تصمیم به انتشار نمی‌گیرد.

تحویل به کاربر:
    دکمه‌ی داخل پست کانال («🎬 دریافت فیلم از ربات» / «📺 دریافت قسمت‌ها
    از ربات») یک لینک عمیق (Deep Link) به‌شکل
        https://t.me/<username>?start=movie_<id>  یا  start=series_<id>
    است. با کلیک روی آن کاربر وارد چت خصوصی با ربات می‌شود و start.py
    با فراخوانی `handle_deep_link` در همین فایل، فرآیند انتخاب کیفیت/فصل/
    قسمت و ارسال فایل (همراه حذف خودکار) را آغاز می‌کند.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from auto_delete import schedule_deletion
from config import config
from inline import deliver_episode_keyboard, deliver_quality_keyboard, deliver_season_keyboard
from repository import (
    count_episodes,
    get_content_by_id,
    get_content_files,
    get_episode,
    get_episodes,
    get_season_by_number,
    get_seasons,
    mark_content_published,
    mark_season_published,
)
from texts import texts

logger = logging.getLogger(__name__)

_bot_username_cache: str | None = None


async def _get_bot_username(bot) -> str:
    global _bot_username_cache
    if _bot_username_cache is None:
        me = await bot.get_me()
        _bot_username_cache = me.username
    return _bot_username_cache


async def _deep_link(bot, payload: str) -> str:
    username = await _get_bot_username(bot)
    return f"https://t.me/{username}?start={payload}"


# ==================== انتشار فیلم سینمایی ====================

async def publish_movie(bot, content_id: int) -> bool:
    try:
        content = await get_content_by_id(content_id)
        if not content:
            return False
        content = dict(content)

        files = await get_content_files(content_id)
        qualities = [f["quality"] for f in files]
        caption = texts.channel_post_movie(content, qualities)
        link = await _deep_link(bot, f"movie_{content_id}")
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(texts.GET_MOVIE_BUTTON, url=link)]])

        message_id = await _send_or_update_post(bot, content, caption, markup)
        if message_id is None:
            return False

        await mark_content_published(content_id, message_id)
        return True
    except Exception:
        logger.exception("خطا در انتشار فیلم در کانال (content_id=%s)", content_id)
        return False


# ==================== انتشار سریال ====================

async def publish_series(bot, content_id: int) -> bool:
    try:
        content = await get_content_by_id(content_id)
        if not content:
            return False
        content = dict(content)

        seasons = await get_seasons(content_id)
        seasons_summary = []
        for season in seasons:
            episode_count = await count_episodes(season["id"])
            if episode_count:
                seasons_summary.append((season["season_number"], episode_count))

        caption = texts.channel_post_series(content, seasons_summary)
        link = await _deep_link(bot, f"series_{content_id}")
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(texts.GET_SERIES_BUTTON, url=link)]])

        message_id = await _send_or_update_post(bot, content, caption, markup)
        if message_id is None:
            return False

        await mark_content_published(content_id, message_id)
        for season in seasons:
            await mark_season_published(season["id"], message_id)
        return True
    except Exception:
        logger.exception("خطا در انتشار سریال در کانال (content_id=%s)", content_id)
        return False


async def _send_or_update_post(bot, content: dict, caption: str, markup: InlineKeyboardMarkup):
    """اگر قبلاً منتشر شده، پست موجود را به‌روزرسانی می‌کند؛ در غیر این صورت پست جدید می‌سازد."""
    poster_url = content.get("poster_url")
    already_published = content.get("published")
    existing_message_id = content.get("channel_message_id")

    if already_published and existing_message_id:
        try:
            if poster_url:
                await bot.edit_message_caption(
                    chat_id=config.CHANNEL_ID,
                    message_id=existing_message_id,
                    caption=caption,
                    reply_markup=markup,
                )
            else:
                await bot.edit_message_text(
                    chat_id=config.CHANNEL_ID,
                    message_id=existing_message_id,
                    text=caption,
                    reply_markup=markup,
                )
            return existing_message_id
        except Exception:
            logger.warning("ویرایش پست قبلی کانال ممکن نشد؛ ارسال پست جدید.", exc_info=True)

    if poster_url:
        sent = await bot.send_photo(
            chat_id=config.CHANNEL_ID, photo=poster_url, caption=caption, reply_markup=markup
        )
    else:
        sent = await bot.send_message(chat_id=config.CHANNEL_ID, text=caption, reply_markup=markup)
    return sent.message_id


# ==================== ورود کاربر از طریق لینک عمیق ====================

async def handle_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str) -> None:
    parts = payload.split("_", 1)
    if len(parts) != 2 or parts[0] not in ("movie", "series") or not parts[1].isdigit():
        return

    kind, content_id_str = parts
    content_id = int(content_id_str)
    content = await get_content_by_id(content_id)
    if not content:
        await update.effective_message.reply_text(texts.MOVIE_NOT_FOUND)
        return

    if kind == "movie":
        await _start_movie_delivery(update.effective_message, content_id)
    else:
        await _start_series_delivery(update.effective_message, content_id)


async def _start_movie_delivery(message, content_id: int) -> None:
    files = await get_content_files(content_id)
    if not files:
        await message.reply_text(texts.DELIVER_NO_FILE)
        return

    if len(files) == 1:
        await _deliver_movie_file(message, content_id, files[0]["quality"])
        return

    qualities = [f["quality"] for f in files]
    await message.reply_text(
        texts.DELIVER_CHOOSE_QUALITY, reply_markup=deliver_quality_keyboard(content_id, qualities)
    )


async def _start_series_delivery(message, content_id: int) -> None:
    seasons = await get_seasons(content_id)
    seasons_with_episodes = []
    for season in seasons:
        if await count_episodes(season["id"]):
            seasons_with_episodes.append(season["season_number"])

    if not seasons_with_episodes:
        await message.reply_text(texts.DELIVER_NO_FILE)
        return

    if len(seasons_with_episodes) == 1:
        await _show_episode_list(message, content_id, seasons_with_episodes[0])
        return

    await message.reply_text(
        texts.DELIVER_CHOOSE_SEASON,
        reply_markup=deliver_season_keyboard(content_id, seasons_with_episodes),
    )


async def _show_episode_list(message, content_id: int, season_number: int) -> None:
    season = await get_season_by_number(content_id, season_number)
    if not season:
        await message.reply_text(texts.DELIVER_NO_FILE)
        return

    episodes = await get_episodes(season["id"])
    if not episodes:
        await message.reply_text(texts.DELIVER_NO_FILE)
        return

    episode_numbers = [e["episode_number"] for e in episodes]
    await message.reply_text(
        texts.DELIVER_CHOOSE_EPISODE,
        reply_markup=deliver_episode_keyboard(content_id, season_number, episode_numbers),
    )


# ==================== ارسال فایل واقعی + حذف خودکار ====================

async def _send_file(message_target, chat_id: int, file_id: str, file_type: str, caption: str, context):
    if file_type == "video":
        sent = await context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
    else:
        sent = await context.bot.send_document(chat_id=chat_id, document=file_id, caption=caption)

    schedule_deletion(context, chat_id, sent.message_id)
    await message_target.reply_text(
        texts.DELIVER_AUTO_DELETE_NOTICE.format(seconds=config.AUTO_DELETE_SECONDS)
    )


async def _deliver_movie_file(message, content_id: int, quality: str, context=None) -> None:
    files = await get_content_files(content_id)
    match = next((f for f in files if f["quality"] == quality), None)
    if not match:
        await message.reply_text(texts.DELIVER_NO_FILE)
        return
    if context is None:
        return
    await context.bot.send_message(chat_id=message.chat_id, text=texts.DELIVER_SENDING)
    await _send_file(message, message.chat_id, match["file_id"], match["file_type"], "", context)


# ==================== callback هندلرهای تحویل ====================

async def deliver_movie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        _, content_id_str, quality = query.data.split("_", 2)
    except ValueError:
        return

    content_id = int(content_id_str)
    files = await get_content_files(content_id)
    match = next((f for f in files if f["quality"] == quality), None)
    if not match:
        await query.edit_message_text(texts.DELIVER_NO_FILE)
        return

    await query.edit_message_text(texts.DELIVER_SENDING)
    await _send_file(
        query.message, query.message.chat_id, match["file_id"], match["file_type"], "", context
    )


async def deliver_season_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        _, content_id_str, season_str = query.data.split("_", 2)
    except ValueError:
        return

    content_id, season_number = int(content_id_str), int(season_str)
    season = await get_season_by_number(content_id, season_number)
    if not season:
        await query.edit_message_text(texts.DELIVER_NO_FILE)
        return

    episodes = await get_episodes(season["id"])
    if not episodes:
        await query.edit_message_text(texts.DELIVER_NO_FILE)
        return

    episode_numbers = [e["episode_number"] for e in episodes]
    await query.edit_message_text(
        texts.DELIVER_CHOOSE_EPISODE,
        reply_markup=deliver_episode_keyboard(content_id, season_number, episode_numbers),
    )


async def deliver_seasons_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    content_id = int(query.data.replace("deliverseasons_", "", 1))
    seasons = await get_seasons(content_id)
    seasons_with_episodes = []
    for season in seasons:
        if await count_episodes(season["id"]):
            seasons_with_episodes.append(season["season_number"])

    if not seasons_with_episodes:
        await query.edit_message_text(texts.DELIVER_NO_FILE)
        return

    await query.edit_message_text(
        texts.DELIVER_CHOOSE_SEASON,
        reply_markup=deliver_season_keyboard(content_id, seasons_with_episodes),
    )


async def deliver_episode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        _, content_id_str, season_str, episode_str = query.data.split("_", 3)
    except ValueError:
        return

    content_id, season_number, episode_number = int(content_id_str), int(season_str), int(episode_str)
    season = await get_season_by_number(content_id, season_number)
    if not season:
        await query.edit_message_text(texts.DELIVER_NO_FILE)
        return

    episode = await get_episode(season["id"], episode_number)
    if not episode:
        await query.edit_message_text(texts.DELIVER_NO_FILE)
        return

    await query.edit_message_text(texts.DELIVER_SENDING)
    await _send_file(
        query.message, query.message.chat_id, episode["file_id"], episode["file_type"], "", context
    )


def get_delivery_handlers() -> list:
    return [
        CallbackQueryHandler(deliver_movie_callback, pattern=r"^delivermovie_\d+_"),
        CallbackQueryHandler(deliver_season_callback, pattern=r"^deliverseason_\d+_\d+$"),
        CallbackQueryHandler(deliver_seasons_back_callback, pattern=r"^deliverseasons_\d+$"),
        CallbackQueryHandler(deliver_episode_callback, pattern=r"^deliverep_\d+_\d+_\d+$"),
    ]

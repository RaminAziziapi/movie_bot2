"""
ماژول افزودن «فیلم سینمایی» توسط ادمین.

جریان کار (کاملاً جدا از افزودن سریال - add_series.py):
۱. دریافت نام فیلم.
۲. جستجو و دریافت اطلاعات از TMDB.
۳. تولید توضیحات فارسی با Gemini.
۴. نمایش پیش‌نمایش کامل (اطلاعاتی).
۵. درخواست ارسال فایل فیلم.
۶. دریافت فایل + انتخاب کیفیت.
۷. نمایش پیش‌نمایش نهایی همراه فایل.
۸. دکمه‌های «انتشار / ویرایش / لغو».

نکته مهم: هیچ‌چیز در کانال منتشر نمی‌شود مگر با زدن دکمه «✅ انتشار» در
پیش‌نمایش نهایی؛ فقط ساخته‌شدن توضیحات یا دریافت فایل هرگز باعث انتشار
خودکار نمی‌شود.
"""
import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from channel_publish import publish_movie
from config import config
from repository import ContentAlreadyExistsError, insert_content, add_content_file
from inline import edit_fields_keyboard, preview_keyboard, quality_keyboard, results_keyboard
import gemini_service
import tmdb_service
from texts import texts

logger = logging.getLogger(__name__)

# --- states ---
ASK_QUERY, CHOOSE_RESULT, WAIT_FILE, WAIT_QUALITY, FINAL_PREVIEW, EDIT_CHOOSE_FIELD, EDIT_WAIT_VALUE = range(7)

# --- کلیدهای context.user_data (فضای نام مجزا تا با add_series.py تداخل نکند) ---
DATA_KEY = "addmovie_data"
FILE_KEY = "addmovie_file"
EDIT_FIELD_KEY = "addmovie_edit_field"

PREFIX = "movprev"
EDIT_PREFIX = "movedit"


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text(texts.NOT_ADMIN)
        return ConversationHandler.END

    context.user_data.pop(DATA_KEY, None)
    context.user_data.pop(FILE_KEY, None)
    await update.message.reply_text(texts.ASK_QUERY_MOVIE)
    return ASK_QUERY


async def receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip()
    await update.message.reply_text(texts.SEARCHING)

    try:
        raw_results = await tmdb_service.search_title(query)
    except Exception:
        logger.exception("خطا در جستجوی TMDB (فیلم)")
        await update.message.reply_text(texts.GENERIC_ERROR)
        return ASK_QUERY

    raw_results = [r for r in raw_results if r.get("media_type") == "movie"]
    if not raw_results:
        await update.message.reply_text(texts.NO_RESULTS.format(query=query))
        return ASK_QUERY

    prepared = []
    for r in raw_results[:6]:
        title = r.get("title") or r.get("name")
        date = (r.get("release_date") or "")[:4]
        label = f"{title} ({date}) - فیلم" if date else f"{title} - فیلم"
        prepared.append({"tmdb_id": r["id"], "media_type": "movie", "label": label})

    await update.message.reply_text(
        texts.CHOOSE_RESULT, reply_markup=results_keyboard(prepared, cancel_callback=f"{PREFIX}_cancel")
    )
    return CHOOSE_RESULT


async def choose_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == f"{PREFIX}_cancel":
        await query.edit_message_text(texts.CANCELLED)
        return ConversationHandler.END

    _, tmdb_id_str, media_type = query.data.split("_", 2)
    await query.edit_message_text(texts.FETCHING_DETAILS)

    try:
        details = await tmdb_service.get_details(int(tmdb_id_str), media_type)
    except Exception:
        logger.exception("خطا در دریافت جزئیات از TMDB (فیلم)")
        await query.message.reply_text(texts.GENERIC_ERROR)
        return ConversationHandler.END

    await query.message.reply_text(texts.PROCESSING_TEXT)
    gemini_result = await gemini_service.process_movie_text(details)
    details.update(gemini_result)

    context.user_data[DATA_KEY] = details
    await query.message.reply_text(texts.preview_movie(details))
    await query.message.reply_text(texts.ASK_MOVIE_FILE)
    return WAIT_FILE


async def wait_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    file_id = None
    file_type = None

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"

    if not file_id:
        await message.reply_text(texts.NO_FILE_RECEIVED)
        return WAIT_FILE

    context.user_data[FILE_KEY] = {"file_id": file_id, "file_type": file_type}
    await message.reply_text(texts.ASK_FILE_QUALITY, reply_markup=quality_keyboard("movquality"))
    return WAIT_QUALITY


async def wait_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    quality = query.data.replace("movquality_", "", 1)

    pending = context.user_data.get(FILE_KEY)
    data = context.user_data.get(DATA_KEY)
    if not pending or not data:
        await query.edit_message_text(texts.GENERIC_ERROR)
        return ConversationHandler.END

    pending["quality"] = quality
    context.user_data[FILE_KEY] = pending
    data["_file"] = True
    context.user_data[DATA_KEY] = data

    await query.edit_message_text(texts.FILE_RECEIVED_MOVIE)
    await _send_final_preview(update, context, data)
    return FINAL_PREVIEW


async def _send_final_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
    caption = texts.preview_movie(data)
    chat = update.effective_chat

    if data.get("poster_url"):
        await context.bot.send_photo(
            chat_id=chat.id,
            photo=data["poster_url"],
            caption=caption,
            reply_markup=preview_keyboard(PREFIX),
        )
    else:
        await context.bot.send_message(
            chat_id=chat.id,
            text=caption,
            reply_markup=preview_keyboard(PREFIX),
        )


async def final_preview_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    data = context.user_data.get(DATA_KEY)
    pending_file = context.user_data.get(FILE_KEY)

    if action == f"{PREFIX}_cancel":
        await query.message.reply_text(texts.CANCELLED)
        context.user_data.pop(DATA_KEY, None)
        context.user_data.pop(FILE_KEY, None)
        return ConversationHandler.END

    if action == f"{PREFIX}_research":
        context.user_data.pop(DATA_KEY, None)
        context.user_data.pop(FILE_KEY, None)
        await query.message.reply_text(texts.RESEARCH_PROMPT)
        return ASK_QUERY

    if action == f"{PREFIX}_edit":
        await query.message.reply_text(
            texts.EDIT_CHOOSE_FIELD,
            reply_markup=edit_fields_keyboard(EDIT_PREFIX, back_callback=f"{EDIT_PREFIX}_back"),
        )
        return EDIT_CHOOSE_FIELD

    if action == f"{PREFIX}_confirm":
        if not data or not pending_file:
            await query.message.reply_text(texts.GENERIC_ERROR)
            return ConversationHandler.END

        try:
            content_id = await insert_content(data, created_by=update.effective_user.id)
            await add_content_file(
                content_id, pending_file["quality"], pending_file["file_id"], pending_file["file_type"]
            )
        except ContentAlreadyExistsError:
            await query.message.reply_text(texts.ALREADY_EXISTS)
            context.user_data.pop(DATA_KEY, None)
            context.user_data.pop(FILE_KEY, None)
            return ConversationHandler.END
        except Exception:
            logger.exception("خطا در ذخیره‌سازی فیلم در دیتابیس")
            await query.message.reply_text(texts.SAVE_ERROR)
            return ConversationHandler.END

        await query.message.reply_text(texts.SAVED_SUCCESS)
        published = await publish_movie(context.bot, content_id)
        await query.message.reply_text(
            texts.PUBLISHED_TO_CHANNEL if published else texts.PUBLISH_ERROR
        )

        context.user_data.pop(DATA_KEY, None)
        context.user_data.pop(FILE_KEY, None)
        return ConversationHandler.END

    return FINAL_PREVIEW


async def edit_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == f"{EDIT_PREFIX}_back":
        data = context.user_data.get(DATA_KEY, {})
        await _send_final_preview(update, context, data)
        return FINAL_PREVIEW

    field = query.data.replace(f"{EDIT_PREFIX}_", "", 1)
    context.user_data[EDIT_FIELD_KEY] = field
    await query.message.reply_text(texts.EDIT_ASK_VALUE)
    return EDIT_WAIT_VALUE


async def edit_wait_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get(EDIT_FIELD_KEY)
    new_value = update.message.text.strip()

    data = context.user_data.get(DATA_KEY, {})
    if field:
        data[field] = new_value
    context.user_data[DATA_KEY] = data

    await update.message.reply_text(texts.EDIT_SAVED)
    await _send_final_preview(update, context, data)
    return FINAL_PREVIEW


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(DATA_KEY, None)
    context.user_data.pop(FILE_KEY, None)
    context.user_data.pop(EDIT_FIELD_KEY, None)
    await update.message.reply_text(texts.CANCELLED)
    return ConversationHandler.END


def get_add_movie_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("addmovie", entry),
            MessageHandler(filters.Regex(f"^{texts.BTN_ADD_MOVIE}$"), entry),
        ],
        states={
            ASK_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_query)],
            CHOOSE_RESULT: [
                CallbackQueryHandler(choose_result, pattern=r"^(pick_.*|movprev_cancel)$")
            ],
            WAIT_FILE: [
                MessageHandler(filters.VIDEO | filters.Document.ALL, wait_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, wait_file),
            ],
            WAIT_QUALITY: [CallbackQueryHandler(wait_quality, pattern=r"^movquality_")],
            FINAL_PREVIEW: [CallbackQueryHandler(final_preview_actions, pattern=f"^{PREFIX}_")],
            EDIT_CHOOSE_FIELD: [CallbackQueryHandler(edit_choose_field, pattern=f"^{EDIT_PREFIX}_")],
            EDIT_WAIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_wait_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="add_movie_conversation",
        persistent=False,
    )

"""
مدیریت محتوای ذخیره‌شده (📚 لیست محتوا) در پنل ادمین.

قابلیت‌ها: مشاهده‌ی همه‌ی فیلم‌ها/سریال‌ها، جستجو، صفحه‌بندی، مشاهده‌ی
جزئیات، ویرایش فیلدها، افزودن/تعویض فایل فیلم، افزودن فصل جدید به
سریال، انتشار/به‌روزرسانی در کانال، و حذف.

نکته درباره‌ی باگ قبلی «لیست فقط یک‌بار کار می‌کرد»: این پیاده‌سازی
همیشه لیست را از دیتابیس به‌صورت زنده (بر اساس صفحه/جستجوی فعلی که در
context.user_data نگه‌داری می‌شود) می‌سازد و با هر callback دوباره
واکشی می‌کند؛ هیچ داده‌ی لیست در حافظه‌ی موقت «قدیمی» نگه‌داری نمی‌شود.
"""
import logging
import math

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from admin_settings import is_admin
from channel_publish import publish_movie, publish_series
from inline import (
    content_detail_keyboard,
    content_edit_fields_keyboard,
    content_list_keyboard,
    delete_confirm_keyboard,
    quality_keyboard,
)
from keyboards import episode_collection_menu
from repository import (
    add_content_file,
    add_episode,
    count_content,
    create_season,
    delete_content,
    get_content_by_id,
    list_content,
    update_content_field,
)
from texts import texts

logger = logging.getLogger(__name__)

PAGE_SIZE = 10

# --- states ---
(
    LIST, DETAIL, EDIT_CHOOSE_FIELD, EDIT_WAIT_VALUE,
    ADD_FILE_WAIT_FILE, ADD_FILE_WAIT_QUALITY,
    ADD_SEASON_ASK_NUMBER, ADD_SEASON_COLLECT_EPISODES,
    DELETE_CONFIRM,
) = range(9)

# --- کلیدهای context.user_data ---
PAGE_KEY = "cmgmt_page"
SEARCH_KEY = "cmgmt_search"
CONTENT_ID_KEY = "cmgmt_content_id"
EDIT_FIELD_KEY = "cmgmt_edit_field"
PENDING_FILE_KEY = "cmgmt_pending_file"
SEASON_NUMBER_KEY = "cmgmt_season_number"
SEASON_EPISODES_KEY = "cmgmt_season_episodes"


def _reset(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        PAGE_KEY, SEARCH_KEY, CONTENT_ID_KEY, EDIT_FIELD_KEY,
        PENDING_FILE_KEY, SEASON_NUMBER_KEY, SEASON_EPISODES_KEY,
    ):
        context.user_data.pop(key, None)


# ==================== لیست + جستجو + صفحه‌بندی ====================

async def _render_list(context: ContextTypes.DEFAULT_TYPE, page: int):
    search = context.user_data.get(SEARCH_KEY)
    total = await count_content(search=search)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    context.user_data[PAGE_KEY] = page

    items = await list_content(limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE, search=search)
    if not items:
        return texts.MOVIE_LIST_EMPTY, None

    header = texts.MOVIE_LIST_HEADER.format(page=page, total_pages=total_pages)
    return header, content_list_keyboard([dict(i) for i in items], page, total_pages)


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(texts.NOT_ADMIN)
        return ConversationHandler.END

    _reset(context)
    text, markup = await _render_list(context, page=1)
    await update.message.reply_text(text, reply_markup=markup)
    return LIST


async def list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("clist_page_", "", 1))
    text, markup = await _render_list(context, page)
    await query.edit_message_text(text, reply_markup=markup)
    return LIST


async def search_in_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """در حالت لیست، هر متن ارسالی (به‌جز دکمه‌ها) به‌عنوان عبارت جستجو در نظر گرفته می‌شود."""
    context.user_data[SEARCH_KEY] = update.message.text.strip()
    text, markup = await _render_list(context, page=1)
    await update.message.reply_text(text, reply_markup=markup)
    return LIST


# ==================== نمایش جزئیات ====================

async def _render_detail(content_id: int):
    content = await get_content_by_id(content_id)
    if not content:
        return None, None
    content = dict(content)
    text = texts.content_detail_text(content)
    markup = content_detail_keyboard(content_id, content["published"], content["media_type"])
    return text, markup


async def show_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    content_id = int(query.data.replace("clist_item_", "", 1))
    context.user_data[CONTENT_ID_KEY] = content_id

    text, markup = await _render_detail(content_id)
    if text is None:
        await query.edit_message_text(texts.MOVIE_NOT_FOUND)
        return LIST

    await query.edit_message_text(text, reply_markup=markup)
    return DETAIL


async def _back_to_detail(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    content_id = context.user_data.get(CONTENT_ID_KEY)
    text, markup = await _render_detail(content_id)
    if text is None:
        await query.edit_message_text(texts.MOVIE_NOT_FOUND)
        return LIST
    await query.edit_message_text(text, reply_markup=markup)
    return DETAIL


# ==================== مسیریابی دکمه‌های جزئیات ====================

async def detail_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    content_id = context.user_data.get(CONTENT_ID_KEY)

    if data.startswith("cdetail_edit_"):
        await query.edit_message_text(
            texts.EDIT_CHOOSE_FIELD, reply_markup=content_edit_fields_keyboard(content_id)
        )
        return EDIT_CHOOSE_FIELD

    if data.startswith("cdetail_addfile_"):
        await query.edit_message_text(texts.ASK_MOVIE_FILE)
        return ADD_FILE_WAIT_FILE

    if data.startswith("cdetail_addseason_"):
        await query.message.reply_text(texts.ASK_SEASON_NUMBER)
        return ADD_SEASON_ASK_NUMBER

    if data.startswith("cdetail_publish_"):
        content = await get_content_by_id(content_id)
        if not content:
            await query.edit_message_text(texts.MOVIE_NOT_FOUND)
            return LIST

        content = dict(content)
        if content["media_type"] == "movie":
            published = await publish_movie(query.bot, content_id)
        else:
            published = await publish_series(query.bot, content_id)

        await query.message.reply_text(
            texts.PUBLISHED_TO_CHANNEL if published else texts.PUBLISH_ERROR
        )
        return await _back_to_detail(query, context)

    if data.startswith("cdetail_delete_"):
        content = await get_content_by_id(content_id)
        title = (content["persian_title"] or content["title"]) if content else ""
        await query.edit_message_text(
            texts.DELETE_CONFIRM.format(title=title), reply_markup=delete_confirm_keyboard()
        )
        return DELETE_CONFIRM

    return await _back_to_detail(query, context)


# ==================== ویرایش فیلد ====================

async def edit_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("clist_item_"):
        return await show_detail(update, context)

    field = query.data.replace("cedit_", "", 1)
    context.user_data[EDIT_FIELD_KEY] = field
    await query.edit_message_text(texts.EDIT_ASK_VALUE)
    return EDIT_WAIT_VALUE


async def edit_wait_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get(EDIT_FIELD_KEY)
    content_id = context.user_data.get(CONTENT_ID_KEY)
    new_value = update.message.text.strip()

    try:
        await update_content_field(content_id, field, new_value)
        await update.message.reply_text(texts.EDIT_UPDATED)
    except ValueError:
        await update.message.reply_text(texts.EDIT_INVALID_NUMBER)
        return EDIT_WAIT_VALUE
    except Exception:
        logger.exception("خطا در ویرایش فیلد محتوا")
        await update.message.reply_text(texts.GENERIC_ERROR)

    text, markup = await _render_detail(content_id)
    if text is None:
        await update.message.reply_text(texts.MOVIE_NOT_FOUND)
        return LIST
    await update.message.reply_text(text, reply_markup=markup)
    return DETAIL


# ==================== افزودن/تعویض فایل فیلم ====================

async def add_file_wait_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    file_id, file_type = None, None
    if message.video:
        file_id, file_type = message.video.file_id, "video"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"

    if not file_id:
        await message.reply_text(texts.NO_FILE_RECEIVED)
        return ADD_FILE_WAIT_FILE

    context.user_data[PENDING_FILE_KEY] = {"file_id": file_id, "file_type": file_type}
    await message.reply_text(texts.ASK_FILE_QUALITY, reply_markup=quality_keyboard("cmgmtquality"))
    return ADD_FILE_WAIT_QUALITY


async def add_file_wait_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    quality = query.data.replace("cmgmtquality_", "", 1)

    pending = context.user_data.get(PENDING_FILE_KEY)
    content_id = context.user_data.get(CONTENT_ID_KEY)
    if not pending or not content_id:
        await query.edit_message_text(texts.GENERIC_ERROR)
        return ConversationHandler.END

    try:
        await add_content_file(content_id, quality, pending["file_id"], pending["file_type"])
        await query.edit_message_text(texts.FILE_SAVED.format(quality=quality))
    except Exception:
        logger.exception("خطا در ذخیره فایل فیلم")
        await query.edit_message_text(texts.SAVE_ERROR)

    context.user_data.pop(PENDING_FILE_KEY, None)
    text, markup = await _render_detail(content_id)
    if text is None:
        await query.message.reply_text(texts.MOVIE_NOT_FOUND)
        return LIST
    await query.message.reply_text(text, reply_markup=markup)
    return DETAIL


# ==================== افزودن فصل جدید به سریال ====================

async def add_season_ask_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text(texts.INVALID_SEASON_NUMBER)
        return ADD_SEASON_ASK_NUMBER

    season_number = int(raw)
    context.user_data[SEASON_NUMBER_KEY] = season_number
    context.user_data[SEASON_EPISODES_KEY] = []

    await update.message.reply_text(
        texts.ASK_EPISODES.format(season=season_number), reply_markup=episode_collection_menu()
    )
    return ADD_SEASON_COLLECT_EPISODES


async def add_season_collect_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    file_id, file_type = None, None
    if message.video:
        file_id, file_type = message.video.file_id, "video"
    elif message.document:
        file_id, file_type = message.document.file_id, "document"

    if not file_id:
        await message.reply_text(texts.NO_FILE_RECEIVED)
        return ADD_SEASON_COLLECT_EPISODES

    episodes = context.user_data.setdefault(SEASON_EPISODES_KEY, [])
    episodes.append({"file_id": file_id, "file_type": file_type})

    season_number = context.user_data.get(SEASON_NUMBER_KEY)
    await message.reply_text(texts.EPISODE_SAVED.format(episode=len(episodes), season=season_number))
    return ADD_SEASON_COLLECT_EPISODES


async def add_season_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from telegram import ReplyKeyboardRemove

    content_id = context.user_data.get(CONTENT_ID_KEY)
    season_number = context.user_data.get(SEASON_NUMBER_KEY)
    episodes = context.user_data.get(SEASON_EPISODES_KEY, [])

    if not episodes:
        await update.message.reply_text(texts.NO_EPISODES_YET)
        return ADD_SEASON_COLLECT_EPISODES

    try:
        season_id = await create_season(content_id, season_number)
        # قسمت‌های جدید همیشه از شماره ۱ به بعد برای این فصل خاص شماره‌گذاری می‌شوند
        for index, episode in enumerate(episodes, start=1):
            await add_episode(season_id, index, episode["file_id"], episode["file_type"])
    except Exception:
        logger.exception("خطا در ذخیره فصل جدید")
        await update.message.reply_text(texts.SAVE_ERROR, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    await update.message.reply_text(
        texts.SEASON_DONE.format(season=season_number, count=len(episodes)),
        reply_markup=ReplyKeyboardRemove(),
    )

    context.user_data.pop(SEASON_NUMBER_KEY, None)
    context.user_data.pop(SEASON_EPISODES_KEY, None)

    text, markup = await _render_detail(content_id)
    if text is None:
        await update.message.reply_text(texts.MOVIE_NOT_FOUND)
        return LIST
    await update.message.reply_text(text, reply_markup=markup)
    return DETAIL


# ==================== حذف محتوا ====================

async def delete_confirm_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    content_id = context.user_data.get(CONTENT_ID_KEY)

    if query.data == "cdelete_cancel":
        await query.message.reply_text(texts.DELETE_CANCELLED)
        return await _back_to_detail(query, context)

    try:
        await delete_content(content_id)
        await query.edit_message_text(texts.DELETE_DONE)
    except Exception:
        logger.exception("خطا در حذف محتوا")
        await query.edit_message_text(texts.GENERIC_ERROR)

    text, markup = await _render_list(context, page=1)
    await query.message.reply_text(text, reply_markup=markup)
    return LIST


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _reset(context)
    await update.message.reply_text(texts.CANCELLED)
    return ConversationHandler.END


def get_movie_management_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{texts.BTN_MOVIE_LIST}$"), entry)],
        states={
            LIST: [
                CallbackQueryHandler(list_page_callback, pattern=r"^clist_page_"),
                CallbackQueryHandler(show_detail, pattern=r"^clist_item_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_in_list),
            ],
            DETAIL: [CallbackQueryHandler(detail_router, pattern=r"^cdetail_")],
            EDIT_CHOOSE_FIELD: [
                CallbackQueryHandler(edit_choose_field, pattern=r"^(cedit_|clist_item_)")
            ],
            EDIT_WAIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_wait_value)],
            ADD_FILE_WAIT_FILE: [
                MessageHandler(filters.VIDEO | filters.Document.ALL, add_file_wait_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_wait_file),
            ],
            ADD_FILE_WAIT_QUALITY: [
                CallbackQueryHandler(add_file_wait_quality, pattern=r"^cmgmtquality_")
            ],
            ADD_SEASON_ASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_season_ask_number)
            ],
            ADD_SEASON_COLLECT_EPISODES: [
                MessageHandler(filters.Regex(f"^{texts.SEASON_FINISHED_BUTTON}$"), add_season_finish),
                MessageHandler(filters.VIDEO | filters.Document.ALL, add_season_collect_episodes),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_season_collect_episodes),
            ],
            DELETE_CONFIRM: [CallbackQueryHandler(delete_confirm_router, pattern=r"^cdelete_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="movie_management_conversation",
        persistent=False,
    )

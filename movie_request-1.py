"""
درخواست فیلم/سریال توسط کاربران عادی + مرور درخواست‌ها توسط ادمین.
"""
import logging
import math

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from admin_settings import get_all_admin_ids, is_admin
from force_join import require_join
from repository import (
    count_pending_requests,
    create_movie_request,
    list_pending_requests,
    mark_request_done,
)
from texts import texts

logger = logging.getLogger(__name__)

WAIT_REQUEST_TEXT = 1
PAGE_SIZE = 10


# ==================== کاربر: ثبت درخواست ====================

async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await require_join(update, context):
        return ConversationHandler.END
    await update.message.reply_text(texts.ASK_REQUEST_TEXT)
    return WAIT_REQUEST_TEXT


async def receive_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query_text = update.message.text.strip()
    user_id = update.effective_user.id

    try:
        await create_movie_request(user_id, query_text)
    except Exception:
        logger.exception("خطا در ثبت درخواست فیلم/سریال")
        await update.message.reply_text(texts.GENERIC_ERROR)
        return ConversationHandler.END

    await update.message.reply_text(texts.REQUEST_SAVED)

    try:
        admin_ids = await get_all_admin_ids()
    except Exception:
        admin_ids = []

    notice = texts.NEW_REQUEST_ADMIN_NOTICE.format(user_id=user_id, text=query_text)
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(chat_id=admin_id, text=notice)
        except Exception:
            logger.debug("اطلاع‌رسانی درخواست جدید به ادمین %s ناموفق بود.", admin_id, exc_info=True)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(texts.CANCELLED)
    return ConversationHandler.END


def get_movie_request_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{texts.BTN_REQUEST_MOVIE}$"), entry)],
        states={
            WAIT_REQUEST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_request)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="movie_request_conversation",
        persistent=False,
    )


# ==================== ادمین: مرور درخواست‌ها ====================

def _requests_keyboard(items, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"✅ انجام‌شد: {item['query_text'][:30]}", callback_data=f"reqdone_{item['id']}")]
        for item in items
    ]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"reqpage_{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"reqpage_{page + 1}"))
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


async def _render_page(page: int):
    total = await count_pending_requests()
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    items = await list_pending_requests(limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)

    if not items:
        return texts.REQUEST_LIST_EMPTY, None

    header = texts.REQUEST_LIST_HEADER.format(page=page, total_pages=total_pages)
    lines = [header]
    for item in items:
        lines.append(f"• #{item['id']} از {item['user_id']}: {item['query_text']}")

    return "\n".join(lines), _requests_keyboard(items, page, total_pages)


async def admin_requests_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(texts.NOT_ADMIN)
        return

    text, markup = await _render_page(1)
    await update.message.reply_text(text, reply_markup=markup)


async def admin_requests_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("reqpage_", "", 1))
    text, markup = await _render_page(page)
    await query.edit_message_text(text, reply_markup=markup)


async def admin_request_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    request_id = int(query.data.replace("reqdone_", "", 1))

    try:
        await mark_request_done(request_id)
    except Exception:
        logger.exception("خطا در علامت‌گذاری درخواست به‌عنوان انجام‌شده")

    text, markup = await _render_page(1)
    await query.edit_message_text(text, reply_markup=markup)


def get_movie_request_admin_handlers() -> list:
    return [
        MessageHandler(filters.Regex(f"^{texts.BTN_MOVIE_REQUESTS}$"), admin_requests_entry),
        CallbackQueryHandler(admin_requests_page, pattern=r"^reqpage_\d+$"),
        CallbackQueryHandler(admin_request_done, pattern=r"^reqdone_\d+$"),
    ]

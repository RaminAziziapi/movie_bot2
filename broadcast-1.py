"""
ارسال همگانی (Broadcast) پیام ادمین به تمام کاربران ثبت‌شده در دیتابیس.

هر نوع پیامی (متن، عکس، ویدیو، سند و ...) با copy_message برای هر کاربر
کپی می‌شود تا فرمت اصلی پیام حفظ شود. خطا در ارسال به یک کاربر (مثلاً
بلاک‌کردن ربات) نباید ارسال به بقیه‌ی کاربران را متوقف کند.
"""
import asyncio
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

from admin_settings import is_admin
from inline import broadcast_confirm_keyboard
from repository import count_users, get_all_user_ids
from texts import texts

logger = logging.getLogger(__name__)

WAIT_MESSAGE, CONFIRM = range(2)

MESSAGE_KEY = "bcast_source_message"


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(texts.NOT_ADMIN)
        return ConversationHandler.END

    context.user_data.pop(MESSAGE_KEY, None)
    await update.message.reply_text(texts.ASK_BROADCAST_MESSAGE)
    return WAIT_MESSAGE


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    context.user_data[MESSAGE_KEY] = {"chat_id": message.chat_id, "message_id": message.message_id}

    try:
        total_users = await count_users()
    except Exception:
        logger.exception("خطا در شمارش کاربران")
        total_users = 0

    await message.reply_text(
        texts.BROADCAST_CONFIRM.format(count=total_users), reply_markup=broadcast_confirm_keyboard()
    )
    return CONFIRM


async def confirm_or_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "bcast_cancel":
        context.user_data.pop(MESSAGE_KEY, None)
        await query.edit_message_text(texts.BROADCAST_CANCELLED)
        return ConversationHandler.END

    source = context.user_data.get(MESSAGE_KEY)
    if not source:
        await query.edit_message_text(texts.GENERIC_ERROR)
        return ConversationHandler.END

    await query.edit_message_text(texts.BROADCAST_SENDING)

    try:
        user_ids = await get_all_user_ids()
    except Exception:
        logger.exception("خطا در دریافت لیست کاربران برای ارسال همگانی")
        await query.message.reply_text(texts.GENERIC_ERROR)
        return ConversationHandler.END

    success, failed = 0, 0
    for user_id in user_ids:
        try:
            await context.bot.copy_message(
                chat_id=user_id, from_chat_id=source["chat_id"], message_id=source["message_id"]
            )
            success += 1
        except Exception:
            failed += 1
            logger.debug("ارسال همگانی به کاربر %s ناموفق بود.", user_id, exc_info=True)
        await asyncio.sleep(0.05)

    context.user_data.pop(MESSAGE_KEY, None)
    await query.message.reply_text(texts.BROADCAST_DONE.format(success=success, failed=failed))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(MESSAGE_KEY, None)
    await update.message.reply_text(texts.CANCELLED)
    return ConversationHandler.END


def get_broadcast_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{texts.BTN_BROADCAST}$"), entry)],
        states={
            WAIT_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_message)],
            CONFIRM: [CallbackQueryHandler(confirm_or_cancel, pattern=r"^bcast_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="broadcast_conversation",
        persistent=False,
    )

import asyncio

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
import keyboards as kb
import utils
from start_handlers import back_to_panel

BROADCAST_CONTENT, BROADCAST_CONFIRM = range(60, 62)


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_broadcast(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "📢 پیام همگانی\n\n"
        "پیامی که می‌خواهید برای همه کاربران ارسال شود را بفرستید.\n"
        "می‌تواند متن، عکس، ویدیو، فایل، پیام فوروارد شده یا پیام دارای دکمه باشد.",
        reply_markup=kb.back_keyboard("back_to_panel"),
    )
    return BROADCAST_CONTENT


async def broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_broadcast(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["broadcast_chat_id"] = update.effective_chat.id
    context.user_data["broadcast_message_id"] = update.message.message_id

    await update.message.reply_text(
        "این پیام برای همه کاربران ارسال شود؟",
        reply_markup=kb.confirm_keyboard("broadcast_confirm", "back_to_panel"),
    )
    return BROADCAST_CONFIRM


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_broadcast(query.from_user.id):
        return ConversationHandler.END

    from_chat_id = context.user_data.get("broadcast_chat_id")
    message_id = context.user_data.get("broadcast_message_id")

    if not from_chat_id or not message_id:
        await query.edit_message_text("❗️ پیامی برای ارسال پیدا نشد.", reply_markup=kb.back_keyboard())
        return ConversationHandler.END

    await query.edit_message_text("⏳ در حال ارسال پیام همگانی... این ممکن است چند دقیقه طول بکشد.")

    user_ids = db.get_all_user_ids()
    success = 0
    failed = 0

    for uid in user_ids:
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=from_chat_id, message_id=message_id)
            success += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(0.05)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "✅ ارسال پیام همگانی تمام شد.\n\n"
            f"👥 کل کاربران: {len(user_ids)}\n"
            f"✅ موفق: {success}\n"
            f"❌ ناموفق: {failed}"
        ),
        reply_markup=kb.back_keyboard(),
    )

    context.user_data.pop("broadcast_chat_id", None)
    context.user_data.pop("broadcast_message_id", None)
    return ConversationHandler.END


broadcast_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(broadcast_start, pattern="^broadcast_start$")],
    states={
        BROADCAST_CONTENT: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_receive)],
        BROADCAST_CONFIRM: [CallbackQueryHandler(broadcast_confirm, pattern="^broadcast_confirm$")],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)
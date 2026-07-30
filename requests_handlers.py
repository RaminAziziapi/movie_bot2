from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
from config import OWNER_ID
from start_handlers import back_to_panel

REQUEST_TEXT = 70


async def request_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📩 نام فیلم یا سریالی که می‌خواهید درخواست دهید را بنویسید:",
    )
    return REQUEST_TEXT


async def request_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    content = update.message.text.strip()

    request_id = db.add_request(user.id, user.username, content)

    await update.message.reply_text("✅ درخواست شما ثبت شد. به محض اضافه شدن، به شما اطلاع داده می‌شود.")

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"📩 درخواست جدید (#{request_id})\nاز: {user.id} (@{user.username})\nمتن: {content}",
        )
    except Exception:
        pass

    return ConversationHandler.END


request_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(request_start, pattern="^request_start$")],
    states={
        REQUEST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_receive)],
    },
    fallbacks=[CommandHandler("cancel", back_to_panel)],
    per_message=False,
)


# ---------------------- مدیریت درخواست‌ها توسط ادمین ----------------------

async def requests_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_handle_requests(query.from_user.id):
        return

    pending = db.get_pending_requests()
    if not pending:
        await query.edit_message_text("📝 هیچ درخواست در انتظاری وجود ندارد.", reply_markup=kb.back_keyboard())
        return

    text = "📝 درخواست‌های در انتظار:\n\n"
    keyboard_rows = []
    for r in pending:
        req_id, user_id, username, content = r[0], r[1], r[2], r[3]
        uname = f"@{username}" if username else str(user_id)
        text += f"#{req_id} از {uname}: {content}\n"
        keyboard_rows.append(
            [InlineKeyboardButton(f"✅ انجام شد (#{req_id})", callback_data=f"fulfill_request_{req_id}")]
        )
    keyboard_rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_panel")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard_rows))


async def fulfill_request_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_handle_requests(query.from_user.id):
        return

    request_id = int(query.data.replace("fulfill_request_", ""))
    user_id = db.fulfill_request(request_id)

    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 درخواست شما اضافه شد! می‌توانید از داخل ربات آن را جستجو کنید.",
            )
        except Exception:
            pass

    await requests_list(update, context)
from telegram import Update
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
from config import OWNER_ID, ROLE_LABELS
from start_handlers import back_to_panel

ADD_ADMIN_ID, ADD_ADMIN_ROLE = range(50, 52)
REMOVE_ADMIN_ID = 52


async def menu_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_admins(query.from_user.id):
        return
    await query.edit_message_text("🛡 مدیریت مدیران", reply_markup=kb.admins_menu_keyboard())


# ---------------------- افزودن مدیر ----------------------

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_admins(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "➕ آیدی عددی کاربری که می‌خواهید مدیر کنید را ارسال کنید.\n"
        "(کاربر باید قبلاً حداقل یک‌بار /start ربات را زده باشد. برای گرفتن آیدی عددی می‌توانید از ربات @userinfobot کمک بگیرید.)",
        reply_markup=kb.back_keyboard("menu_admins"),
    )
    return ADD_ADMIN_ID


async def add_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_admins(update.effective_user.id):
        return ConversationHandler.END

    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "❗️ آیدی باید فقط عدد باشد. دوباره ارسال کنید:",
            reply_markup=kb.back_keyboard("menu_admins"),
        )
        return ADD_ADMIN_ID

    context.user_data["new_admin_id"] = int(text)
    await update.message.reply_text("سطح دسترسی را انتخاب کنید:", reply_markup=kb.role_select_keyboard())
    return ADD_ADMIN_ROLE


async def add_admin_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_admins(query.from_user.id):
        return ConversationHandler.END

    role = query.data.replace("role_", "")
    new_admin_id = context.user_data.get("new_admin_id")

    if not new_admin_id:
        await query.edit_message_text("❗️ خطایی رخ داد، دوباره تلاش کنید.", reply_markup=kb.back_keyboard("menu_admins"))
        return ConversationHandler.END

    db.add_admin(new_admin_id, None, role, query.from_user.id)

    await query.edit_message_text(
        f"✅ کاربر {new_admin_id} با سطح دسترسی «{ROLE_LABELS.get(role, role)}» اضافه شد.",
        reply_markup=kb.back_keyboard("menu_admins"),
    )

    try:
        await context.bot.send_message(
            chat_id=new_admin_id,
            text=f"🎉 شما به عنوان «{ROLE_LABELS.get(role, role)}» به تیم مدیریت ربات اضافه شدید.\nبرای دسترسی به پنل از دستور /admin استفاده کنید.",
        )
    except Exception:
        pass

    context.user_data.pop("new_admin_id", None)
    return ConversationHandler.END


add_admin_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_admin_start, pattern="^add_admin$")],
    states={
        ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_id)],
        ADD_ADMIN_ROLE: [CallbackQueryHandler(add_admin_role, pattern="^role_(admin|uploader|support)$")],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_admins, pattern="^menu_admins$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- حذف مدیر ----------------------

async def remove_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_admins(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "➖ آیدی عددی مدیری که می‌خواهید حذف کنید را ارسال کنید:",
        reply_markup=kb.back_keyboard("menu_admins"),
    )
    return REMOVE_ADMIN_ID


async def remove_admin_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_admins(update.effective_user.id):
        return ConversationHandler.END

    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❗️ آیدی باید فقط عدد باشد.", reply_markup=kb.back_keyboard("menu_admins"))
        return REMOVE_ADMIN_ID

    admin_id = int(text)
    if admin_id == OWNER_ID:
        await update.message.reply_text("❗️ مالک ربات قابل حذف نیست.", reply_markup=kb.back_keyboard("menu_admins"))
        return ConversationHandler.END

    db.remove_admin(admin_id)
    await update.message.reply_text(f"✅ کاربر {admin_id} از لیست مدیران حذف شد.", reply_markup=kb.back_keyboard("menu_admins"))
    return ConversationHandler.END


remove_admin_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(remove_admin_start, pattern="^remove_admin$")],
    states={
        REMOVE_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_admin_finish)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_admins, pattern="^menu_admins$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_admins(query.from_user.id):
        return

    admins = db.get_admins()
    text = f"👑 مالک: {OWNER_ID}\n\n"
    if not admins:
        text += "هیچ مدیر دیگری ثبت نشده است."
    else:
        text += "📋 لیست مدیران:\n\n"
        for a in admins:
            user_id, username, role = a[0], a[1], a[2]
            uname = f"@{username}" if username else str(user_id)
            text += f"🆔 {user_id} | {uname} | {ROLE_LABELS.get(role, role)}\n"

    await query.edit_message_text(text, reply_markup=kb.back_keyboard("menu_admins"))
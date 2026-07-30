import json

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
from start_handlers import back_to_panel

ADD_CHANNEL_INPUT, REMOVE_CHANNEL_INPUT = 20, 30
SETTING_START_TEXT, SETTING_RULES_TEXT, SETTING_SUPPORT_LINK = range(80, 83)
RESTORE_UPLOAD = 90


async def menu_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return
    await query.edit_message_text("⚙️ تنظیمات", reply_markup=kb.settings_menu_keyboard())


# ---------------------- کانال‌های اجباری (بدون تغییر در رفتار) ----------------------

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return
    await query.edit_message_text("📢 مدیریت کانال‌های اجباری", reply_markup=kb.channels_menu_keyboard())


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return

    channels = db.get_channels()
    if not channels:
        text = "📋 هیچ کانالی ثبت نشده است."
    else:
        text = "📋 لیست کانال‌های اجباری:\n\n" + "\n".join(f"• {ch}" for ch in channels)

    await query.edit_message_text(text, reply_markup=kb.channels_menu_keyboard())


async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "➕ آیدی یا یوزرنیم کانال را ارسال کنید (مثال: @mychannel):",
        reply_markup=kb.back_keyboard("menu_settings"),
    )
    return ADD_CHANNEL_INPUT


async def add_channel_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_settings(update.effective_user.id):
        return ConversationHandler.END

    channel = update.message.text.strip()
    db.add_channel(channel)
    await update.message.reply_text(f"✅ کانال {channel} با موفقیت اضافه شد.", reply_markup=kb.channels_menu_keyboard())
    return ConversationHandler.END


add_channel_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_channel_start, pattern="^add_channel$")],
    states={ADD_CHANNEL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_channel_finish)]},
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(manage_channels, pattern="^manage_channels$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


async def remove_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "➖ آیدی یا یوزرنیم کانالی که می‌خواهید حذف کنید را ارسال کنید:",
        reply_markup=kb.back_keyboard("menu_settings"),
    )
    return REMOVE_CHANNEL_INPUT


async def remove_channel_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_settings(update.effective_user.id):
        return ConversationHandler.END

    channel = update.message.text.strip()
    db.remove_channel(channel)
    await update.message.reply_text(f"✅ کانال {channel} با موفقیت حذف شد.", reply_markup=kb.channels_menu_keyboard())
    return ConversationHandler.END


remove_channel_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(remove_channel_start, pattern="^remove_channel$")],
    states={REMOVE_CHANNEL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_channel_finish)]},
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(manage_channels, pattern="^manage_channels$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- متن‌های قابل تنظیم ----------------------

async def setting_start_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return ConversationHandler.END
    await query.edit_message_text("✏️ متن جدید پیام استارت را ارسال کنید:", reply_markup=kb.back_keyboard("menu_settings"))
    return SETTING_START_TEXT


async def setting_start_text_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_settings(update.effective_user.id):
        return ConversationHandler.END
    db.set_setting("start_text", update.message.text)
    await update.message.reply_text("✅ متن استارت آپدیت شد.", reply_markup=kb.settings_menu_keyboard())
    return ConversationHandler.END


setting_start_text_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(setting_start_text_start, pattern="^setting_start_text$")],
    states={SETTING_START_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, setting_start_text_save)]},
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_settings, pattern="^menu_settings$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


async def setting_rules_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return ConversationHandler.END
    await query.edit_message_text("📜 متن جدید قوانین را ارسال کنید:", reply_markup=kb.back_keyboard("menu_settings"))
    return SETTING_RULES_TEXT


async def setting_rules_text_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_settings(update.effective_user.id):
        return ConversationHandler.END
    db.set_setting("rules_text", update.message.text)
    await update.message.reply_text("✅ متن قوانین آپدیت شد.", reply_markup=kb.settings_menu_keyboard())
    return ConversationHandler.END


setting_rules_text_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(setting_rules_text_start, pattern="^setting_rules_text$")],
    states={SETTING_RULES_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, setting_rules_text_save)]},
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_settings, pattern="^menu_settings$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


async def setting_support_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return ConversationHandler.END
    await query.edit_message_text("🆘 لینک یا آیدی پشتیبانی جدید را ارسال کنید:", reply_markup=kb.back_keyboard("menu_settings"))
    return SETTING_SUPPORT_LINK


async def setting_support_link_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_settings(update.effective_user.id):
        return ConversationHandler.END
    db.set_setting("support_link", update.message.text.strip())
    await update.message.reply_text("✅ لینک پشتیبانی آپدیت شد.", reply_markup=kb.settings_menu_keyboard())
    return ConversationHandler.END


setting_support_link_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(setting_support_link_start, pattern="^setting_support_link$")],
    states={SETTING_SUPPORT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, setting_support_link_save)]},
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_settings, pattern="^menu_settings$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- بکاپ / ریستور ----------------------

async def settings_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return

    data = db.export_backup()
    json_bytes = json.dumps(data, default=str, ensure_ascii=False, indent=2).encode("utf-8")

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=json_bytes,
        filename="backup.json",
        caption="💾 فایل بکاپ محتوای ربات (فیلم‌ها، سریال‌ها، قسمت‌ها، کانال‌ها)",
    )


async def settings_restore_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_settings(query.from_user.id):
        return ConversationHandler.END
    await query.edit_message_text(
        "♻️ فایل بکاپ (JSON) را ارسال کنید.\n"
        "⚠️ توجه: این کار محتوای فایل رو به‌عنوان رکورد جدید اضافه می‌کنه، چیزی رو پاک نمی‌کنه.",
        reply_markup=kb.back_keyboard("menu_settings"),
    )
    return RESTORE_UPLOAD


async def settings_restore_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_settings(update.effective_user.id):
        return ConversationHandler.END

    if not update.message.document:
        await update.message.reply_text("❗️ لطفاً فایل JSON بکاپ را ارسال کنید.", reply_markup=kb.back_keyboard("menu_settings"))
        return RESTORE_UPLOAD

    try:
        file = await update.message.document.get_file()
        file_bytes = await file.download_as_bytearray()
        data = json.loads(file_bytes.decode("utf-8"))
        db.restore_backup(data)
    except Exception as exc:
        await update.message.reply_text(f"❗️ خطا در پردازش فایل: {exc}", reply_markup=kb.back_keyboard("menu_settings"))
        return ConversationHandler.END

    await update.message.reply_text("✅ بازیابی اطلاعات با موفقیت انجام شد.", reply_markup=kb.settings_menu_keyboard())
    return ConversationHandler.END


settings_restore_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(settings_restore_start, pattern="^settings_restore$")],
    states={RESTORE_UPLOAD: [MessageHandler(filters.Document.ALL, settings_restore_receive)]},
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_settings, pattern="^menu_settings$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)
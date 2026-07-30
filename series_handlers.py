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
from start_handlers import back_to_panel

ADD_SERIES_NAME, ADD_SERIES_SEASON, RECEIVE_EPISODES = range(40, 43)
DELETE_SERIES_ID = 43

FINISH_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("✅ پایان دریافت قسمت‌ها", callback_data="finish_series")]]
)


async def menu_series(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return
    await query.edit_message_text("📺 مدیریت سریال", reply_markup=kb.series_menu_keyboard())


# ---------------------- افزودن سریال ----------------------

async def add_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "📺 نام سریال را وارد کنید:",
        reply_markup=kb.back_keyboard("menu_series"),
    )
    return ADD_SERIES_NAME


async def add_series_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["new_series_name"] = update.message.text.strip()
    await update.message.reply_text("📁 شماره یا نام فصل را وارد کنید:")
    return ADD_SERIES_SEASON


async def add_series_season(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    season = update.message.text.strip()
    name = context.user_data.get("new_series_name")
    user_id = update.effective_user.id

    series_id = db.add_series(name, season, user_id)
    context.user_data["current_series_id"] = series_id

    await update.message.reply_text(
        f"✅ سریال «{name}» (فصل {season}) ساخته شد.\n\n"
        "🎞 حالا فایل‌های ویدیویی قسمت‌ها را یکی‌یکی و به‌ترتیب ارسال کنید.\n"
        "شماره هر قسمت خودکار محاسبه می‌شود.\n"
        "وقتی تمام قسمت‌ها را فرستادید، دکمه پایین را بزنید.",
        reply_markup=FINISH_BUTTON,
    )
    return RECEIVE_EPISODES


async def receive_episode_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    series_id = context.user_data.get("current_series_id")
    if not series_id or not update.message or not update.message.video:
        await update.message.reply_text("❗️ لطفاً یک فایل ویدیویی ارسال کنید.", reply_markup=FINISH_BUTTON)
        return RECEIVE_EPISODES

    episode_number = db.get_next_episode_number(series_id)
    db.add_episode(series_id, episode_number, update.message.video.file_id)

    await update.message.reply_text(
        f"✅ قسمت {episode_number:02d} دریافت و ذخیره شد.",
        reply_markup=FINISH_BUTTON,
    )
    return RECEIVE_EPISODES


async def finish_series(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    series_id = context.user_data.get("current_series_id")
    if not series_id:
        await query.edit_message_text("❗️ سریال فعالی برای پایان دادن پیدا نشد.", reply_markup=kb.back_keyboard("menu_series"))
        return ConversationHandler.END

    series = db.get_series(series_id)
    episodes = db.get_episodes(series_id)

    if not episodes:
        await query.edit_message_text(
            "❗️ هیچ قسمتی برای این سریال ثبت نشد. سریال حذف می‌شود.",
            reply_markup=kb.back_keyboard("menu_series"),
        )
        db.delete_series(series_id)
        context.user_data.pop("current_series_id", None)
        return ConversationHandler.END

    bot_username = (await context.bot.get_me()).username
    name, season = series[1], series[2]

    result_text = f"🎬 {name}\n📺 فصل {season}\n"
    keyboard_rows = []
    for ep in episodes:
        ep_number, code = ep[1], ep[3]
        link = f"https://t.me/{bot_username}?start=episode_{code}"
        keyboard_rows.append([InlineKeyboardButton(f"🟣 قسمت {ep_number:02d}", url=link)])

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=result_text,
        reply_markup=InlineKeyboardMarkup(keyboard_rows),
    )
    await query.edit_message_text(
        f"✅ سریال «{name}» با {len(episodes)} قسمت با موفقیت ثبت شد.\n"
        "پیام بالا رو می‌تونید توی کانالتون فوروارد یا کپی کنید.",
        reply_markup=kb.back_keyboard("menu_series"),
    )

    context.user_data.pop("current_series_id", None)
    return ConversationHandler.END


add_series_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_series_start, pattern="^add_series$")],
    states={
        ADD_SERIES_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_series_name)],
        ADD_SERIES_SEASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_series_season)],
        RECEIVE_EPISODES: [
            MessageHandler(filters.VIDEO, receive_episode_video),
            CallbackQueryHandler(finish_series, pattern="^finish_series$"),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_series, pattern="^menu_series$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- لیست و حذف سریال ----------------------

async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return

    series_list = db.get_series_list()
    if not series_list:
        await query.edit_message_text("📂 هیچ سریالی ثبت نشده است.", reply_markup=kb.back_keyboard("menu_series"))
        return

    text = "📂 لیست سریال‌ها:\n\n"
    for s in series_list:
        series_id, name, season = s[0], s[1], s[2]
        episodes_count = len(db.get_episodes(series_id))
        text += f"🆔 {series_id} | 📺 {name} | فصل {season} | {episodes_count} قسمت\n"

    await query.edit_message_text(text, reply_markup=kb.back_keyboard("menu_series"))


async def delete_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "🗑 شناسه (ID) سریالی که می‌خواهید حذف کنید را ارسال کنید:",
        reply_markup=kb.back_keyboard("menu_series"),
    )
    return DELETE_SERIES_ID


async def delete_series_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    series_id = update.message.text.strip()
    series = db.get_series(series_id)

    if not series:
        await update.message.reply_text(
            "❗️ سریالی با این شناسه پیدا نشد. دوباره شناسه را ارسال کنید یا بازگردید.",
            reply_markup=kb.back_keyboard("menu_series"),
        )
        return DELETE_SERIES_ID

    db.delete_series(series_id)
    await update.message.reply_text(
        f"✅ سریال با شناسه {series_id} (و تمام قسمت‌هایش) حذف شد.",
        reply_markup=kb.back_keyboard("menu_series"),
    )
    return ConversationHandler.END


delete_series_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(delete_series_start, pattern="^delete_series$")],
    states={
        DELETE_SERIES_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_series_confirm)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_series, pattern="^menu_series$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)
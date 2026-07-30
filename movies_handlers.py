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
from start_handlers import back_to_panel, send_panel

ADD_MOVIE_VIDEO, ADD_MOVIE_NAME, ADD_MOVIE_SEASON, ADD_MOVIE_EPISODE = range(4)
DELETE_MOVIE_ID = 10


async def menu_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text("🎬 مدیریت فیلم", reply_markup=kb.movies_menu_keyboard())
    return ConversationHandler.END


# ---------------------- افزودن فیلم ----------------------

async def add_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "🎬 لطفاً ویدیوی فیلم را ارسال کنید.",
        reply_markup=kb.back_keyboard("menu_movies"),
    )
    return ADD_MOVIE_VIDEO


async def add_movie_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    if not update.message or not update.message.video:
        await update.message.reply_text(
            "❗️ لطفاً یک فایل ویدیویی ارسال کنید.",
            reply_markup=kb.back_keyboard("menu_movies"),
        )
        return ADD_MOVIE_VIDEO

    context.user_data["new_movie_file_id"] = update.message.video.file_id
    await update.message.reply_text("✅ ویدیو دریافت شد.\nاکنون نام فیلم را وارد کنید:")
    return ADD_MOVIE_NAME


async def add_movie_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["new_movie_name"] = update.message.text.strip()
    await update.message.reply_text("📁 شماره فصل را وارد کنید:")
    return ADD_MOVIE_SEASON


async def add_movie_season(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["new_movie_season"] = update.message.text.strip()
    await update.message.reply_text("🎞 شماره قسمت را وارد کنید:")
    return ADD_MOVIE_EPISODE


async def add_movie_episode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    episode = update.message.text.strip()
    name = context.user_data.get("new_movie_name")
    season = context.user_data.get("new_movie_season")
    file_id = context.user_data.get("new_movie_file_id")

    movie_id = db.save_movie(name, season, episode, file_id)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=movie_{movie_id}"

    await update.message.reply_text(
        "✅ فیلم با موفقیت ذخیره شد.\n\n"
        f"🎬 نام: {name}\n"
        f"📁 فصل: {season}\n"
        f"🎞 قسمت: {episode}\n"
        f"🆔 شناسه: {movie_id}\n\n"
        f"🔗 لینک اختصاصی:\n{link}",
        reply_markup=kb.back_keyboard("menu_movies"),
    )

    for key in ("new_movie_name", "new_movie_season", "new_movie_file_id"):
        context.user_data.pop(key, None)

    return ConversationHandler.END


add_movie_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_movie_start, pattern="^add_movie$")],
    states={
        ADD_MOVIE_VIDEO: [MessageHandler(filters.VIDEO, add_movie_video)],
        ADD_MOVIE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_name)],
        ADD_MOVIE_SEASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_season)],
        ADD_MOVIE_EPISODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_episode)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_movies, pattern="^menu_movies$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- حذف فیلم ----------------------

async def delete_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "🗑 شناسه (ID) فیلمی که می‌خواهید حذف کنید را ارسال کنید:",
        reply_markup=kb.back_keyboard("menu_movies"),
    )
    return DELETE_MOVIE_ID


async def delete_movie_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    movie_id = update.message.text.strip()
    movie = db.get_movie(movie_id)

    if not movie:
        await update.message.reply_text(
            "❗️ فیلمی با این شناسه پیدا نشد. دوباره شناسه را ارسال کنید یا بازگردید.",
            reply_markup=kb.back_keyboard("menu_movies"),
        )
        return DELETE_MOVIE_ID

    db.delete_movie(movie_id)
    await update.message.reply_text(
        f"✅ فیلم با شناسه {movie_id} حذف شد.",
        reply_markup=kb.back_keyboard("menu_movies"),
    )
    return ConversationHandler.END


delete_movie_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(delete_movie_start, pattern="^delete_movie$")],
    states={
        DELETE_MOVIE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_movie_confirm)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CallbackQueryHandler(menu_movies, pattern="^menu_movies$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return

    movies = db.get_movies()
    if not movies:
        await query.edit_message_text(
            "📂 هیچ فیلمی ثبت نشده است.",
            reply_markup=kb.back_keyboard("menu_movies"),
        )
        return

    text = "📂 لیست فیلم‌ها:\n\n"
    for movie in movies:
        movie_id, name, season, episode = movie[0], movie[1], movie[2], movie[3]
        text += f"🆔 {movie_id} | 🎬 {name} | فصل {season} | قسمت {episode}\n"

    await query.edit_message_text(text, reply_markup=kb.back_keyboard("menu_movies"))
import os
import logging
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

from database import (
    create_tables,
    save_user,
    save_movie,
    get_movies,
    get_movie,
    delete_movie,
    add_channel,
    remove_channel,
    get_channels,
    get_users_count,
    get_movies_count,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 5341053818

ADD_MOVIE_VIDEO, ADD_MOVIE_NAME, ADD_MOVIE_SEASON, ADD_MOVIE_EPISODE = range(4)
DELETE_MOVIE_ID = 10
ADD_CHANNEL_INPUT = 20
REMOVE_CHANNEL_INPUT = 30


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎬 افزودن فیلم", callback_data="add_movie")],
        [InlineKeyboardButton("📂 لیست فیلم‌ها", callback_data="list_movies")],
        [InlineKeyboardButton("🗑 حذف فیلم", callback_data="delete_movie")],
        [InlineKeyboardButton("📢 مدیریت کانال‌های اجباری", callback_data="manage_channels")],
        [InlineKeyboardButton("👥 آمار کاربران", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(keyboard)


def channels_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ افزودن کانال", callback_data="add_channel")],
        [InlineKeyboardButton("➖ حذف کانال", callback_data="remove_channel")],
        [InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="list_channels")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_panel")]]
    )


async def send_panel(target, edit: bool) -> None:
    text = "👑 پنل مدیریت\nیکی از گزینه‌های زیر را انتخاب کنید:"
    if edit:
        await target.edit_message_text(text, reply_markup=admin_panel_keyboard())
    else:
        await target.reply_text(text, reply_markup=admin_panel_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    save_user(user.id, user.username)

    args = context.args
    if args and args[0].startswith("movie_"):
        movie_id = args[0].replace("movie_", "")
        await handle_movie_request(update, context, movie_id)
        return

    if is_admin(user.id):
        text = (
            "سلام ادمین عزیز 👋\n"
            "به ربات مدیریت فیلم خوش آمدید.\n"
            "برای دسترسی به پنل مدیریت از دستور /admin استفاده کنید."
        )
    else:
        text = (
            "سلام 👋\n"
            "به ربات فیلم خوش آمدید.\n"
            "برای دریافت فیلم از لینک‌های اختصاصی استفاده کنید."
        )
    await update.message.reply_text(text)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("⛔️ شما به این بخش دسترسی ندارید.")
        return
    await send_panel(update.message, edit=False)


async def back_to_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    context.user_data.pop("new_movie_name", None)
    context.user_data.pop("new_movie_season", None)
    context.user_data.pop("new_movie_file_id", None)
    await send_panel(query, edit=True)
    return ConversationHandler.END


# ---------------------- افزودن فیلم ----------------------

async def add_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "🎬 لطفاً ویدیوی فیلم را ارسال کنید.",
        reply_markup=back_keyboard(),
    )
    return ADD_MOVIE_VIDEO


async def add_movie_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    if not update.message or not update.message.video:
        await update.message.reply_text(
            "❗️ لطفاً یک فایل ویدیویی ارسال کنید.",
            reply_markup=back_keyboard(),
        )
        return ADD_MOVIE_VIDEO

    context.user_data["new_movie_file_id"] = update.message.video.file_id
    await update.message.reply_text("✅ ویدیو دریافت شد.\nاکنون نام فیلم را وارد کنید:")
    return ADD_MOVIE_NAME


async def add_movie_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["new_movie_name"] = update.message.text.strip()
    await update.message.reply_text("📁 شماره فصل را وارد کنید:")
    return ADD_MOVIE_SEASON


async def add_movie_season(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["new_movie_season"] = update.message.text.strip()
    await update.message.reply_text("🎞 شماره قسمت را وارد کنید:")
    return ADD_MOVIE_EPISODE


async def add_movie_episode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    episode = update.message.text.strip()
    name = context.user_data.get("new_movie_name")
    season = context.user_data.get("new_movie_season")
    file_id = context.user_data.get("new_movie_file_id")

    movie_id = save_movie(name, season, episode, file_id)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=movie_{movie_id}"

    await update.message.reply_text(
        "✅ فیلم با موفقیت ذخیره شد.\n\n"
        f"🎬 نام: {name}\n"
        f"📁 فصل: {season}\n"
        f"🎞 قسمت: {episode}\n"
        f"🆔 شناسه: {movie_id}\n\n"
        f"🔗 لینک اختصاصی:\n{link}",
        reply_markup=back_keyboard(),
    )

    context.user_data.pop("new_movie_name", None)
    context.user_data.pop("new_movie_season", None)
    context.user_data.pop("new_movie_file_id", None)

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
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- حذف فیلم ----------------------

async def delete_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "🗑 شناسه (ID) فیلمی که می‌خواهید حذف کنید را ارسال کنید:",
        reply_markup=back_keyboard(),
    )
    return DELETE_MOVIE_ID


async def delete_movie_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    movie_id = update.message.text.strip()
    movie = get_movie(movie_id)

    if not movie:
        await update.message.reply_text(
            "❗️ فیلمی با این شناسه پیدا نشد. دوباره شناسه را ارسال کنید یا بازگردید.",
            reply_markup=back_keyboard(),
        )
        return DELETE_MOVIE_ID

    delete_movie(movie_id)
    await update.message.reply_text(
        f"✅ فیلم با شناسه {movie_id} حذف شد.",
        reply_markup=back_keyboard(),
    )
    return ConversationHandler.END


delete_movie_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(delete_movie_start, pattern="^delete_movie$")],
    states={
        DELETE_MOVIE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_movie_confirm)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- مدیریت کانال‌ها ----------------------

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    await query.edit_message_text(
        "📢 مدیریت کانال‌های اجباری",
        reply_markup=channels_menu_keyboard(),
    )


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    channels = get_channels()
    if not channels:
        text = "📋 هیچ کانالی ثبت نشده است."
    else:
        text = "📋 لیست کانال‌های اجباری:\n\n" + "\n".join(f"• {ch}" for ch in channels)

    await query.edit_message_text(text, reply_markup=channels_menu_keyboard())


async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "➕ آیدی یا یوزرنیم کانال را ارسال کنید (مثال: @mychannel):",
        reply_markup=back_keyboard(),
    )
    return ADD_CHANNEL_INPUT


async def add_channel_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    channel = update.message.text.strip()
    add_channel(channel)
    await update.message.reply_text(
        f"✅ کانال {channel} با موفقیت اضافه شد.",
        reply_markup=channels_menu_keyboard(),
    )
    return ConversationHandler.END


add_channel_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_channel_start, pattern="^add_channel$")],
    states={
        ADD_CHANNEL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_channel_finish)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


async def remove_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "➖ آیدی یا یوزرنیم کانالی که می‌خواهید حذف کنید را ارسال کنید:",
        reply_markup=back_keyboard(),
    )
    return REMOVE_CHANNEL_INPUT


async def remove_channel_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    channel = update.message.text.strip()
    remove_channel(channel)
    await update.message.reply_text(
        f"✅ کانال {channel} با موفقیت حذف شد.",
        reply_markup=channels_menu_keyboard(),
    )
    return ConversationHandler.END


remove_channel_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(remove_channel_start, pattern="^remove_channel$")],
    states={
        REMOVE_CHANNEL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_channel_finish)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)


# ---------------------- آمار ----------------------

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    users_count = get_users_count()
    movies_count = get_movies_count()

    text = (
        "👥 آمار ربات\n\n"
        f"👤 تعداد کاربران: {users_count}\n"
        f"🎬 تعداد فیلم‌ها: {movies_count}"
    )
    await query.edit_message_text(text, reply_markup=back_keyboard())


async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    movies = get_movies()
    if not movies:
        await query.edit_message_text(
            "📂 هیچ فیلمی ثبت نشده است.",
            reply_markup=back_keyboard(),
        )
        return

    text = "📂 لیست فیلم‌ها:\n\n"
    for movie in movies:
        movie_id, name, season, episode = movie[0], movie[1], movie[2], movie[3]
        text += f"🆔 {movie_id} | 🎬 {name} | فصل {season} | قسمت {episode}\n"

    await query.edit_message_text(text, reply_markup=back_keyboard())


# ---------------------- عضویت اجباری و ارسال فیلم ----------------------

async def check_user_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    channels = get_channels()
    if not channels:
        return True

    for channel in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except TelegramError as exc:
            logger.warning("خطا در بررسی عضویت کانال %s: %s", channel, exc)
            return False

    return True


def build_join_keyboard(channels) -> InlineKeyboardMarkup:
    keyboard = []
    for channel in channels:
        channel_username = str(channel).lstrip("@")
        keyboard.append(
            [InlineKeyboardButton(f"📢 عضویت در {channel}", url=f"https://t.me/{channel_username}")]
        )
    keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)


async def handle_movie_request(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id: str) -> None:
    user = update.effective_user
    is_member = await check_user_membership(context, user.id)

    if not is_member:
        channels = get_channels()
        context.user_data["pending_movie_id"] = movie_id
        await update.message.reply_text(
            "❗️ برای دریافت فیلم ابتدا باید در کانال‌های زیر عضو شوید:",
            reply_markup=build_join_keyboard(channels),
        )
        return

    await send_movie_to_user(update.effective_chat.id, context, movie_id)


async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = query.from_user
    is_member = await check_user_membership(context, user.id)

    if not is_member:
        await query.answer("❗️ هنوز در تمام کانال‌ها عضو نشده‌اید.", show_alert=True)
        return

    movie_id = context.user_data.get("pending_movie_id")
    if not movie_id:
        await query.edit_message_text("✅ عضویت شما تایید شد.")
        return

    await query.edit_message_text("✅ عضویت شما تایید شد. در حال ارسال فیلم...")
    await send_movie_to_user(query.message.chat_id, context, movie_id)
    context.user_data.pop("pending_movie_id", None)


async def send_movie_to_user(chat_id: int, context: ContextTypes.DEFAULT_TYPE, movie_id: str) -> None:
    movie = get_movie(movie_id)
    if not movie:
        await context.bot.send_message(chat_id=chat_id, text="❗️ فیلم مورد نظر پیدا نشد.")
        return

    _, name, season, episode, file_id = movie

    try:
        sent_message = await context.bot.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=f"🎬 {name}\n📁 فصل {season} | قسمت {episode}\n\n⚠️ این ویدیو تا ۶۰ ثانیه دیگر حذف می‌شود.",
        )
    except TelegramError as exc:
        logger.warning("خطا در ارسال ویدیو: %s", exc)
        await context.bot.send_message(chat_id=chat_id, text="❗️ ارسال فیلم با خطا مواجه شد.")
        return

    asyncio.create_task(delete_video_later(context, chat_id, sent_message.message_id))


async def delete_video_later(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    await asyncio.sleep(60)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError as exc:
        logger.warning("خطا در حذف پیام ویدیو: %s", exc)
        return

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🗑 ویدیو حذف شد. برای دریافت مجدد از لینک اختصاصی استفاده کنید.",
        )
    except TelegramError as exc:
        logger.warning("خطا در ارسال پیام اطلاع‌رسانی: %s", exc)


# ---------------------- خطایابی ----------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("خطای ربات: %s", context.error, exc_info=context.error)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("متغیر محیطی BOT_TOKEN تنظیم نشده است.")

    create_tables()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))

    application.add_handler(add_movie_conv)
    application.add_handler(delete_movie_conv)
    application.add_handler(add_channel_conv)
    application.add_handler(remove_channel_conv)

    application.add_handler(CallbackQueryHandler(list_movies, pattern="^list_movies$"))
    application.add_handler(CallbackQueryHandler(manage_channels, pattern="^manage_channels$"))
    application.add_handler(CallbackQueryHandler(list_channels, pattern="^list_channels$"))
    application.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern="^check_membership$"))
    application.add_handler(CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"))

    application.add_error_handler(error_handler)

    # ---------------- اجرای ربات با Webhook (برای فعال بودن ۲۴/۷ روی Render) ----------------
    PORT = int(os.environ.get("PORT", 8443))
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

    if not RENDER_URL:
        raise RuntimeError(
            "متغیر محیطی RENDER_EXTERNAL_URL پیدا نشد. "
            "این متغیر به‌صورت خودکار توسط Render برای Web Service ست می‌شود."
        )

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{RENDER_URL}/{BOT_TOKEN}",
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
import keyboards as kb
import utils
from delivery import send_episode_to_user, send_movie_to_user


def user_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📩 ثبت درخواست فیلم/سریال", callback_data="request_start")]]
    )


async def send_panel(target, user_id: int, edit: bool) -> None:
    text = "👑 پنل مدیریت\nیکی از گزینه‌های زیر را انتخاب کنید:"
    keyboard = kb.main_panel_keyboard(
        user_id,
        can_manage_admins_flag=utils.can_manage_admins(user_id),
        can_settings_flag=utils.can_manage_settings(user_id),
        can_broadcast_flag=utils.can_broadcast(user_id),
        can_requests_flag=utils.can_handle_requests(user_id),
    )
    if edit:
        await target.edit_message_text(text, reply_markup=keyboard)
    else:
        await target.reply_text(text, reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.save_user(user.id, user.username)

    args = context.args
    if args:
        arg = args[0]
        if arg.startswith("movie_"):
            movie_id = arg.replace("movie_", "")
            await handle_movie_request(update, context, movie_id)
            return
        if arg.startswith("episode_"):
            code = arg.replace("episode_", "")
            await handle_episode_request(update, context, code)
            return

    if utils.is_admin(user.id):
        text = (
            "سلام ادمین عزیز 👋\n"
            "به ربات مدیریت فیلم و سریال خوش آمدید.\n"
            "برای دسترسی به پنل مدیریت از دستور /admin استفاده کنید."
        )
        await update.message.reply_text(text)
        return

    start_text = db.get_setting(
        "start_text",
        "سلام 👋\nبه ربات فیلم و سریال خوش آمدید.\nبرای دریافت محتوا از لینک‌های اختصاصی استفاده کنید.",
    )
    await update.message.reply_text(start_text, reply_markup=user_start_keyboard())


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not utils.is_admin(user.id):
        await update.message.reply_text("⛔️ شما به این بخش دسترسی ندارید.")
        return
    await send_panel(update.message, user.id, edit=False)


async def back_to_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.is_admin(query.from_user.id):
        return ConversationHandler.END

    for key in (
        "new_movie_name", "new_movie_season", "new_movie_file_id",
        "new_series_name", "new_series_season", "current_series_id", "episode_counter",
        "new_admin_id", "pending_movie_id", "pending_episode_code",
    ):
        context.user_data.pop(key, None)

    await send_panel(query, query.from_user.id, edit=True)
    return ConversationHandler.END


async def menu_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """برای بخش «مدیریت کاربران» که فعلاً فقط آمار کاربران رو نشون میده."""
    query = update.callback_query
    await query.answer()
    if not utils.is_admin(query.from_user.id):
        return

    users_count = db.get_users_count()
    new_today = db.get_new_users_count(1)
    text = (
        "👥 مدیریت کاربران\n\n"
        f"👤 تعداد کل کاربران: {users_count}\n"
        f"🆕 کاربران جدید (۲۴ ساعت اخیر): {new_today}"
    )
    await query.edit_message_text(text, reply_markup=kb.back_keyboard())


# ---------------------- عضویت اجباری و ارسال محتوا ----------------------

async def handle_movie_request(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id: str) -> None:
    user = update.effective_user
    is_member = await utils.check_user_membership(context, user.id)

    if not is_member:
        channels = db.get_channels()
        context.user_data["pending_movie_id"] = movie_id
        context.user_data.pop("pending_episode_code", None)
        await update.message.reply_text(
            "❗️ برای دریافت فیلم ابتدا باید در کانال‌های زیر عضو شوید:",
            reply_markup=kb.build_join_keyboard(channels),
        )
        return

    await send_movie_to_user(update.effective_chat.id, context, movie_id)


async def handle_episode_request(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str) -> None:
    user = update.effective_user
    is_member = await utils.check_user_membership(context, user.id)

    if not is_member:
        channels = db.get_channels()
        context.user_data["pending_episode_code"] = code
        context.user_data.pop("pending_movie_id", None)
        await update.message.reply_text(
            "❗️ برای دریافت این قسمت ابتدا باید در کانال‌های زیر عضو شوید:",
            reply_markup=kb.build_join_keyboard(channels),
        )
        return

    await send_episode_to_user(update.effective_chat.id, context, code)


async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = query.from_user
    is_member = await utils.check_user_membership(context, user.id)

    if not is_member:
        await query.answer("❗️ هنوز در تمام کانال‌ها عضو نشده‌اید.", show_alert=True)
        return

    movie_id = context.user_data.get("pending_movie_id")
    episode_code = context.user_data.get("pending_episode_code")

    if not movie_id and not episode_code:
        await query.edit_message_text("✅ عضویت شما تایید شد.")
        return

    await query.edit_message_text("✅ عضویت شما تایید شد. در حال ارسال...")

    if movie_id:
        await send_movie_to_user(query.message.chat_id, context, movie_id)
        context.user_data.pop("pending_movie_id", None)
    if episode_code:
        await send_episode_to_user(query.message.chat_id, context, episode_code)
        context.user_data.pop("pending_episode_code", None)
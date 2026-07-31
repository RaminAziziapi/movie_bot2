"""
پنل مدیریت: دستور /admin، دکمه‌ی خروج از پنل، و دکمه‌ی آمار.

هرکدام از قابلیت‌های دیگر پنل (افزودن فیلم/سریال، لیست محتوا، تنظیمات،
ارسال همگانی، درخواست‌ها) به‌صورت ConversationHandler مستقل در فایل
مربوط به خودشان تعریف شده‌اند و باید همراه با هندلرهای همین فایل در
اپ اصلی ربات ثبت شوند.
"""
import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from admin_settings import is_admin
from keyboards import admin_main_menu, user_main_menu
from texts import texts
from user_service import get_stats_text

logger = logging.getLogger(__name__)


async def admin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(texts.NOT_ADMIN)
        return
    await update.message.reply_text(texts.ADMIN_PANEL_WELCOME, reply_markup=admin_main_menu())


async def exit_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        return
    await update.message.reply_text(texts.EXIT_ADMIN_DONE, reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(texts.WELCOME_USER, reply_markup=user_main_menu())


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        return
    await update.message.reply_text(await get_stats_text())


def get_admin_panel_handlers() -> list:
    return [
        CommandHandler("admin", admin_entry),
        MessageHandler(filters.Regex(f"^{texts.BTN_EXIT_ADMIN}$"), exit_admin),
        MessageHandler(filters.Regex(f"^{texts.BTN_USER_STATS}$"), show_stats),
    ]

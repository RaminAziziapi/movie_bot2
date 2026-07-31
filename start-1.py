"""
دستور /start.

مسئولیت‌ها:
    ۱. ثبت/به‌روزرسانی کاربر در دیتابیس.
    ۲. اگر لینک عمیق (Deep Link) همراه با پیام باشد (مثلاً از دکمه‌ی
       داخل پست کانال آمده)، فرآیند تحویل فایل به کاربر آغاز می‌شود
       (channel_publish.handle_deep_link) - بعد از بررسی عضویت اجباری.
    ۳. در غیر این صورت، خوش‌آمدگویی مناسب (ادمین یا کاربر عادی) و منوی
       مربوطه نمایش داده می‌شود.
"""
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from admin_settings import is_admin
from channel_publish import handle_deep_link
from force_join import require_join
from keyboards import user_main_menu
from texts import texts
from user_service import register_user

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await register_user(update)
    user_id = update.effective_user.id
    admin = await is_admin(user_id)

    payload = context.args[0] if context.args else None

    if payload:
        if not admin and not await require_join(update, context):
            return
        await handle_deep_link(update, context, payload)
        return

    if admin:
        await update.message.reply_text(texts.WELCOME_ADMIN)
        return

    if not await require_join(update, context):
        return

    await update.message.reply_text(texts.WELCOME_USER, reply_markup=user_main_menu())


def get_start_handler() -> CommandHandler:
    return CommandHandler("start", start)

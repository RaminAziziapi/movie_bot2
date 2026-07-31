"""
عضویت اجباری در کانال(های) تنظیم‌شده توسط ادمین (force_join_channels).

سایر ماژول‌ها (start.py، movie_request.py و ...) قبل از اجرای هر عملیات
مخصوص کاربران عادی باید `require_join` را فراخوانی کنند؛ اگر کاربر عضو
همه کانال‌ها نباشد، پیام و دکمه‌های عضویت نمایش داده می‌شود و ادامه‌ی
عملیات متوقف می‌شود.

اگر یک کانال به هر دلیلی (حذف‌شدن، ربات دیگر ادمین نیست و ...) قابل
بررسی نباشد، همان کانال نادیده گرفته می‌شود (به‌جای اینکه کل ربات برای
همه کاربران قفل شود) و خطا فقط لاگ می‌شود.
"""
import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from inline import join_check_keyboard
from repository import list_force_join_channels
from texts import texts

logger = logging.getLogger(__name__)

_NOT_JOINED_STATUSES = {"left", "kicked"}


async def get_missing_channels(bot, user_id: int) -> list[dict]:
    try:
        channels = await list_force_join_channels()
    except Exception:
        logger.exception("خطا در دریافت لیست کانال‌های عضویت اجباری")
        return []

    missing = []
    for channel in channels:
        chat_id = channel["chat_id"]
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in _NOT_JOINED_STATUSES:
                missing.append(dict(channel))
        except Exception:
            logger.warning("بررسی عضویت کانال %s ممکن نشد؛ نادیده گرفته شد.", chat_id, exc_info=True)

    return missing


async def require_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """True یعنی کاربر مجاز به ادامه است. اگر False برگرداند، پیام لازم قبلاً ارسال شده."""
    user_id = update.effective_user.id
    missing = await get_missing_channels(context.bot, user_id)

    if not missing:
        return True

    await update.effective_message.reply_text(
        texts.JOIN_REQUIRED, reply_markup=join_check_keyboard(missing)
    )
    return False


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    missing = await get_missing_channels(context.bot, user_id)

    if missing:
        await query.answer(texts.JOIN_CHECK_FAILED, show_alert=True)
        return

    await query.answer()
    await query.edit_message_text(texts.JOIN_CONFIRMED)


def get_force_join_handlers() -> list:
    return [CallbackQueryHandler(check_join_callback, pattern=r"^check_join$")]

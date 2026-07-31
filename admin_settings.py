"""
مدیریت تنظیمات ربات: ادمین‌های اضافی و کانال‌های عضویت اجباری.

نکته مهم درباره ادمین‌ها:
تابع `is_admin` در همین فایل، تنها منبع معتبر برای بررسی «آیا کاربر ادمین
است؟» در کل پروژه است و هر دو منبع را ترکیب می‌کند:
    ۱. ADMIN_IDS در Environment (ادمین‌های اصلی/بوت‌استرپ)
    ۲. جدول admins در دیتابیس (ادمین‌هایی که از داخل ربات اضافه شده‌اند)
سایر ماژول‌ها (admin_panel، movie_management، broadcast، movie_request و ...)
باید همیشه از همین تابع استفاده کنند، نه از بررسی مستقیم config.ADMIN_IDS.
"""
import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import config
from inline import admins_menu_keyboard, force_join_menu_keyboard, settings_menu_keyboard
from repository import (
    add_admin,
    add_force_join_channel,
    is_admin_in_db,
    list_admins,
    list_force_join_channels,
    remove_admin,
    remove_force_join_channel,
)
from texts import texts

logger = logging.getLogger(__name__)

# --- states ---
(
    SETTINGS_MENU, ADMINS_MENU, WAIT_ADD_ADMIN, WAIT_REMOVE_ADMIN,
    FORCEJOIN_MENU, WAIT_ADD_FORCEJOIN, WAIT_REMOVE_FORCEJOIN,
) = range(7)


# ==================== بررسی ترکیبی ادمین (منبع واحد در کل پروژه) ====================

async def is_admin(user_id: int) -> bool:
    if user_id in config.ADMIN_IDS:
        return True
    try:
        return await is_admin_in_db(user_id)
    except Exception:
        logger.exception("خطا در بررسی ادمین از دیتابیس؛ فرض بر عدم دسترسی است.")
        return False


async def get_all_admin_ids() -> list[int]:
    """اتحاد ادمین‌های اصلی (Environment) و ادمین‌های دیتابیس، بدون تکرار."""
    ids = set(config.ADMIN_IDS)
    try:
        rows = await list_admins()
        ids.update(row["user_id"] for row in rows)
    except Exception:
        logger.exception("خطا در دریافت لیست ادمین‌ها از دیتابیس.")
    return list(ids)


# ==================== منوی تنظیمات ====================

async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text(texts.NOT_ADMIN)
        return ConversationHandler.END

    await update.message.reply_text(texts.SETTINGS_MENU, reply_markup=settings_menu_keyboard())
    return SETTINGS_MENU


async def settings_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "settings_admins":
        return await _show_admins_menu(query)
    if query.data == "settings_forcejoin":
        return await _show_forcejoin_menu(query)

    return SETTINGS_MENU


async def _show_admins_menu(query) -> int:
    try:
        rows = await list_admins()
    except Exception:
        logger.exception("خطا در دریافت لیست ادمین‌ها")
        rows = []

    lines = [texts.ADMIN_LIST_HEADER]
    for main_id in config.ADMIN_IDS:
        lines.append(f"• {main_id} (اصلی)")
    if rows:
        for row in rows:
            lines.append(f"• {row['user_id']}")
    elif not config.ADMIN_IDS:
        lines.append(texts.ADMIN_LIST_EMPTY)

    await query.edit_message_text("\n".join(lines), reply_markup=admins_menu_keyboard())
    return ADMINS_MENU


async def _show_forcejoin_menu(query) -> int:
    try:
        rows = await list_force_join_channels()
    except Exception:
        logger.exception("خطا در دریافت لیست کانال‌های عضویت اجباری")
        rows = []

    lines = [texts.FORCE_JOIN_LIST_HEADER]
    if rows:
        for row in rows:
            title = row["title"] or row["chat_id"]
            lines.append(f"• {title} ({row['chat_id']})")
    else:
        lines.append(texts.FORCE_JOIN_LIST_EMPTY)

    await query.edit_message_text("\n".join(lines), reply_markup=force_join_menu_keyboard())
    return FORCEJOIN_MENU


async def back_to_settings(query) -> int:
    await query.edit_message_text(texts.SETTINGS_MENU, reply_markup=settings_menu_keyboard())
    return SETTINGS_MENU


# ==================== مدیریت ادمین‌ها ====================

async def admins_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "settings_back":
        return await back_to_settings(query)
    if query.data == "admins_add":
        await query.edit_message_text(texts.ASK_NEW_ADMIN_ID)
        return WAIT_ADD_ADMIN
    if query.data == "admins_remove":
        await query.edit_message_text(texts.ASK_REMOVE_ADMIN_ID)
        return WAIT_REMOVE_ADMIN

    return ADMINS_MENU


async def wait_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    if not raw.lstrip("-").isdigit():
        await update.message.reply_text(texts.INVALID_USER_ID)
        return WAIT_ADD_ADMIN

    new_admin_id = int(raw)
    if new_admin_id in config.ADMIN_IDS:
        await update.message.reply_text(texts.ADMIN_ALREADY_MAIN)
    else:
        try:
            await add_admin(new_admin_id, added_by=update.effective_user.id)
            await update.message.reply_text(texts.ADMIN_ADDED.format(user_id=new_admin_id))
        except Exception:
            logger.exception("خطا در افزودن ادمین جدید")
            await update.message.reply_text(texts.GENERIC_ERROR)

    await update.message.reply_text(texts.SETTINGS_MENU, reply_markup=admins_menu_keyboard())
    return ADMINS_MENU


async def wait_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    if not raw.lstrip("-").isdigit():
        await update.message.reply_text(texts.INVALID_USER_ID)
        return WAIT_REMOVE_ADMIN

    target_id = int(raw)
    if target_id in config.ADMIN_IDS:
        await update.message.reply_text(texts.CANNOT_REMOVE_MAIN_ADMIN)
    else:
        try:
            await remove_admin(target_id)
            await update.message.reply_text(texts.ADMIN_REMOVED.format(user_id=target_id))
        except Exception:
            logger.exception("خطا در حذف ادمین")
            await update.message.reply_text(texts.GENERIC_ERROR)

    await update.message.reply_text(texts.SETTINGS_MENU, reply_markup=admins_menu_keyboard())
    return ADMINS_MENU


# ==================== مدیریت کانال‌های عضویت اجباری ====================

async def forcejoin_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "settings_back":
        return await back_to_settings(query)
    if query.data == "fjoin_add":
        await query.edit_message_text(texts.ASK_FORCE_JOIN_CHANNEL)
        return WAIT_ADD_FORCEJOIN
    if query.data == "fjoin_remove":
        await query.edit_message_text(texts.ASK_REMOVE_FORCE_JOIN_CHANNEL)
        return WAIT_REMOVE_FORCEJOIN

    return FORCEJOIN_MENU


def _parse_channel_ref(raw: str):
    raw = raw.strip()
    if raw.lstrip("-").isdigit():
        return int(raw)
    if not raw.startswith("@"):
        raw = f"@{raw}"
    return raw


async def wait_add_forcejoin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_ref = _parse_channel_ref(update.message.text)

    try:
        chat = await context.bot.get_chat(chat_ref)
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            raise RuntimeError("ربات در این کانال ادمین نیست.")

        invite_link = chat.invite_link
        if not invite_link:
            try:
                invite_link = await context.bot.export_chat_invite_link(chat.id)
            except Exception:
                invite_link = None

        await add_force_join_channel(
            chat_id=str(chat.id),
            title=chat.title,
            invite_link=invite_link,
            added_by=update.effective_user.id,
        )
        await update.message.reply_text(texts.FORCE_JOIN_CHANNEL_ADDED.format(chat_id=chat.id))
    except Exception:
        logger.exception("خطا در افزودن کانال عضویت اجباری")
        await update.message.reply_text(texts.FORCE_JOIN_CHANNEL_ADD_ERROR)

    await update.message.reply_text(texts.SETTINGS_MENU, reply_markup=force_join_menu_keyboard())
    return FORCEJOIN_MENU


async def wait_remove_forcejoin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    try:
        try:
            chat = await context.bot.get_chat(_parse_channel_ref(raw))
            chat_id = str(chat.id)
        except Exception:
            chat_id = raw

        await remove_force_join_channel(chat_id)
        await update.message.reply_text(texts.FORCE_JOIN_CHANNEL_REMOVED.format(chat_id=chat_id))
    except Exception:
        logger.exception("خطا در حذف کانال عضویت اجباری")
        await update.message.reply_text(texts.GENERIC_ERROR)

    await update.message.reply_text(texts.SETTINGS_MENU, reply_markup=force_join_menu_keyboard())
    return FORCEJOIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(texts.CANCELLED)
    return ConversationHandler.END


def get_admin_settings_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{texts.BTN_SETTINGS}$"), entry)],
        states={
            SETTINGS_MENU: [CallbackQueryHandler(settings_menu_router, pattern=r"^settings_")],
            ADMINS_MENU: [CallbackQueryHandler(admins_menu_router, pattern=r"^(admins_|settings_back)")],
            WAIT_ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_add_admin)],
            WAIT_REMOVE_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_remove_admin)],
            FORCEJOIN_MENU: [CallbackQueryHandler(forcejoin_menu_router, pattern=r"^(fjoin_|settings_back)")],
            WAIT_ADD_FORCEJOIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_add_forcejoin)],
            WAIT_REMOVE_FORCEJOIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_remove_forcejoin)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="admin_settings_conversation",
        persistent=False,
    )

from telegram import Update
from telegram.error import TelegramError
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
from gemini_client import process_with_gemini
from start_handlers import back_to_panel, send_panel
from tmdb_client import get_tmdb_details, search_tmdb

TMDB_SEARCH_NAME, TMDB_PREVIEW, TMDB_EDIT = range(100, 103)


def _format_preview(d: dict) -> str:
    is_tv = d.get("content_type") == "tv"
    title_line = d.get("title") or ""
    if d.get("title_fa"):
        title_line += f" ({d['title_fa']})"

    icon = "📺" if is_tv else "🎬"
    lines = [f"{icon} {title_line}", ""]

    if d.get("year"):
        lines.append(f"📅 سال ساخت: {d['year']}")
    if d.get("rating"):
        lines.append(f"⭐ امتیاز: {d['rating']}")
    genre = d.get("genre_fa") or d.get("genre")
    if genre:
        lines.append(f"🎭 ژانر: {genre}")
    if d.get("country"):
        lines.append(f"🌍 کشور: {d['country']}")
    if d.get("runtime"):
        lines.append(f"⏱ مدت زمان: {d['runtime']}")
    if is_tv:
        if d.get("number_of_seasons"):
            lines.append(f"📚 تعداد فصل‌ها: {d['number_of_seasons']}")
        if d.get("number_of_episodes"):
            lines.append(f"🎞 تعداد قسمت‌ها: {d['number_of_episodes']}")
    if d.get("director"):
        lines.append(f"🎬 کارگردان: {d['director']}")
    if d.get("actors"):
        lines.append(f"👥 بازیگران:\n{d['actors']}")

    summary = d.get("summary_fa") or d.get("description_raw")
    if summary:
        lines.append(f"\n📝 خلاصه:\n{summary}")

    if d.get("intro"):
        lines.append(f"\n📢 متن معرفی کانال:\n{d['intro']}")

    return "\n".join(lines)


async def _show_preview(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    d = context.user_data["tmdb_draft"]
    text = _format_preview(d)
    keyboard = kb.tmdb_preview_keyboard()

    TELEGRAM_CAPTION_LIMIT = 1024

    if d.get("poster_url"):
        try:
            if len(text) <= TELEGRAM_CAPTION_LIMIT:
                await context.bot.send_photo(chat_id=chat_id, photo=d["poster_url"], caption=text, reply_markup=keyboard)
            else:
                # کپشن جا نمی‌شه: اول فقط عکس، بعد کل متن رو جدا با دکمه‌ها بفرست
                title_line = d.get("title") or ""
                await context.bot.send_photo(chat_id=chat_id, photo=d["poster_url"], caption=title_line[:TELEGRAM_CAPTION_LIMIT])
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
            return
        except TelegramError:
            pass  # اگه لینک عکس مشکل داشت، حداقل متن رو بفرست

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)


async def tmdb_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    await query.edit_message_text(
        "🔍 نام فیلم یا سریال را وارد کنید (فارسی یا انگلیسی):",
        reply_markup=kb.back_keyboard(),
    )
    return TMDB_SEARCH_NAME


async def tmdb_search_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    query_text = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال جستجو در TMDB...")

    try:
        result = await search_tmdb(query_text)
    except Exception as exc:
        await status_msg.edit_text(f"❗️ خطا در ارتباط با TMDB: {exc}", reply_markup=kb.back_keyboard())
        return TMDB_SEARCH_NAME

    if not result:
        await status_msg.edit_text(
            "❗️ چیزی با این نام پیدا نشد. یک نام دیگر امتحان کنید یا بازگردید.",
            reply_markup=kb.back_keyboard(),
        )
        return TMDB_SEARCH_NAME

    media_type = result.get("media_type")

    try:
        details = await get_tmdb_details(result["id"], media_type)
    except Exception as exc:
        await status_msg.edit_text(f"❗️ خطا در دریافت جزئیات از TMDB: {exc}", reply_markup=kb.back_keyboard())
        return TMDB_SEARCH_NAME

    await status_msg.edit_text("🤖 در حال پردازش متن با هوش مصنوعی...")

    try:
        gemini_out = await process_with_gemini(details)
    except Exception:
        gemini_out = {"genre_fa": details.get("genre", ""), "summary_fa": details.get("description_raw", ""), "intro": ""}

    details.update(gemini_out)
    context.user_data["tmdb_draft"] = details

    await status_msg.delete()
    await _show_preview(update.effective_chat.id, context)
    return TMDB_PREVIEW


async def tmdb_preview_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not utils.can_manage_content(query.from_user.id):
        return ConversationHandler.END

    action = query.data

    if action == "tmdb_cancel":
        context.user_data.pop("tmdb_draft", None)
        await query.message.reply_text("❌ لغو شد.")
        await send_panel(query.message, query.from_user.id, edit=False)
        return ConversationHandler.END

    if action == "tmdb_research":
        context.user_data.pop("tmdb_draft", None)
        await query.message.reply_text("🔄 نام جدید را برای جستجو وارد کنید:")
        return TMDB_SEARCH_NAME

    if action == "tmdb_edit":
        await query.message.reply_text(
            "✏️ متن خلاصه/معرفی جدیدی که می‌خواهید جایگزین خلاصه فعلی شود را بنویسید:"
        )
        return TMDB_EDIT

    if action == "tmdb_confirm":
        d = context.user_data.get("tmdb_draft")
        if not d:
            await query.message.reply_text("❗️ اطلاعاتی برای ذخیره پیدا نشد.")
            return ConversationHandler.END

        draft_id = db.save_content_draft(d, query.from_user.id)
        await query.message.reply_text(f"✅ اطلاعات با شناسه #{draft_id} ذخیره شد.")
        context.user_data.pop("tmdb_draft", None)
        await send_panel(query.message, query.from_user.id, edit=False)
        return ConversationHandler.END

    return TMDB_PREVIEW


async def tmdb_edit_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not utils.can_manage_content(update.effective_user.id):
        return ConversationHandler.END

    d = context.user_data.get("tmdb_draft")
    if not d:
        await update.message.reply_text("❗️ اطلاعاتی برای ویرایش پیدا نشد.")
        return ConversationHandler.END

    d["summary_fa"] = update.message.text.strip()
    context.user_data["tmdb_draft"] = d

    await _show_preview(update.effective_chat.id, context)
    return TMDB_PREVIEW


tmdb_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(tmdb_start, pattern="^tmdb_start$")],
    states={
        TMDB_SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tmdb_search_name)],
        TMDB_PREVIEW: [
            CallbackQueryHandler(tmdb_preview_action, pattern="^tmdb_(confirm|edit|research|cancel)$")
        ],
        TMDB_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tmdb_edit_receive)],
    },
    fallbacks=[
        CallbackQueryHandler(back_to_panel, pattern="^back_to_panel$"),
        CommandHandler("cancel", back_to_panel),
    ],
    per_message=False,
)
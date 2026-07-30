from telegram import Update
from telegram.ext import ContextTypes

import database as db
import keyboards as kb
import utils


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not utils.can_view_stats(query.from_user.id):
        return

    text = (
        "📊 آمار ربات\n\n"
        f"👤 تعداد کاربران: {db.get_users_count()}\n"
        f"🆕 کاربران جدید (۲۴ ساعت اخیر): {db.get_new_users_count(1)}\n"
        f"🎬 تعداد فیلم‌ها: {db.get_movies_count()}\n"
        f"📺 تعداد سریال‌ها: {db.get_series_count()}\n"
        f"🎞 تعداد قسمت‌ها: {db.get_episodes_count()}\n"
        f"🛡 تعداد مدیران: {db.get_admins_count()}"
    )
    await query.edit_message_text(text, reply_markup=kb.back_keyboard())
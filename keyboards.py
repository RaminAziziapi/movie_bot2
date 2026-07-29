from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_panel_keyboard(user_id, can_manage_admins_flag, can_settings_flag, can_broadcast_flag, can_requests_flag):
    keyboard = [
        [InlineKeyboardButton("🎬 مدیریت فیلم", callback_data="menu_movies")],
        [InlineKeyboardButton("📺 مدیریت سریال", callback_data="menu_series")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="menu_users")],
    ]
    if can_manage_admins_flag:
        keyboard.append([InlineKeyboardButton("🛡 مدیریت مدیران", callback_data="menu_admins")])
    if can_settings_flag:
        keyboard.append([InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings")])
    keyboard.append([InlineKeyboardButton("📊 آمار", callback_data="stats")])
    if can_broadcast_flag:
        keyboard.append([InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast_start")])
    if can_requests_flag:
        keyboard.append([InlineKeyboardButton("📝 درخواست‌ها", callback_data="requests_list")])
    return InlineKeyboardMarkup(keyboard)


def movies_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎬 افزودن فیلم", callback_data="add_movie")],
        [InlineKeyboardButton("📂 لیست فیلم‌ها", callback_data="list_movies")],
        [InlineKeyboardButton("🗑 حذف فیلم", callback_data="delete_movie")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def series_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📺 افزودن سریال", callback_data="add_series")],
        [InlineKeyboardButton("📂 لیست سریال‌ها", callback_data="list_series")],
        [InlineKeyboardButton("🗑 حذف سریال", callback_data="delete_series")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admins_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ افزودن مدیر", callback_data="add_admin")],
        [Inl
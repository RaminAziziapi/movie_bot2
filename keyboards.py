from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_panel_keyboard(user_id, can_manage_admins_flag, can_settings_flag, can_broadcast_flag, can_requests_flag):
    keyboard = [
        [InlineKeyboardButton("🎬 مدیریت فیلم", callback_data="menu_movies")],
        [InlineKeyboardButton("📺 مدیریت سریال", callback_data="menu_series")],
        [InlineKeyboardButton("🔍 افزودن با TMDB", callback_data="tmdb_start")],
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
        [InlineKeyboardButton("➖ حذف مدیر", callback_data="remove_admin")],
        [InlineKeyboardButton("📋 لیست مدیران", callback_data="list_admins")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📢 کانال‌های اجباری", callback_data="manage_channels")],
        [InlineKeyboardButton("✏️ متن استارت", callback_data="setting_start_text")],
        [InlineKeyboardButton("📜 متن قوانین", callback_data="setting_rules_text")],
        [InlineKeyboardButton("🆘 لینک پشتیبانی", callback_data="setting_support_link")],
        [InlineKeyboardButton("💾 بکاپ", callback_data="settings_backup")],
        [InlineKeyboardButton("♻️ ریستور", callback_data="settings_restore")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def channels_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ افزودن کانال", callback_data="add_channel")],
        [InlineKeyboardButton("➖ حذف کانال", callback_data="remove_channel")],
        [InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="list_channels")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_settings")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard(target: str = "back_to_panel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=target)]])


def role_select_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🛡 ادمین", callback_data="role_admin")],
        [InlineKeyboardButton("📤 آپلودکننده", callback_data="role_uploader")],
        [InlineKeyboardButton("🎧 پشتیبان", callback_data="role_support")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="back_to_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(confirm_data: str, cancel_data: str = "back_to_panel") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ بله", callback_data=confirm_data),
            InlineKeyboardButton("❌ خیر", callback_data=cancel_data),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_join_keyboard(channels) -> InlineKeyboardMarkup:
    keyboard = []
    for channel in channels:
        channel_username = str(channel).lstrip("@")
        keyboard.append(
            [InlineKeyboardButton(f"📢 عضویت در {channel}", url=f"https://t.me/{channel_username}")]
        )
    keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)


def tmdb_preview_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ تأیید و ذخیره", callback_data="tmdb_confirm"),
            InlineKeyboardButton("✏️ ویرایش", callback_data="tmdb_edit"),
        ],
        [
            InlineKeyboardButton("🔄 جستجوی دوباره", callback_data="tmdb_research"),
            InlineKeyboardButton("❌ لغو", callback_data="tmdb_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

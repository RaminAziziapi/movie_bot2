"""کیبوردهای شیشه‌ای (Inline) مورد استفاده در تمام بخش‌های ربات.

برای جلوگیری از برخورد callback_data بین فرآیندهای مختلف (افزودن فیلم،
افزودن سریال، مدیریت محتوا و ...)، اکثر کیبوردهای عمومی یک «prefix»
منحصربه‌فرد می‌گیرند و callback_data را با همان prefix می‌سازند.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from texts import texts

_QUALITY_OPTIONS = ["480p", "720p", "1080p"]


# ==================== شروع افزودن محتوا ====================

def content_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texts.BTN_ADD_MOVIE, callback_data="addtype_movie")],
            [InlineKeyboardButton(texts.BTN_ADD_SERIES, callback_data="addtype_series")],
        ]
    )


# ==================== جستجوی TMDB (مشترک فیلم/سریال) ====================

def results_keyboard(results: list[dict], cancel_callback: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(r["label"], callback_data=f"pick_{r['tmdb_id']}_{r['media_type']}")]
        for r in results
    ]
    buttons.append([InlineKeyboardButton("❌ لغو", callback_data=cancel_callback)])
    return InlineKeyboardMarkup(buttons)


# ==================== پیش‌نمایش عمومی (افزودن فیلم/سریال) ====================

def preview_keyboard(prefix: str, allow_research: bool = True) -> InlineKeyboardMarkup:
    """
    prefix مثلاً 'movprev' یا 'serprev' است؛ callback_data ها به شکل
    f"{prefix}_confirm" / f"{prefix}_edit" / f"{prefix}_research" / f"{prefix}_cancel"
    ساخته می‌شوند.
    """
    rows = [[InlineKeyboardButton("✅ انتشار", callback_data=f"{prefix}_confirm")]]
    edit_row = [InlineKeyboardButton("✏️ ویرایش", callback_data=f"{prefix}_edit")]
    if allow_research:
        edit_row.append(InlineKeyboardButton("🔄 جستجوی دوباره", callback_data=f"{prefix}_research"))
    rows.append(edit_row)
    rows.append([InlineKeyboardButton("❌ لغو", callback_data=f"{prefix}_cancel")])
    return InlineKeyboardMarkup(rows)


def edit_fields_keyboard(prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"{prefix}_{field}")]
        for field, label in texts.EDIT_FIELD_LABELS.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت به پیش‌نمایش", callback_data=back_callback)])
    return InlineKeyboardMarkup(buttons)


# ==================== افزودن سریال: کنترل فصل‌ها ====================

def season_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texts.BTN_NEW_SEASON, callback_data="season_new")],
            [InlineKeyboardButton(texts.BTN_FINISH_SERIES, callback_data="season_finish_series")],
        ]
    )


# ==================== کیفیت فایل (فیلم) ====================

def quality_keyboard(prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(q, callback_data=f"{prefix}_{q}")] for q in _QUALITY_OPTIONS
    ]
    return InlineKeyboardMarkup(buttons)


# ==================== مدیریت محتوا (پنل ادمین) ====================

def content_list_keyboard(items, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    for item in items:
        icon = "🎬" if item["media_type"] == "movie" else "📺"
        label = f"{icon} {item['persian_title'] or item['title']} ({item['year'] or '-'})"
        if item["published"]:
            label += " ✅"
        buttons.append([InlineKeyboardButton(label, callback_data=f"clist_item_{item['id']}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"clist_page_{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"clist_page_{page + 1}"))
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


def content_detail_keyboard(content_id: int, published: bool, media_type: str) -> InlineKeyboardMarkup:
    publish_label = "🔁 به‌روزرسانی پست کانال" if published else "📢 انتشار در کانال"
    rows = [
        [InlineKeyboardButton("✏️ ویرایش", callback_data=f"cdetail_edit_{content_id}")],
    ]
    if media_type == "movie":
        rows.append(
            [InlineKeyboardButton("🎞 افزودن/تعویض فایل", callback_data=f"cdetail_addfile_{content_id}")]
        )
    else:
        rows.append(
            [InlineKeyboardButton("📺 افزودن فصل جدید", callback_data=f"cdetail_addseason_{content_id}")]
        )
    rows.append([InlineKeyboardButton(publish_label, callback_data=f"cdetail_publish_{content_id}")])
    rows.append([InlineKeyboardButton("🗑 حذف", callback_data=f"cdetail_delete_{content_id}")])
    rows.append([InlineKeyboardButton("⬅️ بازگشت به لیست", callback_data="clist_page_1")])
    return InlineKeyboardMarkup(rows)


def content_edit_fields_keyboard(content_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"cedit_{field}")]
        for field, label in texts.EDIT_FIELD_LABELS_FULL.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data=f"clist_item_{content_id}")])
    return InlineKeyboardMarkup(buttons)


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ بله، حذف کن", callback_data="cdelete_confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="cdelete_cancel")],
        ]
    )


# ==================== ارسال همگانی ====================

def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ ارسال", callback_data="bcast_confirm")],
            [InlineKeyboardButton("❌ لغو", callback_data="bcast_cancel")],
        ]
    )


# ==================== تنظیمات: ادمین‌ها و کانال‌های عضویت اجباری ====================

def settings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texts.BTN_MANAGE_ADMINS, callback_data="settings_admins")],
            [InlineKeyboardButton(texts.BTN_MANAGE_FORCE_JOIN, callback_data="settings_forcejoin")],
        ]
    )


def admins_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texts.BTN_ADD_ADMIN, callback_data="admins_add")],
            [InlineKeyboardButton(texts.BTN_REMOVE_ADMIN, callback_data="admins_remove")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="settings_back")],
        ]
    )


def force_join_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(texts.BTN_ADD_FORCE_JOIN, callback_data="fjoin_add")],
            [InlineKeyboardButton(texts.BTN_REMOVE_FORCE_JOIN, callback_data="fjoin_remove")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="settings_back")],
        ]
    )


# ==================== عضویت اجباری (کاربر) ====================

def join_check_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        if ch.get("invite_link"):
            title = ch.get("title") or "کانال"
            rows.append(
                [InlineKeyboardButton(f"{texts.JOIN_BUTTON_PREFIX} {title}", url=ch["invite_link"])]
            )
    rows.append([InlineKeyboardButton(texts.CHECK_JOIN_BUTTON, callback_data="check_join")])
    return InlineKeyboardMarkup(rows)


# ==================== تحویل فایل/قسمت به کاربر ====================

def deliver_quality_keyboard(content_id: int, qualities: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(q, callback_data=f"delivermovie_{content_id}_{q}")] for q in qualities
    ]
    return InlineKeyboardMarkup(buttons)


def deliver_season_keyboard(content_id: int, seasons: list[int]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"فصل {s}", callback_data=f"deliverseason_{content_id}_{s}")]
        for s in seasons
    ]
    return InlineKeyboardMarkup(buttons)


def deliver_episode_keyboard(content_id: int, season_number: int, episodes: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for ep in episodes:
        row.append(
            InlineKeyboardButton(
                f"قسمت {ep}", callback_data=f"deliverep_{content_id}_{season_number}_{ep}"
            )
        )
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [InlineKeyboardButton("⬅️ بازگشت به فصل‌ها", callback_data=f"deliverseasons_{content_id}")]
    )
    return InlineKeyboardMarkup(buttons)

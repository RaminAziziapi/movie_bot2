"""کیبوردهای دکمه‌ای (Reply Keyboard) — منوی اصلی پنل ادمین، منوی کاربر عادی
و کیبورد حالت دریافت قسمت‌های سریال.
"""
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

from texts import texts


def admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [texts.BTN_ADD_MOVIE, texts.BTN_ADD_SERIES],
            [texts.BTN_MOVIE_LIST, texts.BTN_USER_STATS],
            [texts.BTN_MOVIE_REQUESTS, texts.BTN_BROADCAST],
            [texts.BTN_SETTINGS],
            [texts.BTN_EXIT_ADMIN],
        ],
        resize_keyboard=True,
    )


def user_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[texts.BTN_REQUEST_MOVIE]],
        resize_keyboard=True,
    )


def episode_collection_menu() -> ReplyKeyboardMarkup:
    """کیبورد نمایش داده‌شده در حین ارسال پشت‌سرهم قسمت‌های یک فصل."""
    return ReplyKeyboardMarkup(
        [[texts.SEASON_FINISHED_BUTTON]],
        resize_keyboard=True,
    )


def remove_menu() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()

import logging

from telegram.error import TelegramError

import database as db
from config import OWNER_ID, ROLE_LEVELS

logger = logging.getLogger(__name__)


def get_role(user_id: int):
    """نقش کاربر رو برمی‌گردونه: owner / admin / uploader / support / None"""
    if user_id == OWNER_ID:
        return "owner"
    return db.get_admin_role(user_id)


def is_admin(user_id: int) -> bool:
    """آیا کاربر اصلاً جزو مدیرهاست (هر سطحی)"""
    return get_role(user_id) is not None


def has_level(user_id: int, min_role: str) -> bool:
    role = get_role(user_id)
    if role is None:
        return False
    return ROLE_LEVELS.get(role, 0) >= ROLE_LEVELS.get(min_role, 999)


def is_owner(user_id: int) -> bool:
    return get_role(user_id) == "owner"


def can_manage_content(user_id: int) -> bool:
    """افزودن/حذف فیلم و سریال: owner, admin, uploader"""
    return has_level(user_id, "uploader")


def can_manage_settings(user_id: int) -> bool:
    """تنظیمات، کانال‌ها: owner, admin"""
    return has_level(user_id, "admin")


def can_manage_admins(user_id: int) -> bool:
    """اضافه/حذف مدیر: فقط owner"""
    return is_owner(user_id)


def can_broadcast(user_id: int) -> bool:
    return has_level(user_id, "admin")


def can_handle_requests(user_id: int) -> bool:
    """دیدن و پاسخ به درخواست‌ها: owner, admin, support"""
    role = get_role(user_id)
    return role in ("owner", "admin", "support")


def can_view_stats(user_id: int) -> bool:
    return is_admin(user_id)


async def check_user_membership(context, user_id: int) -> bool:
    channels = db.get_channels()
    if not channels:
        return True

    for channel in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except TelegramError as exc:
            logger.warning("خطا در بررسی عضویت کانال %s: %s", channel, exc)
            return False

    return True
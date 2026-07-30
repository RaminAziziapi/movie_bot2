import logging
import os

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
from config import BOT_TOKEN

import start_handlers as sh
import movies_handlers as mh
import series_handlers as srh
import admins_handlers as ah
import broadcast_handlers as bh
import requests_handlers as rh
import settings_handlers as seth
import stats_handlers as sth
import content_handlers as ch

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("خطای ربات: %s", context.error, exc_info=context.error)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("متغیر محیطی BOT_TOKEN تنظیم نشده است.")

    db.create_tables()

    application = Application.builder().token(BOT_TOKEN).build()

    # --- دستورات پایه ---
    application.add_handler(CommandHandler("start", sh.start))
    application.add_handler(CommandHandler("admin", sh.admin_command))

    # --- مکالمات (Conversation Handlers) ---
    application.add_handler(mh.add_movie_conv)
    application.add_handler(mh.delete_movie_conv)
    application.add_handler(srh.add_series_conv)
    application.add_handler(srh.delete_series_conv)
    application.add_handler(ah.add_admin_conv)
    application.add_handler(ah.remove_admin_conv)
    application.add_handler(bh.broadcast_conv)
    application.add_handler(rh.request_conv)
    application.add_handler(seth.add_channel_conv)
    application.add_handler(seth.remove_channel_conv)
    application.add_handler(seth.setting_start_text_conv)
    application.add_handler(seth.setting_rules_text_conv)
    application.add_handler(seth.setting_support_link_conv)
    application.add_handler(seth.settings_restore_conv)
    application.add_handler(ch.tmdb_conv)

    # --- ناوبری پنل ---
    application.add_handler(CallbackQueryHandler(sh.back_to_panel, pattern="^back_to_panel$"))
    application.add_handler(CallbackQueryHandler(mh.menu_movies, pattern="^menu_movies$"))
    application.add_handler(CallbackQueryHandler(srh.menu_series, pattern="^menu_series$"))
    application.add_handler(CallbackQueryHandler(sh.menu_placeholder, pattern="^menu_users$"))
    application.add_handler(CallbackQueryHandler(ah.menu_admins, pattern="^menu_admins$"))
    application.add_handler(CallbackQueryHandler(seth.menu_settings, pattern="^menu_settings$"))

    # --- فیلم ---
    application.add_handler(CallbackQueryHandler(mh.list_movies, pattern="^list_movies$"))

    # --- سریال ---
    application.add_handler(CallbackQueryHandler(srh.list_series, pattern="^list_series$"))

    # --- مدیران ---
    application.add_handler(CallbackQueryHandler(ah.list_admins, pattern="^list_admins$"))

    # --- تنظیمات / کانال‌ها ---
    application.add_handler(CallbackQueryHandler(seth.manage_channels, pattern="^manage_channels$"))
    application.add_handler(CallbackQueryHandler(seth.list_channels, pattern="^list_channels$"))
    application.add_handler(CallbackQueryHandler(seth.settings_backup, pattern="^settings_backup$"))

    # --- آمار ---
    application.add_handler(CallbackQueryHandler(sth.stats, pattern="^stats$"))

    # --- درخواست‌ها ---
    application.add_handler(CallbackQueryHandler(rh.requests_list, pattern="^requests_list$"))
    application.add_handler(CallbackQueryHandler(rh.fulfill_request_callback, pattern="^fulfill_request_\\d+$"))

    # --- عضویت اجباری ---
    application.add_handler(CallbackQueryHandler(sh.check_membership_callback, pattern="^check_membership$"))

    application.add_error_handler(error_handler)

    # ---------------- اجرای ربات با Webhook (برای فعال بودن ۲۴/۷ روی Render) ----------------
    PORT = int(os.environ.get("PORT", 8443))
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

    if not RENDER_URL:
        raise RuntimeError(
            "متغیر محیطی RENDER_EXTERNAL_URL پیدا نشد. "
            "این متغیر به‌صورت خودکار توسط Render برای Web Service ست می‌شود."
        )

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{RENDER_URL}/{BOT_TOKEN}",
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()

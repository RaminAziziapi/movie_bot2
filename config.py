import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# مالک اصلی ربات (بالاترین سطح دسترسی). اگه بخواید عوضش کنید، آیدی عددی
# جدید رو توی Environment Variable به اسم OWNER_ID توی Render بذارید.
OWNER_ID = int(os.environ.get("OWNER_ID", "5341053818"))

# سطوح دسترسی مدیران (هرچی عدد بزرگتر، دسترسی بیشتر)
ROLE_LEVELS = {
    "support": 1,
    "uploader": 2,
    "admin": 3,
    "owner": 4,
}

ROLE_LABELS = {
    "owner": "👑 مالک",
    "admin": "🛡 ادمین",
    "uploader": "📤 آپلودکننده",
    "support": "🎧 پشتیبان",
}

AUTO_DELETE_SECONDS = 60
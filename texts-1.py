"""
تمام متن‌های نمایش داده‌شده به کاربر/ادمین در همین فایل قرار دارند
تا مدیریت و ویرایش زبان ربات در یک‌جا متمرکز باشد.
هیچ رشته فارسی نباید مستقیم داخل فایل‌های handler نوشته شود.
"""


class Texts:
    # --- عمومی ---
    WELCOME_ADMIN = (
        "👋 سلام ادمین عزیز!\n"
        "از منوی زیر یکی از گزینه‌ها را انتخاب کنید، یا دستور /admin را بزنید."
    )
    WELCOME_USER = "👋 سلام! به ربات فیلم و سریال خوش آمدید."
    NOT_ADMIN = "⛔️ شما اجازه دسترسی به این بخش را ندارید."
    GENERIC_ERROR = "❌ خطایی پیش آمد. لطفاً دوباره تلاش کنید یا دستور /cancel را ارسال کنید."
    CANCELLED = "❌ عملیات لغو شد."

    BTN_ADD_MOVIE = "🎬 افزودن فیلم سینمایی"
    BTN_ADD_SERIES = "📺 افزودن سریال"

    MEDIA_TYPE_FA = {"movie": "فیلم", "series": "سریال"}

    # --- شروع افزودن محتوا ---
    ASK_CONTENT_TYPE = "چه نوع محتوایی می‌خواهید اضافه کنید؟"

    # --- جستجوی TMDB ---
    ASK_QUERY_MOVIE = "🎬 نام فیلم سینمایی مورد نظر را ارسال کنید (فارسی یا انگلیسی):"
    ASK_QUERY_SERIES = "📺 نام سریال مورد نظر را ارسال کنید (فارسی یا انگلیسی):"
    SEARCHING = "🔎 در حال جستجو..."
    NO_RESULTS = "❌ نتیجه‌ای برای «{query}» یافت نشد.\nلطفاً نام دیگری را امتحان کنید یا /cancel را بزنید."
    CHOOSE_RESULT = "🔎 موارد زیر یافت شد. مورد مدنظر را انتخاب کنید:"
    FETCHING_DETAILS = "📥 در حال دریافت اطلاعات کامل..."
    RESEARCH_PROMPT = "🔄 نام جدید را برای جستجوی مجدد ارسال کنید:"

    # --- پردازش Gemini ---
    PROCESSING_TEXT = "🧠 در حال پردازش و ترجمه متن..."

    # --- ذخیره‌سازی ---
    SAVED_SUCCESS = "✅ اطلاعات با موفقیت در پایگاه‌داده ذخیره شد."
    ALREADY_EXISTS = "⚠️ این فیلم/سریال قبلاً در پایگاه‌داده ثبت شده است."
    SAVE_ERROR = "❌ خطایی هنگام ذخیره‌سازی رخ داد. لطفاً دوباره تلاش کنید."

    # --- ویرایش پیش‌نمایش (در فرآیند افزودن) ---
    EDIT_CHOOSE_FIELD = "✏️ کدام بخش را می‌خواهید ویرایش کنید؟"
    EDIT_ASK_VALUE = "✏️ متن جدید را ارسال کنید:"
    EDIT_SAVED = "✅ تغییرات اعمال شد."
    EDIT_UPDATED = "✅ فیلد با موفقیت به‌روزرسانی شد."
    EDIT_INVALID_NUMBER = "❌ مقدار وارد شده باید عدد باشد. دوباره تلاش کنید:"

    # فیلدهای قابل‌ویرایش در پیش‌نمایش فرآیند افزودن
    EDIT_FIELD_LABELS = {
        "description_fa": "📝 خلاصه داستان فارسی",
        "channel_intro_fa": "📢 متن معرفی کانال",
        "genres_fa": "🎭 ژانر فارسی",
        "persian_title": "🔤 عنوان فارسی",
    }

    # فیلدهای قابل‌ویرایش در پنل مدیریت محتوا (کامل‌تر)
    EDIT_FIELD_LABELS_FULL = {
        "persian_title": "🔤 عنوان فارسی",
        "title": "🔤 عنوان اصلی",
        "year": "📅 سال",
        "description_fa": "📝 خلاصه داستان",
        "channel_intro_fa": "📢 متن معرفی کانال",
        "genres_fa": "🎭 ژانر",
        "director": "🎬 کارگردان",
        "actors": "👥 بازیگران",
        "country": "🌍 کشور",
        "runtime": "⏱ مدت زمان (دقیقه)",
        "rating": "⭐ امتیاز",
    }

    # --- فرآیند افزودن فیلم (مرحله فایل) ---
    ASK_MOVIE_FILE = "🎞 لطفاً فایل فیلم (ویدیو یا سند) را ارسال کنید:"
    NO_FILE_RECEIVED = "❌ فایلی دریافت نشد. لطفاً یک ویدیو یا سند ارسال کنید."
    FILE_RECEIVED_MOVIE = "✅ فایل فیلم دریافت شد."

    # --- فرآیند افزودن سریال ---
    ASK_SEASON_NUMBER = "📺 شماره فصلی که می‌خواهید اضافه کنید را وارد کنید (مثلاً 1):"
    INVALID_SEASON_NUMBER = "❌ شماره فصل باید یک عدد صحیح مثبت باشد. دوباره تلاش کنید:"
    ASK_EPISODES = (
        "🎞 حالت دریافت قسمت‌های فصل {season} فعال شد.\n"
        "قسمت‌ها را یکی‌یکی و به‌ترتیب ارسال کنید (نیازی به وارد کردن شماره قسمت نیست).\n"
        "بعد از پایان، روی «پایان فصل» بزنید."
    )
    EPISODE_SAVED = "✅ قسمت {episode} فصل {season} ذخیره شد. منتظر قسمت بعدی یا «پایان فصل» هستم."
    SEASON_FINISHED_BUTTON = "🏁 پایان فصل"
    SEASON_DONE = "✅ فصل {season} با {count} قسمت ذخیره شد."
    ASK_ANOTHER_SEASON = "فصل دیگری هم دارید؟"
    BTN_NEW_SEASON = "➕ فصل جدید"
    BTN_FINISH_SERIES = "✅ پایان و مشاهده پیش‌نمایش"
    NO_EPISODES_YET = "❌ هنوز هیچ قسمتی برای این فصل ارسال نشده. حداقل یک قسمت ارسال کنید."

    # --- انتشار در کانال ---
    PUBLISHED_TO_CHANNEL = "📢 پست در کانال منتشر/به‌روزرسانی شد."
    PUBLISH_ERROR = "❌ خطا در انتشار پست در کانال. مطمئن شوید ربات ادمین کانال است."
    GET_MOVIE_BUTTON = "🎬 دریافت فیلم از ربات"
    GET_SERIES_BUTTON = "📺 دریافت قسمت‌ها از ربات"

    # --- کیفیت فایل ---
    ASK_FILE_QUALITY = "🎚 کیفیت این فایل را انتخاب کنید:"
    FILE_SAVED = "✅ فایل با کیفیت {quality} ذخیره شد."

    # --- منوی پنل ادمین ---
    BTN_ADD_CONTENT = "➕ افزودن فیلم/سریال"
    BTN_MOVIE_LIST = "📚 لیست محتوا"
    BTN_USER_STATS = "📊 آمار"
    BTN_BROADCAST = "📨 ارسال همگانی"
    BTN_MOVIE_REQUESTS = "📥 درخواست‌های فیلم"
    BTN_EXIT_ADMIN = "⬅️ خروج از پنل ادمین"
    BTN_REQUEST_MOVIE = "🎯 درخواست فیلم"
    BTN_SETTINGS = "⚙ تنظیمات"

    ADMIN_PANEL_WELCOME = "🛠 به پنل مدیریت خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:"
    EXIT_ADMIN_DONE = "شما از پنل ادمین خارج شدید."

    # --- تنظیمات (ادمین‌ها و کانال‌های عضویت اجباری) ---
    SETTINGS_MENU = "⚙ تنظیمات ربات را انتخاب کنید:"
    BTN_MANAGE_ADMINS = "👤 مدیریت ادمین‌ها"
    BTN_MANAGE_FORCE_JOIN = "🔒 مدیریت کانال‌های عضویت اجباری"

    ASK_NEW_ADMIN_ID = "🆔 آیدی عددی (User ID) ادمین جدید را ارسال کنید:"
    INVALID_USER_ID = "❌ آیدی عددی نامعتبر است. دوباره تلاش کنید:"
    ADMIN_ADDED = "✅ ادمین جدید با آیدی {user_id} اضافه شد."
    ADMIN_ALREADY_MAIN = "⚠️ این کاربر از ادمین‌های اصلی (Environment) است و همیشه دسترسی دارد."
    ADMIN_LIST_HEADER = "👤 لیست ادمین‌ها:"
    ADMIN_LIST_EMPTY = "به‌جز ادمین‌های اصلی، ادمین دیگری ثبت نشده."
    BTN_ADD_ADMIN = "➕ افزودن ادمین"
    BTN_REMOVE_ADMIN = "➖ حذف ادمین"
    ASK_REMOVE_ADMIN_ID = "🆔 آیدی عددی ادمینی که می‌خواهید حذف کنید را ارسال کنید:"
    ADMIN_REMOVED = "✅ ادمین {user_id} حذف شد."
    CANNOT_REMOVE_MAIN_ADMIN = "⛔️ ادمین‌های اصلی (Environment) از داخل ربات قابل حذف نیستند."

    ASK_FORCE_JOIN_CHANNEL = (
        "🔒 آیدی عددی یا یوزرنیم کانال را ارسال کنید (مثل -1001234567890 یا @channel).\n"
        "توجه: ربات باید در آن کانال ادمین باشد."
    )
    FORCE_JOIN_CHANNEL_ADDED = "✅ کانال {chat_id} به لیست عضویت اجباری اضافه شد."
    FORCE_JOIN_CHANNEL_ADD_ERROR = "❌ امکان افزودن این کانال نبود. بررسی کنید ربات در آن ادمین باشد."
    FORCE_JOIN_LIST_HEADER = "🔒 کانال‌های عضویت اجباری فعلی:"
    FORCE_JOIN_LIST_EMPTY = "هیچ کانال عضویت اجباری‌ای ثبت نشده."
    BTN_ADD_FORCE_JOIN = "➕ افزودن کانال"
    BTN_REMOVE_FORCE_JOIN = "➖ حذف کانال"
    ASK_REMOVE_FORCE_JOIN_CHANNEL = "🆔 آیدی/یوزرنیم کانالی که می‌خواهید حذف کنید را ارسال کنید:"
    FORCE_JOIN_CHANNEL_REMOVED = "✅ کانال {chat_id} از لیست عضویت اجباری حذف شد."

    # --- لیست/مدیریت محتوا ---
    MOVIE_LIST_EMPTY = "هیچ فیلم/سریالی در پایگاه‌داده ثبت نشده است."
    MOVIE_LIST_HEADER = "📚 لیست محتوا (صفحه {page} از {total_pages}):"
    MOVIE_NOT_FOUND = "❌ محتوای مورد نظر یافت نشد."

    DELETE_CONFIRM = "⚠️ آیا از حذف «{title}» مطمئن هستید؟ این عملیات غیرقابل بازگشت است."
    DELETE_DONE = "🗑 حذف شد."
    DELETE_CANCELLED = "حذف لغو شد."

    # --- آمار ---
    USER_STATS = "📊 تعداد کل کاربران ربات: {count}"

    # --- ارسال همگانی ---
    ASK_BROADCAST_MESSAGE = "📨 پیام مورد نظر برای ارسال همگانی را بفرستید (متن، عکس، ویدیو و ...):"
    BROADCAST_CONFIRM = "آیا از ارسال این پیام به همه کاربران ({count} نفر) مطمئن هستید؟"
    BROADCAST_SENDING = "⏳ در حال ارسال..."
    BROADCAST_DONE = "✅ ارسال همگانی پایان یافت.\nموفق: {success}\nناموفق: {failed}"
    BROADCAST_CANCELLED = "ارسال همگانی لغو شد."

    # --- درخواست فیلم (کاربر) ---
    ASK_REQUEST_TEXT = "🎯 نام فیلم یا سریال مورد نظر خود را بنویسید:"
    REQUEST_SAVED = "✅ درخواست شما ثبت شد و به‌زودی بررسی می‌شود."
    NEW_REQUEST_ADMIN_NOTICE = "📥 درخواست جدید از کاربر {user_id}:\n{text}"

    # --- درخواست‌ها (ادمین) ---
    REQUEST_LIST_EMPTY = "درخواستی موجود نیست."
    REQUEST_LIST_HEADER = "📥 درخواست‌های در انتظار (صفحه {page} از {total_pages}):"

    # --- عضویت اجباری کانال ---
    JOIN_REQUIRED = "🔒 برای استفاده از ربات، ابتدا باید در کانال(های) زیر عضو شوید:"
    JOIN_BUTTON_PREFIX = "📢 عضویت در"
    CHECK_JOIN_BUTTON = "✅ عضو شدم، بررسی کن"
    JOIN_CHECK_FAILED = "❌ هنوز عضویت شما در همه کانال‌ها تأیید نشد."
    JOIN_CONFIRMED = "✅ عضویت شما تأیید شد."

    # --- تحویل فایل به کاربر ---
    DELIVER_CHOOSE_QUALITY = "🎚 کیفیت مورد نظر برای دریافت فیلم را انتخاب کنید:"
    DELIVER_CHOOSE_SEASON = "📺 فصل مورد نظر را انتخاب کنید:"
    DELIVER_CHOOSE_EPISODE = "🎞 قسمت مورد نظر را انتخاب کنید:"
    DELIVER_SENDING = "🎬 در حال ارسال فایل..."
    DELIVER_NO_FILE = "❌ فایلی برای این محتوا هنوز ثبت نشده است."
    DELIVER_AUTO_DELETE_NOTICE = (
        "⚠️ این فایل تا {seconds} ثانیه دیگر از این چت حذف می‌شود؛ لطفاً آن را ذخیره/فوروارد کنید."
    )

    @staticmethod
    def preview_movie(data: dict) -> str:
        """پیش‌نمایش فیلم قبل از ذخیره (پس از دریافت فایل)."""
        title = data.get("persian_title") or data.get("title")
        lines = [f"🎬 {title} ({data.get('title')})", "📁 نوع: فیلم سینمایی"]
        lines.extend(Texts._common_preview_lines(data))

        if data.get("description_fa"):
            lines.append(f"\n📝 خلاصه:\n{data['description_fa']}")
        if data.get("channel_intro_fa"):
            lines.append(f"\n📢 متن معرفی کانال:\n{data['channel_intro_fa']}")
        lines.append(
            f"\n🎞 فایل فیلم: {'✅ دریافت شد' if data.get('_file') else '❌ هنوز ارسال نشده'}"
        )
        return "\n".join(lines)

    @staticmethod
    def preview_series(data: dict, seasons_summary: list[tuple[int, int]]) -> str:
        """پیش‌نمایش سریال قبل از ذخیره (شامل خلاصه فصل‌ها/قسمت‌های آماده‌شده)."""
        title = data.get("persian_title") or data.get("title")
        lines = [f"📺 {title} ({data.get('title')})", "📁 نوع: سریال"]
        lines.extend(Texts._common_preview_lines(data))

        if data.get("description_fa"):
            lines.append(f"\n📝 خلاصه:\n{data['description_fa']}")
        if data.get("channel_intro_fa"):
            lines.append(f"\n📢 متن معرفی کانال:\n{data['channel_intro_fa']}")

        if seasons_summary:
            lines.append("\n📺 فصل‌های آماده‌شده برای انتشار:")
            for season_number, episode_count in seasons_summary:
                lines.append(f"  • فصل {season_number}: {episode_count} قسمت")
        else:
            lines.append("\n⚠️ هنوز هیچ فصلی اضافه نشده است.")

        return "\n".join(lines)

    @staticmethod
    def _common_preview_lines(data: dict) -> list[str]:
        lines = []
        if data.get("year"):
            lines.append(f"📅 سال ساخت: {data['year']}")
        if data.get("rating") is not None:
            lines.append(f"⭐ امتیاز: {data['rating']}")
        if data.get("genres_fa"):
            lines.append(f"🎭 ژانر: {data['genres_fa']}")
        if data.get("country"):
            lines.append(f"🌍 کشور: {data['country']}")
        if data.get("runtime"):
            lines.append(f"⏱ مدت زمان: {data['runtime']} دقیقه")
        if data.get("director"):
            lines.append(f"🎬 کارگردان: {data['director']}")
        if data.get("actors"):
            lines.append(f"👥 بازیگران: {data['actors']}")
        return lines

    @staticmethod
    def content_detail_text(content: dict, extra: str = "") -> str:
        """نمایش جزئیات یک فیلم/سریال در پنل مدیریت (لیست محتوا → مشاهده)."""
        media_fa = Texts.MEDIA_TYPE_FA.get(content.get("media_type"), "")
        title = content.get("persian_title") or content.get("title")

        lines = [f"🎬 {title} (#{content['id']})", f"📁 نوع: {media_fa}"]
        if content.get("year"):
            lines.append(f"📅 سال: {content['year']}")
        if content.get("rating") is not None:
            lines.append(f"⭐ امتیاز: {content['rating']}")
        if content.get("genres_fa"):
            lines.append(f"🎭 ژانر: {content['genres_fa']}")

        status_fa = "✅ منتشرشده در کانال" if content.get("published") else "❌ منتشرنشده"
        lines.append(f"📢 وضعیت انتشار: {status_fa}")
        if extra:
            lines.append(extra)

        return "\n".join(lines)

    @staticmethod
    def channel_post_movie(content: dict, qualities: list[str]) -> str:
        """متن پست کانال برای فیلم سینمایی."""
        title = content.get("persian_title") or content.get("title")
        lines = [f"🎬 {title}", "📁 نوع: فیلم سینمایی"]
        lines.extend(Texts._channel_common_lines(content))

        if qualities:
            lines.append(f"\n🎚 کیفیت‌های موجود: {', '.join(sorted(qualities))}")
        else:
            lines.append("\n⏳ فایل فیلم به‌زودی اضافه می‌شود.")

        lines.append("\n👇 برای دریافت فیلم روی دکمه زیر بزنید")
        return "\n".join(lines)

    @staticmethod
    def channel_post_series(content: dict, seasons_summary: list[tuple[int, int]]) -> str:
        """متن پست کانال برای سریال."""
        title = content.get("persian_title") or content.get("title")
        lines = [f"📺 {title}", "📁 نوع: سریال"]
        lines.extend(Texts._channel_common_lines(content))

        if seasons_summary:
            lines.append("\n📺 فصل‌های موجود:")
            for season_number, episode_count in seasons_summary:
                lines.append(f"  • فصل {season_number}: {episode_count} قسمت")
        else:
            lines.append("\n⏳ قسمت‌ها به‌زودی اضافه می‌شوند.")

        lines.append("\n👇 برای دریافت قسمت‌ها روی دکمه زیر بزنید")
        return "\n".join(lines)

    @staticmethod
    def _channel_common_lines(content: dict) -> list[str]:
        lines = []
        if content.get("year"):
            lines.append(f"📅 سال انتشار: {content['year']}")
        if content.get("genres_fa"):
            lines.append(f"🎭 ژانر: {content['genres_fa']}")
        if content.get("rating") is not None:
            lines.append(f"⭐ امتیاز: {content['rating']}")

        description = content.get("description_fa") or content.get("description_en")
        if description:
            lines.append(f"\n📝 خلاصه داستان:\n{description}")
        return lines


texts = Texts()

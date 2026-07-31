"""
ماژول افزودن «سریال» توسط ادمین.

جریان کار (کاملاً جدا از افزودن فیلم سینمایی - add_movie.py):
۱. دریافت نام سریال.
۲. جستجو و دریافت اطلاعات از TMDB.
۳. تولید توضیحات فارسی با Gemini.
۴. پرسیدن شماره فصل.
۵. ورود به «حالت دریافت قسمت‌ها»: ادمین می‌تواند پشت‌سرهم و بدون تکرار
   مراحل، هر تعداد فایل (قسمت) ارسال کند؛ شماره قسمت به‌صورت خودکار
   افزایش می‌یابد (نیازی به وارد کردن شماره قسمت نیست).
۶. با زدن «پایان فصل»، همه قسمت‌های آن فصل در حافظه موقت ذخیره و
   سؤال «فصل دیگری هم دارید؟» پرسیده می‌شود (➕ فصل جدید / ✅ پایان).
۷. پس از پایان، پیش‌نمایش کامل (شامل خلاصه هر فصل) نمایش داده می‌شود.
۸. فقط با زدن «✅ انتشار» در پیش‌نمایش نهایی، سریال و تمام فصل‌ها/قسمت‌ها
   در دیتابیس ذخیره و پست آن در کانال منتشر می‌شود.

هیچ داده‌ای (هیچ قسمتی) قبل از تأیید نهایی در دیتابیس دائمی ذخیره
نمی‌شود؛ همه‌چیز تا لحظه‌ی «انتشار» فقط در context.user_data (حافظه
موقت مکالمه) نگه‌داری می‌شود تا اگر ادمین منصرف شد، هیچ داده‌ی نصفه/
ناقصی وارد پایگاه‌داده نشود.
"""
import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from channel_publish import publish_series
from config import config
from keyboards import episode_collection_menu
from repository import (
    ContentAlreadyExistsError,
    add_episode,
    create_season,
    insert_content,
)
from inline import edit_fields_keyboard, preview_keyboard, results_keyboard, season_action_keyboard
import gemini_service
import tmdb_service
from texts import texts

logger = logging.getLogger(__name__)

# --- states ---
(
    ASK_QUERY, CHOOSE_RESULT, ASK_SEASON_NUMBER, COLLECT_EPISODES,
    SEASON_DECISION, FINAL_PREVIEW, EDIT_CHOOSE_FIELD, EDIT_WAIT_VALUE,
) = range(8)

# --- کلیدهای context.user_data (فضای نام مجزا تا با add_movie.py تداخل نکند) ---
DATA_KEY = "addseries_data"
SEASONS_KEY = "addseries_seasons"          # dict[int season_number] -> list[{"file_id","file_type"}]
CURRENT_SEASON_KEY = "addseries_current_season"
EDIT_FIELD_KEY = "addseries_edit_field"

PREFIX = "serprev"
EDIT_PREFIX = "seredit"


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def _reset_conversation_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(DATA_KEY, None)
    context.user_data.pop(SEASONS_KEY, None)
    context.user_data.pop(CURRENT_SEASON_KEY, None)
    context.user_data.pop(EDIT_FIELD_KEY, None)


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text(texts.NOT_ADMIN)
        return ConversationHandler.END

    _reset_conversation_data(context)
    await update.message.reply_text(texts.ASK_QUERY_SERIES)
    return ASK_QUERY


async def receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip()
    await update.message.reply_text(texts.SEARCHING)

    try:
        raw_results = await tmdb_service.search_title(query)
    except Exception:
        logger.exception("خطا در جستجوی TMDB (سریال)")
        await update.message.reply_text(texts.GENERIC_ERROR)
        return ASK_QUERY

    raw_results = [r for r in raw_results if r.get("media_type") == "series"]
    if not raw_results:
        await update.message.reply_text(texts.NO_RESULTS.format(query=query))
        return ASK_QUERY

    prepared = []
    for r in raw_results[:6]:
        title = r.get("name") or r.get("title")
        date = (r.get("first_air_date") or "")[:4]
        label = f"{title} ({date}) - سریال" if date else f"{title} - سریال"
        prepared.append({"tmdb_id": r["id"], "media_type": "series", "label": label})

    await update.message.reply_text(
        texts.CHOOSE_RESULT, reply_markup=results_keyboard(prepared, cancel_callback=f"{PREFIX}_cancel")
    )
    return CHOOSE_RESULT


async def choose_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == f"{PREFIX}_cancel":
        await query.edit_message_text(texts.CANCELLED)
        return ConversationHandler.END

    _, tmdb_id_str, media_type = query.data.split("_", 2)
    await query.edit_message_text(texts.FETCHING_DETAILS)

    try:
        details = await tmdb_service.get_details(int(tmdb_id_str), media_type)
    except Exception:
        logger.exception("خطا در دریافت جزئیات از TMDB (سریال)")
        await query.message.reply_text(texts.GENERIC_ERROR)
        return ConversationHandler.END

    await query.message.reply_text(texts.PROCESSING_TEXT)
    gemini_result = await gemini_service.process_movie_text(details)
    details.update(gemini_result)

    context.user_data[DATA_KEY] = details
    context.user_data[SEASONS_KEY] = {}

    await query.message.reply_text(texts.preview_series(details, seasons_summary=[]))
    await query.message.reply_text(texts.ASK_SEASON_NUMBER)
    return ASK_SEASON_NUMBER


async def receive_season_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text(texts.INVALID_SEASON_NUMBER)
        return ASK_SEASON_NUMBER

    season_number = int(raw)
    context.user_data[CURRENT_SEASON_KEY] = season_number

    seasons = context.user_data.setdefault(SEASONS_KEY, {})
    seasons.setdefault(season_number, [])

    await update.message.reply_text(
        texts.ASK_EPISODES.format(season=season_number),
        reply_markup=episode_collection_menu(),
    )
    return COLLECT_EPISODES


async def collect_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    season_number = context.user_data.get(CURRENT_SEASON_KEY)
    seasons = context.user_data.setdefault(SEASONS_KEY, {})
    episodes = seasons.setdefault(season_number, [])

    file_id = None
    file_type = None
    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"

    if not file_id:
        await message.reply_text(texts.NO_FILE_RECEIVED)
        return COLLECT_EPISODES

    episodes.append({"file_id": file_id, "file_type": file_type})
    seasons[season_number] = episodes
    context.user_data[SEASONS_KEY] = seasons

    await message.reply_text(
        texts.EPISODE_SAVED.format(episode=len(episodes), season=season_number)
    )
    return COLLECT_EPISODES


async def finish_season(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    season_number = context.user_data.get(CURRENT_SEASON_KEY)
    seasons = context.user_data.get(SEASONS_KEY, {})
    episodes = seasons.get(season_number, [])

    if not episodes:
        await update.message.reply_text(texts.NO_EPISODES_YET)
        return COLLECT_EPISODES

    await update.message.reply_text(
        texts.SEASON_DONE.format(season=season_number, count=len(episodes)),
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(texts.ASK_ANOTHER_SEASON, reply_markup=season_action_keyboard())
    return SEASON_DECISION


async def season_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "season_new":
        await query.edit_message_text(texts.ASK_SEASON_NUMBER)
        return ASK_SEASON_NUMBER

    # season_finish_series
    data = context.user_data.get(DATA_KEY, {})
    seasons = context.user_data.get(SEASONS_KEY, {})
    seasons_summary = [(num, len(eps)) for num, eps in sorted(seasons.items()) if eps]

    if not seasons_summary:
        await query.edit_message_text(texts.NO_EPISODES_YET)
        return ConversationHandler.END

    await query.edit_message_text(texts.preview_series(data, seasons_summary))
    await _send_final_preview(update, context, data, seasons_summary)
    return FINAL_PREVIEW


async def _send_final_preview(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict, seasons_summary: list
) -> None:
    caption = texts.preview_series(data, seasons_summary)
    chat = update.effective_chat

    if data.get("poster_url"):
        await context.bot.send_photo(
            chat_id=chat.id,
            photo=data["poster_url"],
            caption=caption,
            reply_markup=preview_keyboard(PREFIX, allow_research=False),
        )
    else:
        await context.bot.send_message(
            chat_id=chat.id,
            text=caption,
            reply_markup=preview_keyboard(PREFIX, allow_research=False),
        )


async def final_preview_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    data = context.user_data.get(DATA_KEY)
    seasons = context.user_data.get(SEASONS_KEY, {})
    seasons_summary = [(num, len(eps)) for num, eps in sorted(seasons.items()) if eps]

    if action == f"{PREFIX}_cancel":
        await query.message.reply_text(texts.CANCELLED)
        _reset_conversation_data(context)
        return ConversationHandler.END

    if action == f"{PREFIX}_edit":
        await query.message.reply_text(
            texts.EDIT_CHOOSE_FIELD,
            reply_markup=edit_fields_keyboard(EDIT_PREFIX, back_callback=f"{EDIT_PREFIX}_back"),
        )
        return EDIT_CHOOSE_FIELD

    if action == f"{PREFIX}_confirm":
        if not data or not seasons_summary:
            await query.message.reply_text(texts.GENERIC_ERROR)
            return ConversationHandler.END

        try:
            content_id = await insert_content(data, created_by=update.effective_user.id)
            for season_number, episodes in sorted(seasons.items()):
                if not episodes:
                    continue
                season_id = await create_season(content_id, season_number)
                for index, episode in enumerate(episodes, start=1):
                    await add_episode(
                        season_id, index, episode["file_id"], episode["file_type"]
                    )
        except ContentAlreadyExistsError:
            await query.message.reply_text(texts.ALREADY_EXISTS)
            _reset_conversation_data(context)
            return ConversationHandler.END
        except Exception:
            logger.exception("خطا در ذخیره‌سازی سریال در دیتابیس")
            await query.message.reply_text(texts.SAVE_ERROR)
            return ConversationHandler.END

        await query.message.reply_text(texts.SAVED_SUCCESS)
        published = await publish_series(context.bot, content_id)
        await query.message.reply_text(
            texts.PUBLISHED_TO_CHANNEL if published else texts.PUBLISH_ERROR
        )

        _reset_conversation_data(context)
        return ConversationHandler.END

    return FINAL_PREVIEW


async def edit_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == f"{EDIT_PREFIX}_back":
        data = context.user_data.get(DATA_KEY, {})
        seasons = context.user_data.get(SEASONS_KEY, {})
        seasons_summary = [(num, len(eps)) for num, eps in sorted(seasons.items()) if eps]
        await _send_final_preview(update, context, data, seasons_summary)
        return FINAL_PREVIEW

    field = query.data.replace(f"{EDIT_PREFIX}_", "", 1)
    context.user_data[EDIT_FIELD_KEY] = field
    await query.message.reply_text(texts.EDIT_ASK_VALUE)
    return EDIT_WAIT_VALUE


async def edit_wait_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.get(EDIT_FIELD_KEY)
    new_value = update.message.text.strip()

    data = context.user_data.get(DATA_KEY, {})
    if field:
        data[field] = new_value
    context.user_data[DATA_KEY] = data

    seasons = context.user_data.get(SEASONS_KEY, {})
    seasons_summary = [(num, len(eps)) for num, eps in sorted(seasons.items()) if eps]

    await update.message.reply_text(texts.EDIT_SAVED)
    await _send_final_preview(update, context, data, seasons_summary)
    return FINAL_PREVIEW


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _reset_conversation_data(context)
    await update.message.reply_text(texts.CANCELLED, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def get_add_series_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("addseries", entry),
            MessageHandler(filters.Regex(f"^{texts.BTN_ADD_SERIES}$"), entry),
        ],
        states={
            ASK_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_query)],
            CHOOSE_RESULT: [
                CallbackQueryHandler(choose_result, pattern=r"^(pick_.*|serprev_cancel)$")
            ],
            ASK_SEASON_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_season_number)
            ],
            COLLECT_EPISODES: [
                MessageHandler(
                    filters.Regex(f"^{texts.SEASON_FINISHED_BUTTON}$"), finish_season
                ),
                MessageHandler(filters.VIDEO | filters.Document.ALL, collect_episodes),
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_episodes),
            ],
            SEASON_DECISION: [
                CallbackQueryHandler(season_decision, pattern=r"^season_")
            ],
            FINAL_PREVIEW: [CallbackQueryHandler(final_preview_actions, pattern=f"^{PREFIX}_")],
            EDIT_CHOOSE_FIELD: [CallbackQueryHandler(edit_choose_field, pattern=f"^{EDIT_PREFIX}_")],
            EDIT_WAIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_wait_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="add_series_conversation",
        persistent=False,
    )

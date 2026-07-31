"""
لایه دسترسی به دیتابیس (محتوا/فیلم/سریال، فایل‌ها، فصل/قسمت‌ها، ادمین‌ها،
کانال‌های عضویت اجباری، کاربران، درخواست‌ها).
هر عملیات جدید دیتابیس باید در همین فایل اضافه شود تا کوئری‌های SQL در
جای واحدی متمرکز بمانند.
"""
import asyncpg

from connection import get_pool


class ContentAlreadyExistsError(Exception):
    """زمانی که فیلم/سریال با همان tmdb_id و media_type قبلاً ثبت شده باشد."""


# ==================== محتوا (فیلم و سریال) ====================

_INSERT_QUERY = """
INSERT INTO content (
    tmdb_id, media_type, title, original_title, persian_title,
    poster_url, year, genres_fa, rating, country, runtime,
    actors, director, description_en, description_fa, channel_intro_fa,
    number_of_seasons, number_of_episodes, created_by
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
    $11, $12, $13, $14, $15, $16, $17, $18, $19
)
RETURNING id;
"""


async def insert_content(data: dict, created_by: int) -> int:
    """ذخیره یک فیلم/سریال جدید (پیش‌نویس، هنوز منتشرنشده)."""
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                _INSERT_QUERY,
                data.get("tmdb_id"),
                data.get("media_type"),
                data.get("title"),
                data.get("original_title"),
                data.get("persian_title"),
                data.get("poster_url"),
                data.get("year"),
                data.get("genres_fa"),
                data.get("rating"),
                data.get("country"),
                data.get("runtime"),
                data.get("actors"),
                data.get("director"),
                data.get("description_en"),
                data.get("description_fa"),
                data.get("channel_intro_fa"),
                data.get("number_of_seasons"),
                data.get("number_of_episodes"),
                created_by,
            )
        return row["id"]
    except asyncpg.UniqueViolationError as exc:
        raise ContentAlreadyExistsError() from exc


async def get_content_by_tmdb_id(tmdb_id: int, media_type: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM content WHERE tmdb_id = $1 AND media_type = $2",
            tmdb_id, media_type,
        )


async def get_content_by_id(content_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM content WHERE id = $1", content_id)


async def list_content(
    limit: int = 10, offset: int = 0, search: str | None = None, media_type: str | None = None
):
    """لیست فیلم‌ها/سریال‌ها برای نمایش در پنل ادمین (جدیدترین‌ها اول)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params: list = []

        if search:
            params.append(f"%{search}%")
            conditions.append(f"(title ILIKE ${len(params)} OR persian_title ILIKE ${len(params)})")
        if media_type:
            params.append(media_type)
            conditions.append(f"media_type = ${len(params)}")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        return await conn.fetch(
            f"""
            SELECT id, title, persian_title, year, media_type, published
            FROM content
            {where}
            ORDER BY created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )


async def count_content(search: str | None = None, media_type: str | None = None) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params: list = []

        if search:
            params.append(f"%{search}%")
            conditions.append(f"(title ILIKE ${len(params)} OR persian_title ILIKE ${len(params)})")
        if media_type:
            params.append(media_type)
            conditions.append(f"media_type = ${len(params)}")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        row = await conn.fetchrow(f"SELECT COUNT(*) AS c FROM content {where}", *params)
        return row["c"]


# فیلدهایی که ادمین اجازه ویرایش آن‌ها را دارد. کوئری UPDATE با f-string فقط
# روی نام ستون ساخته می‌شود و چون نام ستون همیشه از این مجموعه ثابت انتخاب
# می‌شود (نه از ورودی خام کاربر)، خطر SQL Injection وجود ندارد.
_EDITABLE_TEXT_FIELDS = {
    "title", "persian_title", "genres_fa", "description_fa",
    "channel_intro_fa", "director", "actors", "country",
}
_EDITABLE_NUMERIC_FIELDS = {"year": int, "runtime": int, "rating": float}
_EDITABLE_FIELDS = _EDITABLE_TEXT_FIELDS | set(_EDITABLE_NUMERIC_FIELDS)


async def update_content_field(content_id: int, field: str, raw_value: str) -> None:
    """ویرایش یک فیلد از یک فیلم/سریال. برای فیلدهای عددی، raw_value تبدیل نوع می‌شود."""
    if field not in _EDITABLE_FIELDS:
        raise ValueError(f"فیلد قابل ویرایش نیست: {field}")

    value: object = raw_value
    if field in _EDITABLE_NUMERIC_FIELDS:
        try:
            value = _EDITABLE_NUMERIC_FIELDS[field](raw_value)
        except (TypeError, ValueError):
            raise ValueError(f"مقدار عددی نامعتبر برای فیلد {field}") from None

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE content SET {field} = $1, updated_at = NOW() WHERE id = $2",
            value, content_id,
        )


async def delete_content(content_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM content WHERE id = $1", content_id)


async def mark_content_published(content_id: int, channel_message_id: int | None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE content SET published = TRUE, channel_message_id = $1, updated_at = NOW() "
            "WHERE id = $2",
            channel_message_id, content_id,
        )


# ==================== فایل‌های فیلم (کیفیت‌ها) ====================

async def add_content_file(content_id: int, quality: str, file_id: str, file_type: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO content_files (content_id, quality, file_id, file_type)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (content_id, quality)
            DO UPDATE SET file_id = EXCLUDED.file_id, file_type = EXCLUDED.file_type
            """,
            content_id, quality, file_id, file_type,
        )


async def get_content_files(content_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT quality, file_id, file_type FROM content_files "
            "WHERE content_id = $1 ORDER BY quality",
            content_id,
        )


async def delete_content_file(content_id: int, quality: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM content_files WHERE content_id = $1 AND quality = $2",
            content_id, quality,
        )


# ==================== سریال: فصل‌ها و قسمت‌ها ====================

async def create_season(content_id: int, season_number: int) -> int:
    """ایجاد یک فصل جدید برای یک سریال (اگر از قبل وجود داشت، همان id برگردانده می‌شود)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO series_seasons (content_id, season_number)
            VALUES ($1, $2)
            ON CONFLICT (content_id, season_number) DO UPDATE SET content_id = EXCLUDED.content_id
            RETURNING id
            """,
            content_id, season_number,
        )
        return row["id"]


async def add_episode(
    season_id: int,
    episode_number: int,
    file_id: str,
    file_type: str,
    quality: str | None = None,
    language: str | None = None,
    is_dubbed: bool = False,
    has_subtitle: bool = False,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO series_episodes (
                season_id, episode_number, file_id, file_type,
                quality, language, is_dubbed, has_subtitle
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (season_id, episode_number)
            DO UPDATE SET file_id = EXCLUDED.file_id, file_type = EXCLUDED.file_type,
                          quality = EXCLUDED.quality, language = EXCLUDED.language,
                          is_dubbed = EXCLUDED.is_dubbed, has_subtitle = EXCLUDED.has_subtitle
            """,
            season_id, episode_number, file_id, file_type,
            quality, language, is_dubbed, has_subtitle,
        )


async def count_episodes(season_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS c FROM series_episodes WHERE season_id = $1", season_id
        )
        return row["c"]


async def get_seasons(content_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM series_seasons WHERE content_id = $1 ORDER BY season_number",
            content_id,
        )


async def get_season(season_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM series_seasons WHERE id = $1", season_id)


async def get_season_by_number(content_id: int, season_number: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM series_seasons WHERE content_id = $1 AND season_number = $2",
            content_id, season_number,
        )


async def get_episodes(season_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM series_episodes WHERE season_id = $1 ORDER BY episode_number",
            season_id,
        )


async def get_episode(season_id: int, episode_number: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM series_episodes WHERE season_id = $1 AND episode_number = $2",
            season_id, episode_number,
        )


async def mark_season_published(season_id: int, channel_message_id: int | None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE series_seasons SET published = TRUE, channel_message_id = $1 WHERE id = $2",
            channel_message_id, season_id,
        )


# ==================== ادمین‌ها (چند ادمین) ====================

async def add_admin(user_id: int, added_by: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO admins (user_id, added_by) VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id, added_by,
        )


async def remove_admin(user_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE user_id = $1", user_id)


async def is_admin_in_db(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM admins WHERE user_id = $1", user_id)
        return row is not None


async def list_admins():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, added_by, added_at FROM admins ORDER BY added_at")


# ==================== کانال‌های عضویت اجباری ====================

async def add_force_join_channel(
    chat_id: str, title: str | None, invite_link: str | None, added_by: int
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO force_join_channels (chat_id, title, invite_link, added_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (chat_id) DO UPDATE SET title = EXCLUDED.title,
                                                invite_link = EXCLUDED.invite_link
            """,
            chat_id, title, invite_link, added_by,
        )


async def remove_force_join_channel(chat_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM force_join_channels WHERE chat_id = $1", chat_id)


async def list_force_join_channels():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT id, chat_id, title, invite_link FROM force_join_channels ORDER BY added_at"
        )


# ==================== کاربران ====================

async def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id)
            DO UPDATE SET username = EXCLUDED.username,
                          first_name = EXCLUDED.first_name,
                          last_seen_at = NOW()
            """,
            user_id, username, first_name,
        )


async def count_users() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) AS c FROM users")
        return row["c"]


async def get_all_user_ids() -> list[int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users")
        return [r["user_id"] for r in rows]


# ==================== درخواست فیلم/سریال ====================

async def create_movie_request(user_id: int, query_text: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO movie_requests (user_id, query_text) VALUES ($1, $2) RETURNING id",
            user_id, query_text,
        )
        return row["id"]


async def list_pending_requests(limit: int = 10, offset: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT id, user_id, query_text, created_at
            FROM movie_requests
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )


async def count_pending_requests() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS c FROM movie_requests WHERE status = 'pending'"
        )
        return row["c"]


async def mark_request_done(request_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE movie_requests SET status = 'done' WHERE id = $1", request_id)

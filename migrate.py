"""
اجراکننده Migration های دیتابیس.

برای اینکه پروژه کاملاً «تخت» (بدون زیرپوشه) بماند، متن SQL هر Migration
مستقیم داخل همین فایل به‌صورت رشته نگه‌داری می‌شود (نه فایل .sql جدا).

هر Migration فقط یک‌بار اجرا می‌شود و در جدول schema_migrations ثبت
می‌گردد. برای قابلیت‌های بعدی، کافی‌ست یک آیتم جدید به لیست MIGRATIONS
اضافه کنید (با نام منحصربه‌فرد)؛ هرگز آیتم‌های قبلی را تغییر یا حذف
نکنید، چون این باعث پاک‌شدن یا خرابی داده‌های موجود می‌شود.
هیچ Migration نباید شامل DROP یا DELETE روی داده‌های واقعی باشد.
"""
import logging

import asyncpg

from config import config

logger = logging.getLogger(__name__)


MIGRATIONS: list[tuple[str, str]] = [
    (
        "001_create_movies_table",
        """
        CREATE TABLE IF NOT EXISTS movies (
            id                  SERIAL PRIMARY KEY,
            tmdb_id             INTEGER NOT NULL,
            media_type          VARCHAR(10) NOT NULL,      -- 'movie' یا 'tv'
            title               TEXT NOT NULL,
            original_title      TEXT,
            persian_title       TEXT,
            poster_url          TEXT,
            year                INTEGER,
            genres              TEXT,
            genres_fa           TEXT,
            rating              NUMERIC(3, 1),
            country             TEXT,
            runtime             INTEGER,
            actors              TEXT,
            director            TEXT,
            description_en      TEXT,
            description_fa      TEXT,
            channel_intro_fa    TEXT,
            number_of_seasons   INTEGER,
            number_of_episodes  INTEGER,
            status              VARCHAR(20) NOT NULL DEFAULT 'saved',
            created_by          BIGINT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_movies_tmdb_id UNIQUE (tmdb_id)
        );

        CREATE INDEX IF NOT EXISTS idx_movies_title ON movies (title);
        CREATE INDEX IF NOT EXISTS idx_movies_persian_title ON movies (persian_title);
        CREATE INDEX IF NOT EXISTS idx_movies_media_type ON movies (media_type);
        """,
    ),
    (
        "002_movies_publish_fields",
        """
        ALTER TABLE movies ADD COLUMN IF NOT EXISTS published BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE movies ADD COLUMN IF NOT EXISTS channel_message_id BIGINT;
        """,
    ),
    (
        "003_create_movie_files_table",
        """
        CREATE TABLE IF NOT EXISTS movie_files (
            id          SERIAL PRIMARY KEY,
            movie_id    INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            quality     VARCHAR(20) NOT NULL,
            file_id     TEXT NOT NULL,
            file_type   VARCHAR(20) NOT NULL,   -- 'video' یا 'document'
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_movie_files_movie_quality UNIQUE (movie_id, quality)
        );

        CREATE INDEX IF NOT EXISTS idx_movie_files_movie_id ON movie_files (movie_id);
        """,
    ),
    (
        "004_create_users_table",
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id       BIGINT PRIMARY KEY,
            username      TEXT,
            first_name    TEXT,
            joined_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
    ),
    (
        "005_create_movie_requests_table",
        """
        CREATE TABLE IF NOT EXISTS movie_requests (
            id          SERIAL PRIMARY KEY,
            user_id     BIGINT NOT NULL,
            query_text  TEXT NOT NULL,
            status      VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_movie_requests_status ON movie_requests (status);
        """,
    ),
    # ==================================================================
    # نسخه سوم به بعد: تفکیک کامل فیلم/سریال، چند ادمین، چند کانال عضویت اجباری.
    # جدول‌های قدیمی movies/movie_files هرگز حذف نمی‌شوند؛ فقط تغییر نام و
    # گسترش داده می‌شوند تا هیچ داده‌ای از دست نرود.
    # ==================================================================
    (
        "006_rename_movies_to_content",
        """
        ALTER TABLE movies RENAME TO content;
        ALTER TABLE content RENAME COLUMN media_type TO media_type_old;
        ALTER TABLE content ADD COLUMN IF NOT EXISTS media_type VARCHAR(10);
        UPDATE content SET media_type = CASE
            WHEN media_type_old = 'tv' THEN 'series'
            ELSE media_type_old
        END WHERE media_type IS NULL;
        ALTER TABLE content ALTER COLUMN media_type SET NOT NULL;
        ALTER TABLE content DROP COLUMN media_type_old;

        ALTER TABLE movie_files RENAME TO content_files;
        ALTER TABLE content_files RENAME COLUMN movie_id TO content_id;
        ALTER TABLE content_files RENAME CONSTRAINT uq_movie_files_movie_quality
            TO uq_content_files_content_quality;

        CREATE INDEX IF NOT EXISTS idx_content_media_type ON content (media_type);
        """,
    ),
    (
        "007_create_series_tables",
        """
        CREATE TABLE IF NOT EXISTS series_seasons (
            id                  SERIAL PRIMARY KEY,
            content_id          INTEGER NOT NULL REFERENCES content(id) ON DELETE CASCADE,
            season_number       INTEGER NOT NULL,
            published           BOOLEAN NOT NULL DEFAULT FALSE,
            channel_message_id  BIGINT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_series_seasons_content_season UNIQUE (content_id, season_number)
        );

        CREATE TABLE IF NOT EXISTS series_episodes (
            id              SERIAL PRIMARY KEY,
            season_id       INTEGER NOT NULL REFERENCES series_seasons(id) ON DELETE CASCADE,
            episode_number  INTEGER NOT NULL,
            file_id         TEXT NOT NULL,
            file_type       VARCHAR(20) NOT NULL,   -- 'video' یا 'document'
            quality         VARCHAR(20),
            language        VARCHAR(50),
            is_dubbed       BOOLEAN NOT NULL DEFAULT FALSE,
            has_subtitle    BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_series_episodes_season_episode UNIQUE (season_id, episode_number)
        );

        CREATE INDEX IF NOT EXISTS idx_series_seasons_content_id ON series_seasons (content_id);
        CREATE INDEX IF NOT EXISTS idx_series_episodes_season_id ON series_episodes (season_id);
        """,
    ),
    (
        "008_create_admins_table",
        """
        CREATE TABLE IF NOT EXISTS admins (
            user_id     BIGINT PRIMARY KEY,
            added_by    BIGINT,
            added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
    ),
    (
        "009_create_force_join_channels_table",
        """
        CREATE TABLE IF NOT EXISTS force_join_channels (
            id            SERIAL PRIMARY KEY,
            chat_id       TEXT NOT NULL,
            title         TEXT,
            invite_link   TEXT,
            added_by      BIGINT,
            added_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_force_join_channels_chat_id UNIQUE (chat_id)
        );
        """,
    ),
]


async def run_migrations() -> None:
    conn = await asyncpg.connect(
        dsn=config.DATABASE_URL,
        ssl="require" if config.DB_SSL else None,
    )
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name        TEXT PRIMARY KEY,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        applied_rows = await conn.fetch("SELECT name FROM schema_migrations")
        applied = {row["name"] for row in applied_rows}

        for name, sql in MIGRATIONS:
            if name in applied:
                continue
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (name) VALUES ($1)", name
                )
            logger.info("✅ Migration اجرا شد: %s", name)
    finally:
        await conn.close()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migrations())

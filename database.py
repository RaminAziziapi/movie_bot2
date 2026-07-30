import os
import secrets
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("متغیر محیطی DATABASE_URL تنظیم نشده است.")
        _pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL, sslmode="require")
    return _pool


def get_connection():
    return get_pool().getconn()


def put_connection(conn):
    get_pool().putconn(conn)


def _run(query, params=None, fetch=None, commit=False):
    """اجرای کوئری با مدیریت خودکار اتصال. fetch: None/'one'/'all'"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            result = None
            if fetch == "one":
                result = cur.fetchone()
            elif fetch == "all":
                result = cur.fetchall()
        if commit:
            conn.commit()
        return result
    finally:
        put_connection(conn)


# ==================================================================
# ساخت جداول + مهاجرت امن (اگه ستون یا جدولی از قبل نبود، اضافه میشه
# و چیزی از دیتای موجود پاک نمیشه)
# ==================================================================

def create_tables() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # --- جداول پایه (مثل قبل) ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    season TEXT,
                    episode TEXT,
                    file_id TEXT NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id SERIAL PRIMARY KEY,
                    channel_username TEXT UNIQUE NOT NULL
                );
                """
            )

            # --- جداول جدید ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    role TEXT NOT NULL,
                    added_by BIGINT,
                    added_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS series (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    season TEXT,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id SERIAL PRIMARY KEY,
                    series_id INTEGER REFERENCES series(id) ON DELETE CASCADE,
                    episode_number INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    fulfilled_at TIMESTAMP
                );
                """
            )

            # --- مهاجرت امن ستون‌های جدید روی جدول users ---
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS joined_at TIMESTAMP DEFAULT NOW();")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE;")

        conn.commit()
    finally:
        put_connection(conn)


# ==================================================================
# کاربران (همون رفتار قبلی حفظ شده + توابع جدید)
# ==================================================================

def save_user(user_id: int, username: str) -> None:
    _run(
        """
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username;
        """,
        (user_id, username),
        commit=True,
    )


def get_users_count() -> int:
    return _run("SELECT COUNT(*) FROM users;", fetch="one", commit=False)[0]


def get_new_users_count(days: int = 1) -> int:
    return _run(
        "SELECT COUNT(*) FROM users WHERE joined_at >= NOW() - (%s || ' days')::interval;",
        (str(days),),
        fetch="one",
    )[0]


def get_all_user_ids():
    rows = _run("SELECT user_id FROM users WHERE COALESCE(is_blocked, FALSE) = FALSE;", fetch="all")
    return [r[0] for r in rows]


# ==================================================================
# فیلم‌ها (بدون تغییر در رفتار)
# ==================================================================

def save_movie(name: str, season: str, episode: str, file_id: str) -> int:
    row = _run(
        """
        INSERT INTO movies (name, season, episode, file_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """,
        (name, season, episode, file_id),
        fetch="one",
        commit=True,
    )
    return row[0]


def get_movies():
    return _run("SELECT id, name, season, episode FROM movies ORDER BY id DESC;", fetch="all")


def get_movie(movie_id):
    return _run(
        "SELECT id, name, season, episode, file_id FROM movies WHERE id = %s;",
        (movie_id,),
        fetch="one",
    )


def delete_movie(movie_id) -> None:
    _run("DELETE FROM movies WHERE id = %s;", (movie_id,), commit=True)


def get_movies_count() -> int:
    return _run("SELECT COUNT(*) FROM movies;", fetch="one")[0]


# ==================================================================
# کانال‌های اجباری (بدون تغییر در رفتار)
# ==================================================================

def add_channel(channel: str) -> None:
    _run(
        "INSERT INTO channels (channel_username) VALUES (%s) ON CONFLICT (channel_username) DO NOTHING;",
        (channel,),
        commit=True,
    )


def remove_channel(channel: str) -> None:
    _run("DELETE FROM channels WHERE channel_username = %s;", (channel,), commit=True)


def get_channels():
    rows = _run("SELECT channel_username FROM channels ORDER BY id;", fetch="all")
    return [r[0] for r in rows]


# ==================================================================
# مدیران
# ==================================================================

def add_admin(user_id: int, username: str, role: str, added_by: int) -> None:
    _run(
        """
        INSERT INTO admins (user_id, username, role, added_by)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET role = EXCLUDED.role, username = EXCLUDED.username;
        """,
        (user_id, username, role, added_by),
        commit=True,
    )


def remove_admin(user_id: int) -> None:
    _run("DELETE FROM admins WHERE user_id = %s;", (user_id,), commit=True)


def get_admins():
    return _run("SELECT user_id, username, role FROM admins ORDER BY added_at;", fetch="all")


def get_admin_role(user_id: int):
    row = _run("SELECT role FROM admins WHERE user_id = %s;", (user_id,), fetch="one")
    return row[0] if row else None


def get_admins_count() -> int:
    return _run("SELECT COUNT(*) FROM admins;", fetch="one")[0]


# ==================================================================
# سریال‌ها و قسمت‌ها
# ==================================================================

def add_series(name: str, season: str, created_by: int) -> int:
    row = _run(
        "INSERT INTO series (name, season, created_by) VALUES (%s, %s, %s) RETURNING id;",
        (name, season, created_by),
        fetch="one",
        commit=True,
    )
    return row[0]


def get_series(series_id):
    return _run("SELECT id, name, season, created_by FROM series WHERE id = %s;", (series_id,), fetch="one")


def get_series_list():
    return _run("SELECT id, name, season FROM series ORDER BY id DESC;", fetch="all")


def delete_series(series_id) -> None:
    _run("DELETE FROM series WHERE id = %s;", (series_id,), commit=True)


def get_series_count() -> int:
    return _run("SELECT COUNT(*) FROM series;", fetch="one")[0]


def _generate_episode_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8]


def add_episode(series_id: int, episode_number: int, file_id: str) -> str:
    code = _generate_episode_code()
    # اطمینان از یکتا بودن کد
    while _run("SELECT 1 FROM episodes WHERE code = %s;", (code,), fetch="one"):
        code = _generate_episode_code()

    _run(
        """
        INSERT INTO episodes (series_id, episode_number, file_id, code)
        VALUES (%s, %s, %s, %s);
        """,
        (series_id, episode_number, file_id, code),
        commit=True,
    )
    return code


def get_episodes(series_id):
    return _run(
        "SELECT id, episode_number, file_id, code FROM episodes WHERE series_id = %s ORDER BY episode_number;",
        (series_id,),
        fetch="all",
    )


def get_episode_by_code(code: str):
    return _run(
        """
        SELECT e.id, e.series_id, e.episode_number, e.file_id, s.name, s.season
        FROM episodes e JOIN series s ON s.id = e.series_id
        WHERE e.code = %s;
        """,
        (code,),
        fetch="one",
    )


def get_episodes_count() -> int:
    return _run("SELECT COUNT(*) FROM episodes;", fetch="one")[0]


def get_next_episode_number(series_id: int) -> int:
    row = _run(
        "SELECT COALESCE(MAX(episode_number), 0) FROM episodes WHERE series_id = %s;",
        (series_id,),
        fetch="one",
    )
    return row[0] + 1


# ==================================================================
# تنظیمات (متن استارت، قوانین، لینک پشتیبانی و ...)
# ==================================================================

def get_setting(key: str, default=None):
    row = _run("SELECT value FROM settings WHERE key = %s;", (key,), fetch="one")
    return row[0] if row else default


def set_setting(key: str, value: str) -> None:
    _run(
        """
        INSERT INTO settings (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        """,
        (key, value),
        commit=True,
    )


# ==================================================================
# درخواست‌های کاربران
# ==================================================================

def add_request(user_id: int, username: str, content: str) -> int:
    row = _run(
        "INSERT INTO requests (user_id, username, content) VALUES (%s, %s, %s) RETURNING id;",
        (user_id, username, content),
        fetch="one",
        commit=True,
    )
    return row[0]


def get_pending_requests():
    return _run(
        "SELECT id, user_id, username, content FROM requests WHERE status = 'pending' ORDER BY id;",
        fetch="all",
    )


def fulfill_request(request_id: int):
    row = _run("SELECT user_id FROM requests WHERE id = %s;", (request_id,), fetch="one")
    _run(
        "UPDATE requests SET status = 'fulfilled', fulfilled_at = NOW() WHERE id = %s;",
        (request_id,),
        commit=True,
    )
    return row[0] if row else None


# ==================================================================
# بکاپ (خروجی ساده از محتوای اصلی برای بازیابی احتمالی)
# ==================================================================

def export_backup() -> dict:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM movies;")
            movies = cur.fetchall()
            cur.execute("SELECT * FROM series;")
            series = cur.fetchall()
            cur.execute("SELECT * FROM episodes;")
            episodes = cur.fetchall()
            cur.execute("SELECT * FROM channels;")
            channels = cur.fetchall()
        return {
            "movies": movies,
            "series": series,
            "episodes": episodes,
            "channels": channels,
        }
    finally:
        put_connection(conn)


def restore_backup(data: dict) -> None:
    for m in data.get("movies", []):
        save_movie(m.get("name"), m.get("season"), m.get("episode"), m.get("file_id"))
    for ch in data.get("channels", []):
        add_channel(ch.get("channel_username"))
    series_id_map = {}
    for s in data.get("series", []):
        new_id = add_series(s.get("name"), s.get("season"), s.get("created_by"))
        series_id_map[s.get("id")] = new_id
    for e in data.get("episodes", []):
        old_series_id = e.get("series_id")
        new_series_id = series_id_map.get(old_series_id)
        if new_series_id:
            add_episode(new_series_id, e.get("episode_number"), e.get("file_id"))
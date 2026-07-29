import os
import psycopg2
from psycopg2 import pool

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("متغیر محیطی DATABASE_URL تنظیم نشده است.")
        _pool = psycopg2.pool.SimpleConnectionPool(1, 5, DATABASE_URL, sslmode="require")
    return _pool


def get_connection():
    return get_pool().getconn()


def put_connection(conn):
    get_pool().putconn(conn)


def create_tables() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
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
        conn.commit()
    finally:
        put_connection(conn)


def save_user(user_id: int, username: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, username)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username;
                """,
                (user_id, username),
            )
        conn.commit()
    finally:
        put_connection(conn)


def save_movie(name: str, season: str, episode: str, file_id: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO movies (name, season, episode, file_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (name, season, episode, file_id),
            )
            movie_id = cur.fetchone()[0]
        conn.commit()
        return movie_id
    finally:
        put_connection(conn)


def get_movies():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, season, episode FROM movies ORDER BY id DESC;")
            return cur.fetchall()
    finally:
        put_connection(conn)


def get_movie(movie_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, season, episode, file_id FROM movies WHERE id = %s;",
                (movie_id,),
            )
            return cur.fetchone()
    finally:
        put_connection(conn)


def delete_movie(movie_id) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM movies WHERE id = %s;", (movie_id,))
        conn.commit()
    finally:
        put_connection(conn)


def add_channel(channel: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO channels (channel_username)
                VALUES (%s)
                ON CONFLICT (channel_username) DO NOTHING;
                """,
                (channel,),
            )
        conn.commit()
    finally:
        put_connection(conn)


def remove_channel(channel: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM channels WHERE channel_username = %s;", (channel,))
        conn.commit()
    finally:
        put_connection(conn)


def get_channels():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT channel_username FROM channels ORDER BY id;")
            return [row[0] for row in cur.fetchall()]
    finally:
        put_connection(conn)


def get_users_count() -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            return cur.fetchone()[0]
    finally:
        put_connection(conn)


def get_movies_count() -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM movies;")
            return cur.fetchone()[0]
    finally:
        put_connection(conn)
"""
مدیریت Connection Pool برای اتصال به PostgreSQL با asyncpg.
"""
from typing import Optional

import asyncpg

from config import config

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=config.DATABASE_URL,
            min_size=1,
            max_size=5,
            ssl="require" if config.DB_SSL else None,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

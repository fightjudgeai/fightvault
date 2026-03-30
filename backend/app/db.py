"""Async database connection pool module using asyncpg.

Provides a connection pool initialized at app startup and closed at shutdown.
All DB interaction should go through the helper wrappers or the `get_db`
dependency so that connections are always returned to the pool properly.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level pool — set by init_pool() during app lifespan startup.
_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Create the asyncpg connection pool from settings.database_url.

    Called once during FastAPI lifespan startup. Raises if the connection
    cannot be established so the app fails fast on misconfiguration.
    """
    global _pool
    logger.info("Initialising asyncpg connection pool…")
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=20,
        command_timeout=60,
        # Supabase uses pgbouncer in transaction mode; statement-level cache
        # must be disabled.
        statement_cache_size=0,
    )
    logger.info("asyncpg pool ready.")


async def close_pool() -> None:
    """Gracefully close the connection pool.

    Called during FastAPI lifespan shutdown.
    """
    global _pool
    if _pool is not None:
        logger.info("Closing asyncpg connection pool…")
        await _pool.close()
        _pool = None
        logger.info("asyncpg pool closed.")


def get_pool() -> asyncpg.Pool:
    """Return the active pool; raises RuntimeError if uninitialised."""
    if _pool is None:
        raise RuntimeError(
            "Database pool is not initialised. "
            "Ensure init_pool() was called during app startup."
        )
    return _pool


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency that yields a checked-out connection.

    Usage::

        @router.get("/example")
        async def example(db: asyncpg.Connection = Depends(get_db)):
            row = await fetchrow(db, "SELECT 1")

    The connection is always returned to the pool, even on exception.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------


async def execute(
    conn: asyncpg.Connection,
    query: str,
    *args: Any,
) -> str:
    """Execute a DML statement (INSERT/UPDATE/DELETE) and return status tag."""
    return await conn.execute(query, *args)


async def fetch(
    conn: asyncpg.Connection,
    query: str,
    *args: Any,
) -> list[asyncpg.Record]:
    """Execute a SELECT and return all matching rows."""
    return await conn.fetch(query, *args)


async def fetchrow(
    conn: asyncpg.Connection,
    query: str,
    *args: Any,
) -> asyncpg.Record | None:
    """Execute a SELECT and return the first row or None."""
    return await conn.fetchrow(query, *args)


async def fetchval(
    conn: asyncpg.Connection,
    query: str,
    *args: Any,
    column: int = 0,
) -> Any:
    """Execute a SELECT and return a single scalar value or None."""
    return await conn.fetchval(query, *args, column=column)

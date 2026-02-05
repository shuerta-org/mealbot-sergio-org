"""Async PostgreSQL database connection layer using SQLAlchemy Core.

This module provides async engine initialization, connection pool management,
and a FastAPI dependency function for injecting database connections into
route handlers.

Reference: Go implementation vendor/github.com/johnamadeo/server/dbconn.go

Design Decision #1: Async Database Connection Pattern
- Global async engine at startup with connection pooling
- FastAPI dependency injection provides async connections per request
- Improves on Go implementation (new connection per request) with pooling
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
)

from .config import Settings, get_settings

# Global async engine with built-in connection pooling
_engine: AsyncEngine | None = None


def _format_database_url(url: str) -> str:
    """Convert DATABASE_URL to asyncpg format.

    Handles both local and Heroku-style DATABASE_URL formats by ensuring
    the postgresql+asyncpg:// prefix is used.

    Args:
        url: Database URL, potentially with postgresql:// prefix.

    Returns:
        str: Database URL with postgresql+asyncpg:// prefix.
    """
    # Handle postgres:// (Heroku style) and postgresql:// prefixes
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+asyncpg://"):
        # Already in correct format
        return url
    else:
        # Unknown format, return as-is and let SQLAlchemy handle errors
        return url


async def init_engine(settings: Settings | None = None) -> AsyncEngine:
    """Initialize and cache the async database engine.

    Creates a global engine instance with connection pooling configured.
    The engine is cached to ensure reuse across all requests.

    Args:
        settings: Application settings. If None, uses get_settings().

    Returns:
        AsyncEngine: The cached async database engine.
    """
    global _engine
    if _engine is None:
        if settings is None:
            settings = get_settings()

        database_url = _format_database_url(settings.database_url)

        _engine = create_async_engine(
            database_url,
            echo=False,
            # pool_pre_ping performs a health check on connections
            # before returning them from the pool
            pool_pre_ping=True,
            # Connection pool settings
            pool_size=5,
            max_overflow=10,
        )
    return _engine


async def dispose_engine() -> None:
    """Dispose of the database engine and release all connections.

    Should be called during application shutdown to properly clean up
    database resources.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


def reset_engine() -> None:
    """Reset the engine reference (for testing purposes).

    Note: This does NOT properly dispose of the engine. Use dispose_engine()
    for proper cleanup. This is only for test isolation.
    """
    global _engine
    _engine = None


async def get_connection(
    settings: Settings | None = None,
) -> AsyncGenerator[AsyncConnection, None]:
    """FastAPI dependency that yields database connections.

    This async generator provides a database connection from the pool
    and ensures it is properly released after use.

    Usage:
        @app.get("/example")
        async def example(conn: AsyncConnection = Depends(get_connection)):
            result = await conn.execute(text("SELECT 1"))
            return {"data": result.fetchall()}

    Args:
        settings: Application settings. If None, uses get_settings().

    Yields:
        AsyncConnection: A database connection from the pool.
    """
    engine = await init_engine(settings)
    async with engine.connect() as conn:
        yield conn


@asynccontextmanager
async def get_connection_context(
    settings: Settings | None = None,
) -> AsyncGenerator[AsyncConnection, None]:
    """Context manager for database connections.

    Alternative to the dependency injection pattern for use in
    non-route contexts (e.g., background tasks, CLI commands).

    Usage:
        async with get_connection_context() as conn:
            result = await conn.execute(text("SELECT 1"))

    Args:
        settings: Application settings. If None, uses get_settings().

    Yields:
        AsyncConnection: A database connection from the pool.
    """
    engine = await init_engine(settings)
    async with engine.connect() as conn:
        yield conn


@asynccontextmanager
async def lifespan(app: Any) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """FastAPI lifespan context manager for engine lifecycle.

    Initializes the database engine at startup and disposes of it
    at shutdown.

    Usage:
        from fastapi import FastAPI
        from app.database import lifespan

        app = FastAPI(lifespan=lifespan)

    Args:
        app: The FastAPI application instance.

    Yields:
        None
    """
    # Startup: Initialize the engine
    await init_engine()
    yield
    # Shutdown: Dispose of the engine
    await dispose_engine()


# Re-export text for convenience in query construction
__all__ = [
    "init_engine",
    "dispose_engine",
    "reset_engine",
    "get_connection",
    "get_connection_context",
    "lifespan",
    "text",
]

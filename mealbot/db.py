"""Database connection layer using SQLAlchemy Core.

This module provides database connection management with connection pooling,
mirroring the Go implementation's behavior where connections are created
per operation using the context manager pattern.
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import QueuePool

from mealbot.config import Config

# Global engine instance (initialized on first use or explicitly via init_db)
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Get or create the SQLAlchemy engine with connection pooling.

    Returns:
        SQLAlchemy Engine instance with connection pooling enabled.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            Config.get_database_url(),
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Enable connection health checks
        )
    return _engine


def init_db(database_url: Optional[str] = None) -> Engine:
    """Initialize the database engine.

    This function allows explicit initialization with a custom database URL,
    useful for testing.

    Args:
        database_url: Optional custom database URL. If not provided,
                     uses Config.get_database_url().

    Returns:
        Initialized SQLAlchemy Engine.
    """
    global _engine
    url = database_url or Config.get_database_url()
    _engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    return _engine


def close_db() -> None:
    """Close the database engine and dispose of all connections."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


@contextmanager
def get_db_connection() -> Generator[Connection, None, None]:
    """Context manager for database connections.

    This mirrors the Go pattern of creating a new connection per operation.
    The connection is automatically closed when exiting the context.

    Usage:
        with get_db_connection() as conn:
            result = conn.execute(text("SELECT * FROM organizations"))
            rows = result.fetchall()

    Yields:
        SQLAlchemy Connection object.
    """
    engine = get_engine()
    with engine.connect() as connection:
        yield connection


# Constants matching the Go implementation
DUPLICATE_KEY_ERR = "duplicate key value violates unique constraint"

# Re-export text for convenience when using this module
__all__ = [
    "get_engine",
    "init_db",
    "close_db",
    "get_db_connection",
    "DUPLICATE_KEY_ERR",
    "text",
]

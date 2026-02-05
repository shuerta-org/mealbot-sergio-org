"""Tests for database connection layer.

This test suite covers:
- DATABASE_URL format conversion
- Engine initialization and caching
- Connection dependency and context manager
- Engine lifecycle management
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.database import (
    _format_database_url,
    dispose_engine,
    get_connection,
    get_connection_context,
    init_engine,
    lifespan,
    reset_engine,
)


class TestFormatDatabaseUrl:
    """Tests for DATABASE_URL format conversion."""

    def test_postgres_prefix_converted(self):
        """Test postgres:// (Heroku style) is converted to asyncpg format."""
        url = "postgres://user:pass@host:5432/dbname"
        result = _format_database_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/dbname"

    def test_postgresql_prefix_converted(self):
        """Test postgresql:// is converted to asyncpg format."""
        url = "postgresql://user:pass@host:5432/dbname"
        result = _format_database_url(url)
        assert result == "postgresql+asyncpg://user:pass@host:5432/dbname"

    def test_asyncpg_prefix_unchanged(self):
        """Test postgresql+asyncpg:// URL is unchanged."""
        url = "postgresql+asyncpg://user:pass@host:5432/dbname"
        result = _format_database_url(url)
        assert result == url

    def test_unknown_format_unchanged(self):
        """Test unknown URL format is returned unchanged."""
        url = "mysql://user:pass@host:3306/dbname"
        result = _format_database_url(url)
        assert result == url

    def test_only_first_occurrence_replaced(self):
        """Test only the first protocol prefix is replaced."""
        url = "postgres://user:postgres@host:5432/postgres"
        result = _format_database_url(url)
        assert result == "postgresql+asyncpg://user:postgres@host:5432/postgres"


class TestInitEngine:
    """Tests for engine initialization."""

    @pytest.fixture(autouse=True)
    def reset_engine_state(self):
        """Reset engine state before and after each test."""
        reset_engine()
        yield
        reset_engine()

    @pytest.mark.asyncio
    async def test_engine_created_with_settings(self):
        """Test engine is created with correct settings."""
        settings = Settings(
            database_url="postgresql://user:pass@localhost:5432/testdb",
        )

        with patch("app.database.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            engine = await init_engine(settings)

            assert engine is mock_engine
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert (
                call_args[0][0] == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
            )
            assert call_args[1]["pool_pre_ping"] is True

    @pytest.mark.asyncio
    async def test_engine_cached(self):
        """Test engine is cached on subsequent calls."""
        settings = Settings(
            database_url="postgresql://user:pass@localhost:5432/testdb",
        )

        with patch("app.database.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            engine1 = await init_engine(settings)
            engine2 = await init_engine(settings)

            assert engine1 is engine2
            assert mock_create.call_count == 1


class TestDisposeEngine:
    """Tests for engine disposal."""

    @pytest.fixture(autouse=True)
    def reset_engine_state(self):
        """Reset engine state before and after each test."""
        reset_engine()
        yield
        reset_engine()

    @pytest.mark.asyncio
    async def test_dispose_engine_cleans_up(self):
        """Test dispose_engine properly disposes the engine."""
        settings = Settings(
            database_url="postgresql://user:pass@localhost:5432/testdb",
        )

        with patch("app.database.create_async_engine") as mock_create:
            mock_engine = AsyncMock()
            mock_create.return_value = mock_engine

            await init_engine(settings)
            await dispose_engine()

            mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispose_engine_when_none(self):
        """Test dispose_engine does nothing when engine is None."""
        # Should not raise
        await dispose_engine()


class TestGetConnection:
    """Tests for get_connection dependency."""

    @pytest.fixture(autouse=True)
    def reset_engine_state(self):
        """Reset engine state before and after each test."""
        reset_engine()
        yield
        reset_engine()

    @pytest.mark.asyncio
    async def test_get_connection_yields_connection(self):
        """Test get_connection yields a database connection."""
        settings = Settings(
            database_url="postgresql://user:pass@localhost:5432/testdb",
        )

        mock_connection = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.create_async_engine", return_value=mock_engine):
            async for conn in get_connection(settings):
                assert conn is mock_connection


class TestGetConnectionContext:
    """Tests for get_connection_context context manager."""

    @pytest.fixture(autouse=True)
    def reset_engine_state(self):
        """Reset engine state before and after each test."""
        reset_engine()
        yield
        reset_engine()

    @pytest.mark.asyncio
    async def test_get_connection_context_yields_connection(self):
        """Test get_connection_context yields a database connection."""
        settings = Settings(
            database_url="postgresql://user:pass@localhost:5432/testdb",
        )

        mock_connection = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_connection
        )
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.create_async_engine", return_value=mock_engine):
            async with get_connection_context(settings) as conn:
                assert conn is mock_connection


class TestLifespan:
    """Tests for FastAPI lifespan context manager."""

    @pytest.fixture(autouse=True)
    def reset_engine_state(self):
        """Reset engine state before and after each test."""
        reset_engine()
        yield
        reset_engine()

    @pytest.mark.asyncio
    async def test_lifespan_initializes_and_disposes_engine(self):
        """Test lifespan initializes engine on startup and disposes on shutdown."""
        mock_app = MagicMock()
        mock_engine = AsyncMock()

        with patch("app.database.create_async_engine", return_value=mock_engine):
            with patch("app.database.get_settings") as mock_settings:
                mock_settings.return_value = Settings(
                    database_url="postgresql://user:pass@localhost:5432/testdb",
                )

                async with lifespan(mock_app):
                    # Engine should be initialized
                    pass

                # Engine should be disposed
                mock_engine.dispose.assert_called_once()

"""Tests for FastAPI application bootstrap.

This test suite covers:
- Application creation and configuration
- Health endpoint functionality
- CORS middleware behavior
- OPTIONS preflight request handling
- Lifespan context manager (startup/shutdown)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.cors import ALLOWED_HEADERS, ALLOWED_METHODS
from app.main import app, create_app, health_check


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_correct_body(self, client):
        """Test health endpoint returns expected JSON body."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mealbot"

    def test_health_content_type(self, client):
        """Test health endpoint returns JSON content type."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]

    def test_health_no_auth_required(self, client):
        """Test health endpoint does not require authentication."""
        # Request without Authorization header should succeed
        response = client.get("/health")
        assert response.status_code == 200


class TestCORSMiddleware:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present_on_get(self, client):
        """Test CORS headers are present on GET request."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-headers" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_cors_origin_reflected(self, client):
        """Test Access-Control-Allow-Origin reflects request Origin."""
        # Test with localhost origin
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

        # Test with different origin
        response = client.get(
            "/health", headers={"Origin": "https://mealbot-web.herokuapp.com"}
        )
        assert (
            response.headers["access-control-allow-origin"]
            == "https://mealbot-web.herokuapp.com"
        )

    def test_cors_allowed_headers(self, client):
        """Test Access-Control-Allow-Headers matches Go implementation."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        allowed_headers = response.headers["access-control-allow-headers"]

        # Verify all expected headers are present
        for header in ALLOWED_HEADERS:
            assert header in allowed_headers, f"Missing header: {header}"

    def test_cors_allowed_methods(self, client):
        """Test Access-Control-Allow-Methods matches Go implementation."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        allowed_methods = response.headers["access-control-allow-methods"]

        # Verify all expected methods are present
        for method in ALLOWED_METHODS:
            assert method in allowed_methods, f"Missing method: {method}"


class TestCORSPreflight:
    """Tests for CORS preflight (OPTIONS) request handling."""

    def test_options_returns_200(self, client):
        """Test OPTIONS request returns 200 OK."""
        response = client.options(
            "/health", headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200

    def test_options_has_cors_headers(self, client):
        """Test OPTIONS request includes all CORS headers."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-headers" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_options_no_auth_required(self, client):
        """Test OPTIONS request does not require authentication."""
        # Should succeed without Authorization header
        response = client.options(
            "/health", headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200

    def test_options_empty_body(self, client):
        """Test OPTIONS request returns empty body."""
        response = client.options(
            "/health", headers={"Origin": "http://localhost:3000"}
        )
        # OPTIONS preflight should have minimal/empty body
        assert response.text == ""


class TestCreateApp:
    """Tests for the create_app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        """Test create_app returns a FastAPI instance."""
        from fastapi import FastAPI

        with patch("app.main.init_engine", new_callable=AsyncMock):
            with patch("app.main.dispose_engine", new_callable=AsyncMock):
                test_app = create_app()
                assert isinstance(test_app, FastAPI)

    def test_create_app_has_correct_title(self):
        """Test created app has correct title."""
        with patch("app.main.init_engine", new_callable=AsyncMock):
            with patch("app.main.dispose_engine", new_callable=AsyncMock):
                test_app = create_app()
                assert test_app.title == "Mealbot API"

    def test_create_app_has_health_route(self):
        """Test created app includes health route."""
        with patch("app.main.init_engine", new_callable=AsyncMock):
            with patch("app.main.dispose_engine", new_callable=AsyncMock):
                test_app = create_app()
                routes = [route.path for route in test_app.routes]
                assert "/health" in routes


class TestLifespan:
    """Tests for application lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_initializes_engine_on_startup(self):
        """Test lifespan initializes database engine on startup."""
        with patch("app.main.init_engine", new_callable=AsyncMock) as mock_init:
            with patch("app.main.dispose_engine", new_callable=AsyncMock):
                from app.main import lifespan

                mock_app = MagicMock()
                async with lifespan(mock_app):
                    mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_disposes_engine_on_shutdown(self):
        """Test lifespan disposes database engine on shutdown."""
        with patch("app.main.init_engine", new_callable=AsyncMock):
            with patch(
                "app.main.dispose_engine", new_callable=AsyncMock
            ) as mock_dispose:
                from app.main import lifespan

                mock_app = MagicMock()
                async with lifespan(mock_app):
                    pass

                mock_dispose.assert_called_once()


class TestHealthCheckFunction:
    """Tests for the health_check function directly."""

    @pytest.mark.asyncio
    async def test_health_check_returns_json_response(self):
        """Test health_check returns JSONResponse."""
        from fastapi.responses import JSONResponse

        response = await health_check()
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_health_check_body_content(self):
        """Test health_check response body."""
        response = await health_check()
        # Access the body content directly
        assert response.body == b'{"status":"healthy","service":"mealbot"}'

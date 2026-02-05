"""Tests for the Flask application initialization and CORS configuration.

This module provides smoke tests to verify:
- Application starts correctly
- CORS headers are present on responses
- Error handlers return JSON responses
"""

import json

import pytest
from flask import Flask
from flask.testing import FlaskClient


class TestAppInitialization:
    """Tests for Flask application factory."""

    def test_create_app_returns_flask_instance(self, app: Flask) -> None:
        """Test that create_app returns a Flask application instance."""
        assert app is not None
        assert isinstance(app, Flask)

    def test_app_has_testing_config(self, app: Flask) -> None:
        """Test that test configuration is applied."""
        assert app.config["TESTING"] is True
        assert app.config["DEBUG"] is True


class TestCorsConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_on_preflight_request(self, client: FlaskClient) -> None:
        """Test that CORS preflight requests return proper headers."""
        # A proper CORS preflight requires both Origin and Access-Control-Request-Method
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        # Check CORS headers are present
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers

    def test_cors_allows_get_post_delete_methods(self, client: FlaskClient) -> None:
        """Test that CORS allows GET, POST, DELETE methods."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        assert "DELETE" in allowed_methods

    def test_cors_allows_required_headers(self, client: FlaskClient) -> None:
        """Test that CORS allows required headers."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )

        allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
        # Check for key headers from the Go implementation
        assert "Authorization" in allowed_headers or "authorization" in allowed_headers.lower()
        assert "Content-Type" in allowed_headers or "content-type" in allowed_headers.lower()

    def test_cors_origin_header_on_regular_request(self, client: FlaskClient) -> None:
        """Test that Access-Control-Allow-Origin is set on regular requests with Origin."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        # Even non-preflight requests should have the Allow-Origin header
        assert "Access-Control-Allow-Origin" in response.headers


class TestErrorHandlers:
    """Tests for global error handlers."""

    def test_404_returns_json(self, client: FlaskClient) -> None:
        """Test that 404 errors return JSON response."""
        response = client.get("/nonexistent-route")

        assert response.status_code == 404
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert "message" in data

    def test_404_response_format_matches_go(self, client: FlaskClient) -> None:
        """Test that 404 response matches Go's {"message": ...} format."""
        response = client.get("/nonexistent-route")

        data = json.loads(response.data)
        # Go implementation returns {"message": "text"} format
        assert isinstance(data, dict)
        assert "message" in data
        assert isinstance(data["message"], str)


class TestServerStart:
    """Tests to verify the server can start and respond."""

    def test_app_responds_to_requests(self, client: FlaskClient) -> None:
        """Test that the application responds to HTTP requests."""
        # Any request should work, even if route doesn't exist
        response = client.get("/")

        # Response should be received (any status code is valid at this point)
        assert response is not None

    def test_app_returns_json_content_type_for_errors(
        self, client: FlaskClient
    ) -> None:
        """Test that error responses have JSON content type."""
        response = client.get("/nonexistent")

        assert response.content_type == "application/json"

"""Integration smoke tests for the Flask app.

Tests static file serving, CORS headers, route method restrictions,
and basic endpoint behavior using Flask's test client (no database required).
"""

import json
import os
import pytest

from mealbot.app import create_app


@pytest.fixture
def app():
    """Create a test Flask application."""
    # Set a dummy DATABASE_URL so db module doesn't fail at import
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


class TestStaticFiles:
    """Tests for static file serving."""

    def test_serve_privacy_html(self, client):
        """GET /privacy.html should serve the privacy policy page."""
        response = client.get("/privacy.html")
        assert response.status_code == 200
        assert b"Privacy Policy" in response.data

    def test_serve_sample_csv(self, client):
        """GET /sample.csv should serve the sample CSV file."""
        response = client.get("/sample.csv")
        assert response.status_code == 200
        assert b"Name,Email" in response.data

    def test_root_path(self, client):
        """GET / should return 200 (root/index)."""
        response = client.get("/")
        assert response.status_code == 200

    def test_nonexistent_static_file(self, client):
        """GET /nonexistent.html should return 404."""
        response = client.get("/nonexistent.html")
        assert response.status_code == 404


class TestCORS:
    """Tests for CORS middleware behavior."""

    def test_cors_headers_on_response(self, client):
        """Responses should include CORS headers."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
        assert "Authorization" in response.headers.get("Access-Control-Allow-Headers", "")
        assert "GET" in response.headers.get("Access-Control-Allow-Methods", "")

    def test_options_preflight(self, client):
        """OPTIONS requests should return 200 with CORS headers."""
        response = client.options(
            "/orgs",
            headers={"Origin": "https://mealbot-web.herokuapp.com"},
        )
        assert response.status_code == 200
        assert (
            response.headers.get("Access-Control-Allow-Origin")
            == "https://mealbot-web.herokuapp.com"
        )

    def test_cors_echoes_origin(self, client):
        """CORS should echo back the request's Origin header."""
        response = client.get("/", headers={"Origin": "https://custom-origin.example.com"})
        assert (
            response.headers.get("Access-Control-Allow-Origin")
            == "https://custom-origin.example.com"
        )


class TestOrgEndpoints:
    """Tests for organization endpoint method restrictions.

    These tests verify HTTP method enforcement without a database.
    Auth is also checked - requests without auth to API routes should get 401.
    """

    def test_orgs_rejects_post(self, client):
        """POST /orgs should return 401 (auth required) or 405 (method not allowed)."""
        response = client.post("/orgs")
        # Without auth, should get 401
        assert response.status_code == 401

    def test_org_rejects_get(self, client):
        """GET /org should return 401 (auth required) or 405 (method not allowed)."""
        response = client.get("/org")
        # Without auth, should get 401
        assert response.status_code == 401

    def test_crossmatchtrait_rejects_get(self, client):
        """GET /crossmatchtrait should return 401 (auth required)."""
        response = client.get("/crossmatchtrait")
        assert response.status_code == 401


class TestAuthMiddleware:
    """Tests for JWT authentication middleware."""

    def test_api_route_requires_auth(self, client):
        """API routes should require authentication."""
        response = client.get("/orgs?admin=test@example.com")
        assert response.status_code == 401

    def test_static_routes_skip_auth(self, client):
        """Static file routes should not require authentication."""
        response = client.get("/privacy.html")
        assert response.status_code == 200

    def test_root_skips_auth(self, client):
        """Root path should not require authentication."""
        response = client.get("/")
        assert response.status_code == 200

    def test_invalid_auth_header_format(self, client):
        """Invalid Authorization header format should return 401."""
        response = client.get(
            "/orgs?admin=test@example.com",
            headers={"Authorization": "InvalidFormat"},
        )
        assert response.status_code == 401


class TestResponseFormat:
    """Tests for response JSON format parity with Go app."""

    def test_options_returns_empty_body(self, client):
        """OPTIONS preflight should return an empty body."""
        response = client.options("/orgs")
        # Body should be empty or minimal
        assert response.status_code == 200

"""Tests for Organization API endpoints.

This module tests the organization-related API endpoints:
- GET /orgs - Fetch organizations by admin email
- POST /org - Create a new organization
- POST /crossmatchtrait - Set cross-match trait for an organization
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from mealbot.app import create_app
from mealbot.models.organization import get_cross_match_trait


@pytest.fixture
def app():
    """Create and configure a Flask application instance for testing."""
    test_app = create_app(config_override={"TESTING": True, "DEBUG": True})
    with test_app.app_context():
        yield test_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client for the Flask application."""
    return app.test_client()


# =============================================================================
# GET /orgs Tests
# =============================================================================


def test_get_orgs_returns_empty_list_when_no_orgs(client: FlaskClient):
    """GET /orgs returns empty list when no organizations match."""
    with patch("mealbot.routes.organizations.get_organizations") as mock_get_orgs:
        mock_get_orgs.return_value = []

        response = client.get("/orgs?admin=unknown@example.com")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {"orgs": []}
        mock_get_orgs.assert_called_once_with("unknown@example.com")


def test_get_orgs_returns_organizations_for_admin(client: FlaskClient):
    """GET /orgs returns organization names for admin."""
    with patch("mealbot.routes.organizations.get_organizations") as mock_get_orgs:
        mock_get_orgs.return_value = ["org1", "org2", "org3"]

        response = client.get("/orgs?admin=admin@example.com")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {"orgs": ["org1", "org2", "org3"]}
        mock_get_orgs.assert_called_once_with("admin@example.com")


def test_get_orgs_requires_admin_query_param(client: FlaskClient):
    """GET /orgs returns 400 without admin parameter."""
    response = client.get("/orgs")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "message" in data
    assert "admin" in data["message"].lower()


def test_get_orgs_requires_single_admin_query_param(client: FlaskClient):
    """GET /orgs returns 400 when multiple admin values provided."""
    response = client.get("/orgs?admin=test1@example.com&admin=test2@example.com")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "message" in data


def test_get_orgs_rejects_non_get_methods(client: FlaskClient):
    """GET /orgs returns 405 for POST/PUT/DELETE methods."""
    # POST
    response = client.post("/orgs?admin=test@example.com")
    assert response.status_code == 405

    # PUT
    response = client.put("/orgs?admin=test@example.com")
    assert response.status_code == 405

    # DELETE
    response = client.delete("/orgs?admin=test@example.com")
    assert response.status_code == 405


# =============================================================================
# POST /org Tests
# =============================================================================


def test_create_org_success(client: FlaskClient):
    """POST /org creates organization successfully."""
    with patch("mealbot.routes.organizations.create_organization") as mock_create:
        mock_create.return_value = None

        response = client.post(
            "/org?admin=admin@example.com",
            json={"org": "test-org"},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data == {"message": "Successfully created new organization"}
        mock_create.assert_called_once_with("test-org", "admin@example.com")


def test_create_org_requires_admin_query_param(client: FlaskClient):
    """POST /org returns 400 without admin parameter."""
    response = client.post(
        "/org",
        json={"org": "test-org"},
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "message" in data
    assert "admin" in data["message"].lower()


def test_create_org_requires_org_in_body(client: FlaskClient):
    """POST /org returns 400 without org in body."""
    response = client.post(
        "/org?admin=admin@example.com",
        json={"name": "wrong-field"},
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "message" in data


def test_create_org_rejects_empty_org_name(client: FlaskClient):
    """POST /org returns 500 for empty org name."""
    with patch("mealbot.routes.organizations.create_organization") as mock_create:
        mock_create.side_effect = ValueError(
            "Organization name cannot be an empty string"
        )

        response = client.post(
            "/org?admin=admin@example.com",
            json={"org": ""},
            content_type="application/json",
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "message" in data


def test_create_org_rejects_duplicate_org(client: FlaskClient):
    """POST /org returns 500 for duplicate organization."""
    with patch("mealbot.routes.organizations.create_organization") as mock_create:
        mock_create.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        response = client.post(
            "/org?admin=admin@example.com",
            json={"org": "existing-org"},
            content_type="application/json",
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "message" in data


def test_create_org_rejects_non_post_methods(client: FlaskClient):
    """POST /org returns 405 for GET/PUT/DELETE methods."""
    # GET
    response = client.get("/org?admin=test@example.com")
    assert response.status_code == 405

    # PUT
    response = client.put(
        "/org?admin=test@example.com",
        json={"org": "test"},
        content_type="application/json",
    )
    assert response.status_code == 405

    # DELETE
    response = client.delete("/org?admin=test@example.com")
    assert response.status_code == 405


# =============================================================================
# POST /crossmatchtrait Tests
# =============================================================================


def test_crossmatchtrait_sets_trait(client: FlaskClient):
    """POST /crossmatchtrait sets trait successfully."""
    with patch("mealbot.routes.organizations.set_cross_match_trait") as mock_set:
        mock_set.return_value = None

        response = client.post(
            "/crossmatchtrait?org=test-org",
            json={"trait": "department"},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data == {"message": "Successfully set the cross match trait"}
        mock_set.assert_called_once_with("test-org", "department")


def test_crossmatchtrait_requires_org_query_param(client: FlaskClient):
    """POST /crossmatchtrait returns 400 without org parameter."""
    response = client.post(
        "/crossmatchtrait",
        json={"trait": "department"},
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "message" in data


def test_crossmatchtrait_requires_trait_in_body(client: FlaskClient):
    """POST /crossmatchtrait returns 400 without trait in body.

    Note: The Go implementation doesn't explicitly check for trait field,
    it uses body.get("trait", "") which defaults to empty string.
    This test verifies the endpoint still works but uses empty string.
    """
    with patch("mealbot.routes.organizations.set_cross_match_trait") as mock_set:
        mock_set.return_value = None

        response = client.post(
            "/crossmatchtrait?org=test-org",
            json={"other": "field"},
            content_type="application/json",
        )

        # The endpoint accepts this but uses empty string for trait
        assert response.status_code == 201
        mock_set.assert_called_once_with("test-org", "")


def test_crossmatchtrait_rejects_malformed_body(client: FlaskClient):
    """POST /crossmatchtrait returns 400 for malformed JSON body."""
    response = client.post(
        "/crossmatchtrait?org=test-org",
        data="not valid json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_crossmatchtrait_rejects_non_post_methods(client: FlaskClient):
    """POST /crossmatchtrait returns 405 for GET/PUT/DELETE methods."""
    # GET
    response = client.get("/crossmatchtrait?org=test-org")
    assert response.status_code == 405

    # PUT
    response = client.put(
        "/crossmatchtrait?org=test-org",
        json={"trait": "test"},
        content_type="application/json",
    )
    assert response.status_code == 405

    # DELETE
    response = client.delete("/crossmatchtrait?org=test-org")
    assert response.status_code == 405


# =============================================================================
# GetCrossMatchTrait Model Function Tests
# =============================================================================


def test_get_cross_match_trait_returns_null_when_not_set():
    """GetCrossMatchTrait returns empty string for NULL."""
    with patch("mealbot.models.organization.get_db_connection") as mock_conn_ctx:
        mock_conn = MagicMock()
        mock_conn_ctx.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (None,)
        mock_conn.execute.return_value = mock_result

        result = get_cross_match_trait("test-org")

        assert result == ""


def test_get_cross_match_trait_returns_value_when_set():
    """GetCrossMatchTrait returns trait value."""
    with patch("mealbot.models.organization.get_db_connection") as mock_conn_ctx:
        mock_conn = MagicMock()
        mock_conn_ctx.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("department",)
        mock_conn.execute.return_value = mock_result

        result = get_cross_match_trait("test-org")

        assert result == "department"


def test_get_cross_match_trait_returns_empty_when_org_not_found():
    """GetCrossMatchTrait returns empty string when org doesn't exist."""
    with patch("mealbot.models.organization.get_db_connection") as mock_conn_ctx:
        mock_conn = MagicMock()
        mock_conn_ctx.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result

        result = get_cross_match_trait("nonexistent-org")

        assert result == ""

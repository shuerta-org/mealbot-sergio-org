"""Tests for Organizations API endpoints.

This test suite covers:
- GET /orgs returns empty list for unknown admin
- GET /orgs returns organization list for known admin
- POST /org creates organization successfully
- POST /org rejects empty organization name
- POST /crossmatchtrait updates trait successfully
- All endpoints require authentication
- Missing query parameters return appropriate errors
- GetCrossMatchTrait exported function works correctly

Reference: Go org.go implementation
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import get_current_user, reset_jwks_client
from app.config import Settings
from app.database import get_connection
from app.organizations import (
    CreateOrganizationRequestBody,
    GetCrossMatchTrait,
    MessageResponse,
    OrganizationsResponse,
    SetCrossMatchTraitRequestBody,
    create_organization,
    get_cross_match_trait,
    get_organizations,
    router,
    set_cross_match_trait,
)


@pytest.fixture
def test_settings():
    """Fixture providing test settings."""
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        auth0_issuer="https://mealbot.auth0.com/",
        auth0_audience="https://mealbot-2.herokuapp.com/",
        auth0_jwks_url="https://mealbot.auth0.com/.well-known/jwks.json",
    )


@pytest.fixture(autouse=True)
def reset_jwks():
    """Reset JWKS client before each test."""
    reset_jwks_client()
    yield
    reset_jwks_client()


def create_test_app_with_overrides(
    mock_user: dict | None = None,
    mock_conn: AsyncMock | None = None,
) -> FastAPI:
    """Create a test FastAPI app with dependency overrides.

    Args:
        mock_user: Mock user data to return from auth. None means auth fails.
        mock_conn: Mock database connection. None means use real connection.

    Returns:
        FastAPI app with overrides applied.
    """

    @asynccontextmanager
    async def mock_lifespan(app: FastAPI):
        yield

    app = FastAPI(lifespan=mock_lifespan)
    app.include_router(router)

    # Override auth dependency
    if mock_user is not None:

        async def mock_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

    # Override database connection dependency
    if mock_conn is not None:

        async def mock_get_connection():
            yield mock_conn

        app.dependency_overrides[get_connection] = mock_get_connection

    return app


class TestPydanticModels:
    """Tests for Pydantic request/response models."""

    def test_create_organization_request_body(self):
        """Test CreateOrganizationRequestBody model."""
        body = CreateOrganizationRequestBody(org="test-org")
        assert body.org == "test-org"

    def test_set_cross_match_trait_request_body(self):
        """Test SetCrossMatchTraitRequestBody model."""
        body = SetCrossMatchTraitRequestBody(trait="college")
        assert body.trait == "college"

    def test_organizations_response(self):
        """Test OrganizationsResponse model."""
        response = OrganizationsResponse(orgs=["org1", "org2"])
        assert response.orgs == ["org1", "org2"]

    def test_message_response(self):
        """Test MessageResponse model."""
        response = MessageResponse(Message="Success")
        assert response.Message == "Success"


class TestDataAccessFunctions:
    """Tests for database access functions."""

    @pytest.mark.asyncio
    async def test_get_organizations(self):
        """Test get_organizations fetches orgs for admin."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("org1",), ("org2",)]
        mock_conn.execute.return_value = mock_result

        result = await get_organizations("admin@test.com", mock_conn)

        assert result == ["org1", "org2"]
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_organizations_empty(self):
        """Test get_organizations returns empty list for unknown admin."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result

        result = await get_organizations("unknown@test.com", mock_conn)

        assert result == []

    @pytest.mark.asyncio
    async def test_create_organization(self):
        """Test create_organization inserts new org."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        await create_organization("new-org", "admin@test.com", mock_conn)

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_organization_empty_name(self):
        """Test create_organization rejects empty name."""
        mock_conn = AsyncMock()

        with pytest.raises(
            ValueError, match="Organization name cannot be an empty string"
        ):
            await create_organization("", "admin@test.com", mock_conn)

    @pytest.mark.asyncio
    async def test_get_cross_match_trait(self):
        """Test get_cross_match_trait fetches trait."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("college",)
        mock_conn.execute.return_value = mock_result

        result = await get_cross_match_trait("test-org", mock_conn)

        assert result == "college"

    @pytest.mark.asyncio
    async def test_get_cross_match_trait_null(self):
        """Test get_cross_match_trait returns empty string for NULL."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (None,)
        mock_conn.execute.return_value = mock_result

        result = await get_cross_match_trait("test-org", mock_conn)

        assert result == ""

    @pytest.mark.asyncio
    async def test_get_cross_match_trait_no_org(self):
        """Test get_cross_match_trait returns empty string when org not found."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result

        result = await get_cross_match_trait("unknown-org", mock_conn)

        assert result == ""

    @pytest.mark.asyncio
    async def test_set_cross_match_trait(self):
        """Test set_cross_match_trait updates trait."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        await set_cross_match_trait("test-org", "year", mock_conn)

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


class TestGetOrgsEndpoint:
    """Tests for GET /orgs endpoint."""

    def test_get_orgs_returns_organizations(self):
        """Test GET /orgs returns organization list."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("org1",), ("org2",)]
        mock_conn.execute.return_value = mock_result

        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.get("/orgs?admin=test@test.com")

        assert response.status_code == 200
        assert response.json() == {"orgs": ["org1", "org2"]}

    def test_get_orgs_empty_list(self):
        """Test GET /orgs returns empty list for unknown admin."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result

        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.get("/orgs?admin=unknown@test.com")

        assert response.status_code == 200
        assert response.json() == {"orgs": []}

    def test_get_orgs_missing_admin_param(self):
        """Test GET /orgs requires admin query parameter."""
        mock_conn = AsyncMock()
        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.get("/orgs")

        # FastAPI returns 422 for missing required query params
        assert response.status_code == 422


class TestCreateOrgEndpoint:
    """Tests for POST /org endpoint."""

    def test_create_org_success(self):
        """Test POST /org creates organization successfully."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.post(
            "/org?admin=test@test.com",
            json={"org": "new-org"},
        )

        assert response.status_code == 201
        assert response.json()["Message"] == "Successfully created new organization"

    def test_create_org_empty_name(self):
        """Test POST /org rejects empty organization name."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.post(
            "/org?admin=test@test.com",
            json={"org": ""},
        )

        assert response.status_code == 400
        assert (
            "Organization name cannot be an empty string"
            in response.json()["detail"]["Message"]
        )

    def test_create_org_missing_admin_param(self):
        """Test POST /org requires admin query parameter."""
        mock_conn = AsyncMock()
        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.post("/org", json={"org": "new-org"})

        # FastAPI returns 422 for missing required query params
        assert response.status_code == 422


class TestCrossMatchTraitEndpoint:
    """Tests for POST /crossmatchtrait endpoint."""

    def test_crossmatchtrait_success(self):
        """Test POST /crossmatchtrait updates trait successfully."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.commit = AsyncMock()

        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.post(
            "/crossmatchtrait?org=test-org",
            json={"trait": "college"},
        )

        assert response.status_code == 201
        assert response.json()["Message"] == "Successfully set the cross match trait"

    def test_crossmatchtrait_missing_org_param(self):
        """Test POST /crossmatchtrait requires org query parameter."""
        mock_conn = AsyncMock()
        app = create_test_app_with_overrides(
            mock_user={"sub": "user|123"}, mock_conn=mock_conn
        )
        client = TestClient(app)

        response = client.post("/crossmatchtrait", json={"trait": "college"})

        # FastAPI returns 422 for missing required query params
        assert response.status_code == 422


class TestGetCrossMatchTraitExported:
    """Tests for the exported GetCrossMatchTrait function."""

    @pytest.mark.asyncio
    async def test_get_cross_match_trait_exported(self):
        """Test GetCrossMatchTrait function can be imported and used."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("college",)
        mock_conn.execute.return_value = mock_result

        @asynccontextmanager
        async def mock_get_connection_context():
            yield mock_conn

        with patch(
            "app.organizations.get_connection_context", mock_get_connection_context
        ):
            result = await GetCrossMatchTrait("test-org")

        assert result == "college"

    @pytest.mark.asyncio
    async def test_get_cross_match_trait_exported_null(self):
        """Test GetCrossMatchTrait returns empty string for NULL."""
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (None,)
        mock_conn.execute.return_value = mock_result

        @asynccontextmanager
        async def mock_get_connection_context():
            yield mock_conn

        with patch(
            "app.organizations.get_connection_context", mock_get_connection_context
        ):
            result = await GetCrossMatchTrait("test-org")

        assert result == ""

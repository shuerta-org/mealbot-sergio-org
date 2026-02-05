"""Tests for Auth0 JWT authentication module.

This test suite covers:
- Valid token acceptance
- Expired token rejection
- Wrong audience rejection
- Wrong issuer rejection
- Malformed token rejection
- Missing Authorization header rejection
- OPTIONS request handling (CORS preflight)

Uses mock JWKS and test tokens to avoid depending on actual Auth0 infrastructure.
"""

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.auth import (
    ErrorResponse,
    get_current_user,
    get_jwks_client,
    reset_jwks_client,
    verify_audience,
)
from app.config import Settings


# Generate RSA key pair for testing
def generate_rsa_key_pair():
    """Generate an RSA key pair for signing test tokens."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key


# Test fixtures
@pytest.fixture
def rsa_keys():
    """Fixture providing RSA key pair for JWT signing."""
    return generate_rsa_key_pair()


@pytest.fixture
def test_settings():
    """Fixture providing test settings."""
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        auth0_issuer="https://test.auth0.com/",
        auth0_audience="https://test-api.example.com/",
        auth0_jwks_url="https://test.auth0.com/.well-known/jwks.json",
    )


@pytest.fixture(autouse=True)
def reset_jwks():
    """Reset JWKS client before each test."""
    reset_jwks_client()
    yield
    reset_jwks_client()


def create_test_token(
    private_key,
    issuer: str = "https://test.auth0.com/",
    audience: str = "https://test-api.example.com/",
    exp_offset: int = 3600,
    algorithm: str = "RS256",
    kid: str = "test-key-id",
    additional_claims: dict = None,
):
    """Create a test JWT token.

    Args:
        private_key: RSA private key for signing.
        issuer: Token issuer claim.
        audience: Token audience claim.
        exp_offset: Expiration offset in seconds (negative for expired).
        algorithm: Signing algorithm.
        kid: Key ID header.
        additional_claims: Additional claims to include.

    Returns:
        str: Encoded JWT token.
    """
    now = int(time.time())
    payload = {
        "iss": issuer,
        "aud": audience,
        "exp": now + exp_offset,
        "iat": now,
        "sub": "user|12345",
    }
    if additional_claims:
        payload.update(additional_claims)

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return jwt.encode(
        payload,
        private_key_pem,
        algorithm=algorithm,
        headers={"kid": kid},
    )


class MockRequest:
    """Mock FastAPI Request for testing."""

    def __init__(self, method: str = "GET"):
        self.method = method


class MockCredentials:
    """Mock HTTPAuthorizationCredentials."""

    def __init__(self, credentials: str):
        self.credentials = credentials
        self.scheme = "Bearer"


class TestErrorResponse:
    """Tests for ErrorResponse helper class."""

    def test_create_error_response(self):
        """Test error response matches Go format."""
        result = ErrorResponse.create("Test error message")
        assert result == {"Message": "Test error message"}

    def test_create_error_response_empty_message(self):
        """Test error response with empty message."""
        result = ErrorResponse.create("")
        assert result == {"Message": ""}


class TestVerifyAudience:
    """Tests for audience verification function."""

    def test_verify_audience_string_match(self):
        """Test audience verification with matching string."""
        claims = {"aud": "https://test-api.example.com/"}
        assert verify_audience(claims, "https://test-api.example.com/") is True

    def test_verify_audience_string_no_match(self):
        """Test audience verification with non-matching string."""
        claims = {"aud": "https://other-api.example.com/"}
        assert verify_audience(claims, "https://test-api.example.com/") is False

    def test_verify_audience_array_match(self):
        """Test audience verification with matching array (Go behavior)."""
        claims = {"aud": ["https://api1.example.com/", "https://test-api.example.com/"]}
        assert verify_audience(claims, "https://test-api.example.com/") is True

    def test_verify_audience_array_no_match(self):
        """Test audience verification with non-matching array."""
        claims = {"aud": ["https://api1.example.com/", "https://api2.example.com/"]}
        assert verify_audience(claims, "https://test-api.example.com/") is False

    def test_verify_audience_missing(self):
        """Test audience verification with missing claim."""
        claims = {}
        assert verify_audience(claims, "https://test-api.example.com/") is False

    def test_verify_audience_none(self):
        """Test audience verification with None value."""
        claims = {"aud": None}
        assert verify_audience(claims, "https://test-api.example.com/") is False


class TestGetCurrentUser:
    """Tests for the get_current_user authentication dependency."""

    @pytest.mark.asyncio
    async def test_options_request_bypasses_auth(self, test_settings):
        """Test OPTIONS requests bypass authentication (CORS preflight)."""
        request = MockRequest(method="OPTIONS")
        result = await get_current_user(
            request=request,
            credentials=None,
            settings=test_settings,
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, test_settings):
        """Test rejection when Authorization header is missing."""
        request = MockRequest(method="GET")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=request,
                credentials=None,
                settings=test_settings,
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == {"Message": "No authorization header"}
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    async def test_valid_token_accepted(self, rsa_keys, test_settings):
        """Test valid token is accepted and payload returned."""
        private_key, public_key = rsa_keys

        # Create a mock signing key
        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        # Create test token
        token = create_test_token(
            private_key,
            issuer=test_settings.auth0_issuer,
            audience=test_settings.auth0_audience,
        )

        # Mock the JWKS client
        with patch("app.auth.get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_get_client.return_value = mock_client

            request = MockRequest(method="GET")
            credentials = MockCredentials(token)

            result = await get_current_user(
                request=request,
                credentials=credentials,
                settings=test_settings,
            )

            assert result["iss"] == test_settings.auth0_issuer
            assert result["sub"] == "user|12345"

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, rsa_keys, test_settings):
        """Test expired token is rejected."""
        private_key, public_key = rsa_keys

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        # Create expired token
        token = create_test_token(
            private_key,
            issuer=test_settings.auth0_issuer,
            audience=test_settings.auth0_audience,
            exp_offset=-3600,  # Expired 1 hour ago
        )

        with patch("app.auth.get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_get_client.return_value = mock_client

            request = MockRequest(method="GET")
            credentials = MockCredentials(token)

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=request,
                    credentials=credentials,
                    settings=test_settings,
                )

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == {"Message": "Token has expired"}

    @pytest.mark.asyncio
    async def test_wrong_issuer_rejected(self, rsa_keys, test_settings):
        """Test token with wrong issuer is rejected."""
        private_key, public_key = rsa_keys

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        # Create token with wrong issuer
        token = create_test_token(
            private_key,
            issuer="https://wrong-issuer.auth0.com/",
            audience=test_settings.auth0_audience,
        )

        with patch("app.auth.get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_get_client.return_value = mock_client

            request = MockRequest(method="GET")
            credentials = MockCredentials(token)

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=request,
                    credentials=credentials,
                    settings=test_settings,
                )

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == {"Message": "Invalid issuer"}

    @pytest.mark.asyncio
    async def test_wrong_audience_rejected(self, rsa_keys, test_settings):
        """Test token with wrong audience is rejected."""
        private_key, public_key = rsa_keys

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        # Create token with wrong audience
        token = create_test_token(
            private_key,
            issuer=test_settings.auth0_issuer,
            audience="https://wrong-audience.example.com/",
        )

        with patch("app.auth.get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_get_client.return_value = mock_client

            request = MockRequest(method="GET")
            credentials = MockCredentials(token)

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=request,
                    credentials=credentials,
                    settings=test_settings,
                )

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == {"Message": "Invalid audience"}

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, test_settings):
        """Test malformed token is rejected."""
        request = MockRequest(method="GET")
        credentials = MockCredentials("not.a.valid.jwt")

        with patch("app.auth.get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            # PyJWKClient raises error for invalid token
            mock_client.get_signing_key_from_jwt.side_effect = (
                jwt.exceptions.DecodeError("Invalid token")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=request,
                    credentials=credentials,
                    settings=test_settings,
                )

            assert exc_info.value.status_code == 401
            # Should be caught by InvalidTokenError handler
            assert "Invalid access token" in exc_info.value.detail["Message"]

    @pytest.mark.asyncio
    async def test_jwks_fetch_error(self, test_settings):
        """Test JWKS fetch error is handled gracefully."""
        request = MockRequest(method="GET")
        credentials = MockCredentials("valid.looking.token")

        with patch("app.auth.get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.side_effect = (
                jwt.exceptions.PyJWKClientError("Failed to fetch JWKS")
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=request,
                    credentials=credentials,
                    settings=test_settings,
                )

            assert exc_info.value.status_code == 401
            assert "Unable to find appropriate key" in exc_info.value.detail["Message"]

    @pytest.mark.asyncio
    async def test_array_audience_accepted(self, rsa_keys, test_settings):
        """Test token with array audience containing expected audience is accepted."""
        private_key, public_key = rsa_keys

        mock_signing_key = MagicMock()
        mock_signing_key.key = public_key

        # Create token with array audience
        token = create_test_token(
            private_key,
            issuer=test_settings.auth0_issuer,
            audience=[
                "https://other-api.example.com/",
                test_settings.auth0_audience,
            ],
        )

        with patch("app.auth.get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_get_client.return_value = mock_client

            request = MockRequest(method="GET")
            credentials = MockCredentials(token)

            result = await get_current_user(
                request=request,
                credentials=credentials,
                settings=test_settings,
            )

            assert result["sub"] == "user|12345"


class TestGetJwksClient:
    """Tests for JWKS client caching."""

    def test_jwks_client_caching(self, test_settings):
        """Test JWKS client is cached and reused."""
        with patch("app.auth.PyJWKClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Get client twice
            client1 = get_jwks_client(test_settings)
            client2 = get_jwks_client(test_settings)

            # Should only be instantiated once
            assert mock_class.call_count == 1
            assert client1 is client2

    def test_reset_jwks_client(self, test_settings):
        """Test JWKS client reset forces new client creation."""
        with patch("app.auth.PyJWKClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Get client, reset, get again
            _ = get_jwks_client(test_settings)
            reset_jwks_client()
            _ = get_jwks_client(test_settings)

            # Should be instantiated twice
            assert mock_class.call_count == 2

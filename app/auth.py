"""Auth0 JWT authentication middleware for FastAPI.

This module provides JWT validation for Auth0-issued tokens using RS256 signatures.
It implements the same authentication logic as the Go auth.go but with improved
JWKS caching using PyJWKClient for better performance.

Reference: Go implementation auth.go lines 13-185
"""

from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import Settings, get_settings

# Global JWKS client with built-in caching
# PyJWKClient handles automatic refresh and caching of JWKS keys
_jwks_client: PyJWKClient | None = None


class ErrorResponse:
    """Error response format matching Go implementation's {"Message": "..."}."""

    @staticmethod
    def create(message: str) -> dict[str, str]:
        """Create error response dict matching Go format."""
        return {"Message": message}


def get_jwks_client(settings: Settings) -> PyJWKClient:
    """Get or create the cached JWKS client.

    Uses a global client instance to ensure JWKS keys are cached and
    reused across requests. PyJWKClient handles automatic refresh
    when keys expire or rotate.

    Args:
        settings: Application settings with auth0_jwks_url.

    Returns:
        PyJWKClient: The cached JWKS client.
    """
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            settings.auth0_jwks_url,
            cache_keys=True,
            lifespan=3600,  # Cache keys for 1 hour
        )
    return _jwks_client


def reset_jwks_client() -> None:
    """Reset the JWKS client (useful for testing)."""
    global _jwks_client
    _jwks_client = None


# HTTPBearer with auto_error=False to allow custom error handling
# and OPTIONS request handling
security = HTTPBearer(auto_error=False)


def verify_audience(claims: dict[str, Any], audience: str) -> bool:
    """Verify the audience claim matches the expected value.

    Handles both single string audience and array audience formats
    as described in Go implementation verifyAudience (auth.go lines 169-185).

    Args:
        claims: JWT claims dictionary.
        audience: Expected audience value.

    Returns:
        bool: True if audience is valid, False otherwise.
    """
    aud = claims.get("aud")
    if aud is None:
        return False

    # Handle array audience (as in Go implementation)
    if isinstance(aud, list):
        return audience in aud

    # Handle single string audience
    if isinstance(aud, str):
        return aud == audience

    return False


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """FastAPI dependency for JWT authentication.

    Validates Auth0-issued JWT tokens with RS256 signatures.
    Mirrors Go implementation CheckJWT logic (auth.go lines 43-77).

    Args:
        request: The incoming request (used for OPTIONS check).
        credentials: Bearer token credentials from Authorization header.
        settings: Application settings with Auth0 configuration.

    Returns:
        dict: Decoded JWT payload/claims on successful validation.

    Raises:
        HTTPException: 401 Unauthorized for invalid/missing tokens.
    """
    # Skip authentication for OPTIONS requests (CORS preflight)
    # See Go auth.go lines 47-50
    if request.method == "OPTIONS":
        return {}

    # Check for missing Authorization header
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create("No authorization header"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Get the signing key from JWKS (with caching)
        jwks_client = get_jwks_client(settings)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate the token
        # Validates: signature (RS256), expiration, issuer, audience
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.auth0_issuer,
            audience=settings.auth0_audience,
        )

        # Additional audience verification for array format
        # (jwt.decode handles string audience, but Go implementation
        # supports array format - see auth.go lines 169-185)
        if not verify_audience(payload, settings.auth0_audience):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create("Invalid audience"),
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except jwt.exceptions.PyJWKClientError as e:
        # JWKS fetch or key lookup error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(f"Unable to find appropriate key: {str(e)}"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create("Token has expired"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create("Invalid issuer"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create("Invalid audience"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAlgorithmError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create("Token must use RS256 signing method"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        # Catch-all for other JWT validation errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(f"Invalid access token: {str(e)}"),
            headers={"WWW-Authenticate": "Bearer"},
        )

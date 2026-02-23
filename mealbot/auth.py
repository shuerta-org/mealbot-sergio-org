"""JWT authentication middleware.

Ports the Go app's auth.go behavior: validates JWT tokens from Auth0
using RS256 signing, verifies audience and issuer claims, and fetches
JWKS for public key retrieval.
"""

import json
import logging

import jwt
import requests
from flask import request

logger = logging.getLogger("mealbot.auth")

# Auth0 constants matching Go's auth.go
ISSUER = "https://mealbot.auth0.com/"
AUDIENCE = "https://mealbot-2.herokuapp.com/"
JSON_WEB_KEY_SET = "https://mealbot.auth0.com/.well-known/jwks.json"

# Error messages matching Go implementation
INVALID_ACCESS_TOKEN = "Invalid access token"


def _get_pem_certificate(token_header):
    """Fetch the PEM certificate for the token's key ID from JWKS.

    Equivalent to Go's getPEMCertificate function.

    Args:
        token_header: The decoded JWT header containing 'kid'.

    Returns:
        The PEM certificate string.

    Raises:
        Exception: If the key cannot be found or JWKS fetch fails.
    """
    resp = requests.get(JSON_WEB_KEY_SET)
    resp.raise_for_status()
    jwks = resp.json()

    kid = token_header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            cert = (
                "-----BEGIN CERTIFICATE-----\n"
                + key["x5c"][0]
                + "\n-----END CERTIFICATE-----"
            )
            return cert

    raise Exception("Unable to find appropriate key")


def _verify_audience(claims, audience):
    """Verify the audience claim in the token.

    Equivalent to Go's verifyAudience function. Handles both string
    and list audience claims.

    Args:
        claims: The decoded JWT claims dict.
        audience: The expected audience string.

    Returns:
        None on success.

    Raises:
        Exception: If audience claim is missing or invalid.
    """
    aud = claims.get("aud")
    if aud is None:
        raise Exception("No audience claim")

    # Handle both string and list audience claims
    if isinstance(aud, str):
        if aud == audience:
            return None
    elif isinstance(aud, list):
        for item in aud:
            if item == audience:
                return None

    raise Exception("Invalid audience")


def check_jwt(req):
    """Validate the JWT from the Authorization header.

    Equivalent to Go's CustomJWTMiddleware.CheckJWT method.

    Args:
        req: The Flask request object.

    Returns:
        None on success.

    Raises:
        Exception: If token is missing, malformed, or invalid.
    """
    # Preflight requests skip auth
    if req.method == "OPTIONS":
        return None

    auth_header = req.headers.get("Authorization", "")
    if not auth_header:
        raise Exception("No authorization header")

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise Exception("Authorization header format must be Bearer {token}")

    token_str = parts[1]

    # Decode header without verification first to get kid
    try:
        unverified_header = jwt.get_unverified_header(token_str)
    except jwt.exceptions.DecodeError:
        raise Exception("Token is invalid")

    # Verify signing algorithm
    if unverified_header.get("alg") != "RS256":
        raise Exception("Token must use 'alg' signing method")

    # Get the PEM certificate
    cert = _get_pem_certificate(unverified_header)

    # Decode and verify the token
    try:
        decoded = jwt.decode(
            token_str,
            cert,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False},
        )
    except jwt.exceptions.InvalidTokenError as e:
        raise Exception(str(e))

    # Verify audience
    _verify_audience(decoded, AUDIENCE)

    # Verify issuer
    iss = decoded.get("iss", "")
    if iss != ISSUER:
        raise Exception("Invalid issuer")

    return None


def init_app(app):
    """Register JWT authentication middleware with the Flask app.

    Applies auth checking to all requests except OPTIONS preflight.
    On auth failure, prints the error and returns an empty response,
    matching Go's behavior where the handler returns without writing a body.

    Args:
        app: Flask application instance.
    """

    @app.before_request
    def authenticate():
        """Check JWT authentication before each request.

        Skips authentication for:
        - OPTIONS preflight requests (handled by CORS)
        - Static file requests (the / path serves static files)
        """
        # Static file paths don't need auth (Go's FileServer was not behind auth middleware)
        # In Go, the "/" path is handled by http.FileServer, not wrapped by middleware
        # But in the Go code, only specific routes are wrapped with mw.Apply()
        # The static file server at "/" is NOT wrapped with middleware
        # So we skip auth for paths that would be served by the static file handler
        if request.path == "/" or request.path.startswith("/static"):
            return None

        # Skip auth for paths not matching known API routes
        api_routes = {"/members", "/orgs", "/org", "/crossmatchtrait",
                      "/rounds", "/round", "/pairs"}
        if request.path not in api_routes:
            return None

        try:
            check_jwt(request)
        except Exception as e:
            # Match Go's behavior: print error and return without response body
            print(str(e))
            return "", 401

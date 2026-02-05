"""CORS middleware configuration for FastAPI.

This module configures Cross-Origin Resource Sharing (CORS) to match the
behavior of the Go implementation in cors.go.

Reference: Go implementation cors.go lines 1-29
- AccessControlAllowHeaders: Authorization, Content-Type, Origin, Accept, token
- AccessControlAllowMethods: GET, POST, DELETE
- AccessControlAllowOrigin: Reflects the request Origin header (permissive)
"""

from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Allowed headers matching Go implementation cors.go line 9
ALLOWED_HEADERS = ["Authorization", "Content-Type", "Origin", "Accept", "token"]

# Allowed methods matching Go implementation cors.go line 21
ALLOWED_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware that mirrors Go implementation behavior.

    The Go implementation sets Access-Control-Allow-Origin to match the
    request's Origin header (permissive CORS). This middleware replicates
    that behavior exactly.

    For OPTIONS preflight requests, the middleware returns an empty response
    with CORS headers without proceeding to route handlers.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request and add CORS headers to response.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response with CORS headers added.
        """
        # Get origin from request headers (mirrors Go cors.go line 19)
        origin = request.headers.get("Origin", "")

        # Handle OPTIONS preflight requests (mirrors Go cors.go lines 23-25)
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            self._set_cors_headers(response, origin)
            return response

        # Process request through the chain
        response = await call_next(request)

        # Add CORS headers to response
        self._set_cors_headers(response, origin)

        return response

    def _set_cors_headers(self, response: Response, origin: str) -> None:
        """Set CORS headers on response.

        Args:
            response: The response object to modify.
            origin: The request origin to echo back.
        """
        # Mirror request origin (Go cors.go line 19)
        response.headers["Access-Control-Allow-Origin"] = origin

        # Allowed headers (Go cors.go line 20)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(ALLOWED_HEADERS)

        # Allowed methods (Go cors.go line 21)
        response.headers["Access-Control-Allow-Methods"] = ", ".join(ALLOWED_METHODS)


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware on the FastAPI application.

    This function adds the custom CORS middleware that matches the Go
    implementation's behavior.

    Args:
        app: The FastAPI application instance.

    Usage:
        from fastapi import FastAPI
        from app.cors import setup_cors

        app = FastAPI()
        setup_cors(app)
    """
    app.add_middleware(CORSMiddleware)


def create_cors_middleware(app: ASGIApp) -> CORSMiddleware:
    """Create a CORS middleware instance.

    Factory function for creating the middleware, useful for testing.

    Args:
        app: The ASGI application to wrap.

    Returns:
        CORSMiddleware: Configured CORS middleware instance.
    """
    return CORSMiddleware(app)


__all__ = [
    "ALLOWED_HEADERS",
    "ALLOWED_METHODS",
    "CORSMiddleware",
    "setup_cors",
    "create_cors_middleware",
]

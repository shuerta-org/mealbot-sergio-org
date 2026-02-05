"""CORS middleware configuration.

This module configures Cross-Origin Resource Sharing (CORS) to mirror
the Go implementation in cors.go.
"""

from flask import Flask
from flask_cors import CORS

# Headers allowed by CORS, matching the Go implementation
ACCESS_CONTROL_ALLOW_HEADERS = "Authorization, Content-Type, Origin, Accept, token"

# Methods allowed by CORS, matching the Go implementation
ACCESS_CONTROL_ALLOW_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]


def configure_cors(app: Flask) -> None:
    """Configure CORS for the Flask application.

    This mirrors the Go GetCorsHandler function behavior:
    - Access-Control-Allow-Origin: set to the request origin
    - Access-Control-Allow-Headers: Authorization, Content-Type, Origin, Accept, token
    - Access-Control-Allow-Methods: GET, POST, DELETE
    - OPTIONS requests are handled and return 200 with CORS headers

    Args:
        app: Flask application instance to configure.
    """
    CORS(
        app,
        # Allow all origins (matches Go's r.Header.Get("Origin") behavior)
        origins="*",
        # Support credentials (cookies, authorization headers)
        supports_credentials=True,
        # Allowed methods
        methods=ACCESS_CONTROL_ALLOW_METHODS,
        # Allowed headers
        allow_headers=list(ACCESS_CONTROL_ALLOW_HEADERS.split(", ")),
        # Expose headers to the browser
        expose_headers=["Content-Type", "Authorization"],
    )

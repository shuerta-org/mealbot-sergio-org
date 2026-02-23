"""CORS middleware for Flask.

Ports the Go app's cors.go behavior: sets Access-Control-Allow-Origin to
the request's Origin header, allows specific headers and methods, and
handles OPTIONS preflight requests by returning early with 200.
"""

from flask import request, make_response

# Matches Go's AccessControlAllowHeaders constant
ACCESS_CONTROL_ALLOW_HEADERS = "Authorization, Content-Type, Origin, Accept, token"

# Matches Go's allowed methods: "GET, POST, DELETE"
ACCESS_CONTROL_ALLOW_METHODS = "GET, POST, DELETE"


def init_app(app):
    """Register CORS middleware with the Flask app.

    Applies CORS headers to every response via after_request, and
    handles OPTIONS preflight requests via before_request.

    Args:
        app: Flask application instance.
    """

    @app.before_request
    def handle_preflight():
        """Handle CORS preflight OPTIONS requests.

        Returns an empty 200 response with CORS headers for OPTIONS
        requests, matching Go's behavior of returning early.
        """
        if request.method == "OPTIONS":
            response = make_response("", 200)
            origin = request.headers.get("Origin", "")
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = ACCESS_CONTROL_ALLOW_HEADERS
            response.headers["Access-Control-Allow-Methods"] = ACCESS_CONTROL_ALLOW_METHODS
            return response

    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to every response.

        Sets Access-Control-Allow-Origin to the request's Origin header,
        matching Go's behavior of echoing back the origin.
        """
        origin = request.headers.get("Origin", "")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = ACCESS_CONTROL_ALLOW_HEADERS
        response.headers["Access-Control-Allow-Methods"] = ACCESS_CONTROL_ALLOW_METHODS
        return response

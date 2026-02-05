"""Flask application factory for the mealbot application.

This module provides the application factory pattern for creating and
configuring the Flask application, mirroring the Go server.go structure.
"""

import json
from typing import Any, Optional

from flask import Flask, Response
from flask_restful import Api

from mealbot.config import Config, TestConfig
from mealbot.middleware.cors import configure_cors
from mealbot.routes.organizations import register_organization_routes
from mealbot.utils import err_to_bytes


def create_app(config_override: Optional[dict[str, Any]] = None) -> Flask:
    """Create and configure the Flask application.

    This is the application factory function that initializes the Flask app
    with all required configuration, middleware, and error handlers.

    Args:
        config_override: Optional dictionary of configuration overrides.
                        Useful for testing to override default settings.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration
    if config_override and config_override.get("TESTING"):
        app.config.from_object(TestConfig)
    else:
        app.config.from_object(Config)

    # Apply any configuration overrides
    if config_override:
        app.config.update(config_override)

    # Configure CORS (mirrors Go's GetCorsHandler middleware)
    configure_cors(app)

    # Initialize Flask-RESTful API
    api = Api(app)

    # Store api reference on app for route registration in other modules
    app.api = api  # type: ignore[attr-defined]

    # Register routes
    register_organization_routes(api)

    # Register global error handlers
    register_error_handlers(app)

    return app


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers for consistent JSON responses.

    Args:
        app: Flask application instance.
    """

    @app.errorhandler(400)
    def handle_bad_request(error: Exception) -> tuple[Response, int]:
        """Handle 400 Bad Request errors."""
        message = str(error.description) if hasattr(error, "description") else str(error)
        return Response(
            json.dumps({"message": message}),
            status=400,
            mimetype="application/json",
        ), 400

    @app.errorhandler(404)
    def handle_not_found(error: Exception) -> tuple[Response, int]:
        """Handle 404 Not Found errors."""
        return Response(
            json.dumps({"message": "Not Found"}),
            status=404,
            mimetype="application/json",
        ), 404

    @app.errorhandler(500)
    def handle_internal_error(error: Exception) -> tuple[Response, int]:
        """Handle 500 Internal Server Error."""
        message = str(error.description) if hasattr(error, "description") else str(error)
        return Response(
            json.dumps({"message": message}),
            status=500,
            mimetype="application/json",
        ), 500

    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception) -> tuple[Response, int]:
        """Handle any unhandled exceptions with JSON response."""
        app.logger.exception("Unhandled exception: %s", error)
        return Response(
            err_to_bytes(error),
            status=500,
            mimetype="application/json",
        ), 500

"""Flask application factory.

Migrated from server.go main() function. Creates and configures the Flask
application with route registration, static file serving, and middleware hooks.

The Go Middleware struct and Apply/ApplyFake methods are not directly ported —
Flask's decorator and before_request/after_request hooks replace them.
"""

import logging
import os

from flask import Flask, send_from_directory


def create_app(testing=False):
    """Create and configure the Flask application.

    Args:
        testing: If True, enable testing configuration.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path=None,
    )

    if testing:
        app.config["TESTING"] = True

    # Configure logging to stdout for Heroku compatibility
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Root route: serve static files, mirroring Go's http.FileServer(http.Dir("./static"))
    # In Go, GET / with FileServer serves index.html or directory listing from ./static.
    # Here we replicate that by serving files from the static directory.
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:filename>")
    def static_files(filename):
        return send_from_directory(app.static_folder, filename)

    # Organization domain routes (migrated from org.go, registered in server.go)
    from mealbot.org import (
        create_organization_handler,
        cross_match_trait_handler,
        get_organizations_handler,
    )

    _all_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    app.add_url_rule(
        "/orgs", "get_organizations", get_organizations_handler, methods=_all_methods
    )
    app.add_url_rule(
        "/org", "create_organization", create_organization_handler, methods=_all_methods
    )
    app.add_url_rule(
        "/crossmatchtrait",
        "cross_match_trait",
        cross_match_trait_handler,
        methods=_all_methods,
    )

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    application = create_app()
    application.run(host="0.0.0.0", port=port)

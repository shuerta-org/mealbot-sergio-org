"""Flask application entry point and route registration.

Ports the Go app's server.go: Flask initialization, middleware chain
(CORS + auth), route registration, static file serving, and PORT
configuration. CLI dispatch (pair, migrate) is deferred to Milestone 4.
"""

import os

from dotenv import load_dotenv
from flask import Flask, send_from_directory

# Load .env file early for local development
load_dotenv()

from mealbot import cors, auth, db
from mealbot.log import setup_logging
from mealbot.org import (
    get_organizations_handler,
    create_organization_handler,
    cross_match_trait_handler,
)


def create_app():
    """Create and configure the Flask application.

    Sets up middleware (CORS, auth, DB teardown), registers all routes,
    and configures static file serving.

    Returns:
        Configured Flask app instance.
    """
    app = Flask(__name__)

    # Setup logging
    setup_logging()

    # Register middleware (order matters: CORS first, then auth)
    cors.init_app(app)
    auth.init_app(app)

    # Register database teardown
    db.init_app(app)

    # --- Static file serving ---
    # Go serves static files at "/" via http.FileServer(http.Dir("./static"))
    # This means /privacy.html serves ./static/privacy.html
    # /sample.csv serves ./static/sample.csv
    # We replicate this with a catch-all route for static files

    @app.route("/")
    def serve_index():
        """Serve the static directory index.

        In Go, http.FileServer at "/" serves directory listings.
        For parity, we return an empty response or directory listing.
        """
        # Go's FileServer returns a directory listing; for simplicity,
        # we return 200 with an empty body (or could list files)
        return "", 200

    @app.route("/<path:filename>")
    def serve_static(filename):
        """Serve static files from the ./static directory.

        Matches Go's http.FileServer(http.Dir("./static")) behavior
        where /privacy.html maps to ./static/privacy.html.
        """
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
        return send_from_directory(static_dir, filename)

    # --- API routes ---
    # Register organization endpoints
    app.add_url_rule(
        "/orgs",
        "get_organizations",
        get_organizations_handler,
        methods=["GET", "POST", "DELETE", "OPTIONS"],
    )
    app.add_url_rule(
        "/org",
        "create_organization",
        create_organization_handler,
        methods=["GET", "POST", "DELETE", "OPTIONS"],
    )
    app.add_url_rule(
        "/crossmatchtrait",
        "cross_match_trait",
        cross_match_trait_handler,
        methods=["GET", "POST", "DELETE", "OPTIONS"],
    )

    return app


# Create the app instance for WSGI servers (gunicorn) and direct execution
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

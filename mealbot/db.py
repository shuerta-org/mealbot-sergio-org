"""Database connection helper and utilities.

Provides per-request database connections using Flask's g context,
backed by psycopg2 connecting to a PostgreSQL instance via DATABASE_URL.
Mirrors the Go app's server.CreateDBConnection pattern, but amortizes
to one connection per request rather than one per DB function call.
"""

import os

import psycopg2
import psycopg2.extras
from flask import g


def get_db():
    """Get a database connection for the current request.

    Opens a new connection on first call per request and caches it in
    Flask's g context. The connection is automatically closed at request
    teardown via close_db().

    Returns:
        psycopg2 connection object.

    Raises:
        psycopg2.OperationalError: If DATABASE_URL is not set or connection fails.
    """
    if "db" not in g:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable is not set")
        g.db = psycopg2.connect(database_url)
    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request.

    Called automatically by Flask's teardown_appcontext mechanism.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """Register the teardown handler with the Flask app.

    Args:
        app: Flask application instance.
    """
    app.teardown_appcontext(close_db)

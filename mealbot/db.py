"""Database connection helper using psycopg2 and DATABASE_URL.

Migrated from:
- vendor/github.com/johnamadeo/server/dbconn.go (CreateDBConnection, LocalDBConnection)
- db.go (DuplicateKeyErr constant, LocalDBConnection config)
- vendor/github.com/johnamadeo/server/jsonb.go (JSONB type)

JSONB handling note:
    The Go codebase uses a custom JSONB []byte type (jsonb.go) for inserting/retrieving
    JSONB columns from PostgreSQL. In Python with psycopg2, this is not needed —
    use psycopg2.extras.Json to wrap dicts/lists when inserting JSONB values, and
    psycopg2 automatically deserializes JSONB columns into Python dicts/lists on read.

    Example:
        from psycopg2.extras import Json
        cursor.execute(
            "INSERT INTO members (pair_counts) VALUES (%s)",
            (Json({"alice": 1}),)
        )
"""

import os

import psycopg2


# Error message substring when user tries to insert row with duplicate key.
# Matches the Go constant DuplicateKeyErr from db.go.
DUPLICATE_KEY_ERR = "duplicate key value violates unique constraint"


def get_db_connection():
    """Create and return a psycopg2 database connection.

    Reads DATABASE_URL from the environment. Handles the Heroku-style
    postgres:// scheme by rewriting it to postgresql:// for psycopg2
    compatibility.

    Mirrors Go's server.CreateDBConnection behavior: each caller gets a fresh
    connection and is responsible for closing it (use try/finally or a context
    manager).

    Returns:
        psycopg2 connection object.

    Raises:
        psycopg2.OperationalError: If the connection cannot be established.
        KeyError: If DATABASE_URL is not set.
    """
    database_url = os.environ["DATABASE_URL"]

    # Heroku sets DATABASE_URL with the postgres:// scheme, but psycopg2
    # requires postgresql://.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(database_url)

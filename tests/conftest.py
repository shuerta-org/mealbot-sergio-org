"""Pytest fixtures for the mealbot application tests.

This module provides fixtures for:
- Flask application instance with test configuration
- Flask test client for making HTTP requests
- Database setup and teardown
"""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from mealbot.app import create_app


@pytest.fixture(scope="session")
def app() -> Flask:
    """Create and configure a Flask application instance for testing.

    This fixture creates the application with TESTING mode enabled,
    which disables error catching during request handling for better
    error reports in tests.

    Yields:
        Configured Flask application instance.
    """
    test_app = create_app(
        config_override={
            "TESTING": True,
            "DEBUG": True,
        }
    )

    # Establish application context
    with test_app.app_context():
        yield test_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client for the Flask application.

    This client can be used to make requests to the application
    without running a server.

    Args:
        app: Flask application fixture.

    Returns:
        Flask test client instance.
    """
    return app.test_client()


@pytest.fixture
def runner(app: Flask):
    """Create a test CLI runner for the Flask application.

    Args:
        app: Flask application fixture.

    Returns:
        Flask test CLI runner instance.
    """
    return app.test_cli_runner()

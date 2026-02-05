"""Configuration management for the mealbot application.

This module handles loading configuration from environment variables,
with support for local development via python-dotenv.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Server configuration
    PORT: int = int(os.getenv("PORT", "8080"))
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    DEBUG: bool = FLASK_ENV == "development"

    # Database configuration
    # Mirrors the Go implementation: uses DATABASE_URL if set, otherwise builds
    # a local connection string
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Local database connection settings (used when DATABASE_URL is not set)
    DB_USER: str = os.getenv("DB_USER", "johnamadeodaniswara")
    DB_NAME: str = os.getenv("DB_NAME", "mealbot")

    # Mailgun configuration (for email service - used in later milestones)
    MAILGUN_SMTP_LOGIN: Optional[str] = os.getenv("MAILGUN_SMTP_LOGIN")
    MAILGUN_DOMAIN: Optional[str] = os.getenv("MAILGUN_DOMAIN")
    MAILGUN_API_KEY: Optional[str] = os.getenv("MAILGUN_API_KEY")

    # Auth0 configuration (for JWT verification - used in later milestones)
    AUTH0_DOMAIN: Optional[str] = os.getenv("AUTH0_DOMAIN")
    AUTH0_AUDIENCE: Optional[str] = os.getenv("AUTH0_AUDIENCE")
    AUTH0_CLIENT_ID: Optional[str] = os.getenv("AUTH0_CLIENT_ID")
    AUTH0_ALGORITHMS: str = os.getenv("AUTH0_ALGORITHMS", "RS256")

    @classmethod
    def get_database_url(cls) -> str:
        """Get the database connection URL.

        If DATABASE_URL environment variable is set (e.g., on Heroku),
        use it directly. Otherwise, build a local connection string
        matching the Go implementation's behavior.

        Returns:
            Database connection URL string.
        """
        if cls.DATABASE_URL:
            return cls.DATABASE_URL

        # Build local connection string matching Go's createLocalDBUrl
        return f"postgresql://{cls.DB_USER}@localhost/{cls.DB_NAME}?sslmode=disable"


class TestConfig(Config):
    """Test configuration with overrides for testing."""

    TESTING: bool = True
    DEBUG: bool = True

    # Use a test database if not specified
    DATABASE_URL: Optional[str] = os.getenv(
        "TEST_DATABASE_URL", os.getenv("DATABASE_URL")
    )

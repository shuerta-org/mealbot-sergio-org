"""Configuration management using Pydantic-Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    Configuration values are loaded in the following order of precedence:
    1. Environment variables
    2. .env file
    3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server configuration
    port: int = 8080

    # Database configuration (required)
    database_url: str

    # Mailgun configuration (optional - for email sending)
    mailgun_smtp_login: str | None = None
    mailgun_domain: str | None = None
    mailgun_api_key: str | None = None

    # Auth0 configuration (defaults match Go implementation constants)
    # See auth.go lines 17-21 for original values
    auth0_issuer: str = "https://mealbot.auth0.com/"
    auth0_audience: str = "https://mealbot-2.herokuapp.com/"
    auth0_jwks_url: str = "https://mealbot.auth0.com/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    """Get cached Settings instance.

    Uses lru_cache to ensure settings are only loaded once and
    reused across all calls. This provides a singleton-like pattern
    for configuration access.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()

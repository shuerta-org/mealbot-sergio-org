"""FastAPI application entry point.

This module creates and configures the FastAPI application instance with:
- Database engine lifecycle management (lifespan)
- CORS middleware configuration
- Authentication dependencies (available but no protected routes yet)
- Health check endpoint

Reference: Go implementation server.go lines 66-111
- Middleware handler chain (Auth then CORS)
- Route registration with ServeMux
- Port from environment, server listen

This is the "tracer bullet" module that proves the core infrastructure works.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .cors import setup_cors
from .database import dispose_engine, init_engine
from .logging_config import configure_logging, get_logger
from .organizations import router as organizations_router

# Configure logging at module load time
configure_logging()
logger = get_logger("mealbot.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Application lifespan context manager.

    Handles startup and shutdown events for the application:
    - Startup: Initialize database engine, log startup message
    - Shutdown: Dispose database engine, log shutdown message

    Reference: Go server.go doesn't explicitly have lifecycle management,
    but this provides cleaner resource handling than the Go approach of
    creating connections per-request.

    Args:
        app: The FastAPI application instance.

    Yields:
        None
    """
    # Startup
    logger.info("Application starting up...")

    try:
        await init_engine()
        logger.info("Database engine initialized successfully")
    except Exception as e:
        logger.log_error(e, 500, "lifespan_startup")
        raise

    yield

    # Shutdown
    logger.info("Application shutting down...")

    try:
        await dispose_engine()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.log_error(e, 500, "lifespan_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Factory function that creates a fully configured FastAPI app with:
    - Lifespan management for database connections
    - CORS middleware matching Go implementation
    - Health check endpoint
    - Configured for adding authentication and routes later

    Returns:
        FastAPI: Configured application instance.

    Usage:
        app = create_app()
        # For running: uvicorn app.main:app
    """
    app = FastAPI(
        title="Mealbot API",
        description="Pairing and scheduling application API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS middleware (matches Go cors.go behavior)
    setup_cors(app)

    # Register health check endpoint
    app.add_api_route("/health", health_check, methods=["GET"])

    # Include organizations router
    # Reference: Go server.go lines 97-99 - /org, /orgs, /crossmatchtrait routes
    app.include_router(organizations_router)
    logger.info("Organizations router registered")

    logger.info("FastAPI application created and configured")

    return app


async def health_check() -> JSONResponse:
    """Health check endpoint.

    Simple endpoint to verify the application is running and responding
    to requests. Does not require authentication.

    Reference: Not in Go implementation - added for operational monitoring
    as specified in PROJECT.md section 5.1.

    Returns:
        JSONResponse: Health status response.

    Example Response:
        {"status": "healthy", "service": "mealbot"}
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "mealbot",
        }
    )


# Create the application instance for uvicorn
app = create_app()


__all__ = [
    "app",
    "create_app",
    "health_check",
    "lifespan",
]

"""FastAPI application entry point.

This module creates and configures the FastAPI application instance with:
- Database engine lifecycle management (lifespan)
- CORS middleware configuration
- Authentication dependencies (available but no protected routes yet)
- Health check endpoint
- Static file serving (privacy.html, sample.csv)

Reference: Go implementation server.go lines 66-111
- Middleware handler chain (Auth then CORS)
- Route registration with ServeMux
- Port from environment, server listen
- Static file serving: serveMux.Handle("/", http.FileServer(http.Dir("./static")))

This is the "tracer bullet" module that proves the core infrastructure works.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .cors import setup_cors
from .database import dispose_engine, init_engine
from .logging_config import configure_logging, get_logger

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
    - Static file serving from /static directory
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

    # Mount static files at root path (lowest precedence, added last)
    # Reference: Go server.go line 103 - http.FileServer(http.Dir("./static"))
    # Static files are served without authentication
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Static files mounted from {static_dir}")
    else:
        logger.warning(
            f"Static directory not found at {static_dir}, "
            "static files will not be served"
        )

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

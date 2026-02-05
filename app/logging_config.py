"""Structured logging configuration for the application.

This module provides logging utilities that mirror the structured logging
behavior of the Go implementation's log.go, which uses logrus with fields
for context.

Reference: Go implementation log.go lines 1-35
- LogAndWriteErr: Logs errors with status, function name fields
- LogAndWrite: Logs success with function field
- Uses logrus structured logging

The Python implementation uses the standard logging module with structured
JSON output for production environments and human-readable output for
development.
"""

import json
import logging
import os
import sys
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging output.

    Produces log entries as JSON objects with fields matching the Go
    logrus implementation style:
    - timestamp
    - level
    - message
    - function (when provided)
    - status (when provided)
    - Additional context fields
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            str: JSON-formatted log entry.
        """
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add function name if available (mirrors Go log.go "function" field)
        if hasattr(record, "func_name") and record.func_name:
            log_entry["function"] = record.func_name

        # Add status code if available (mirrors Go log.go "status" field)
        if hasattr(record, "status_code") and record.status_code:
            log_entry["status"] = record.status_code

        # Add any extra fields
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_entry.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development environments.

    Produces colored, structured output that's easy to read during
    development while still showing the same fields as production.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",   # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability.

        Args:
            record: The log record to format.

        Returns:
            str: Formatted log entry.
        """
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]

        parts = [
            f"{color}{record.levelname:<8}{reset}",
            f"{self.formatTime(record, self.datefmt)}",
            f"{record.name}",
        ]

        # Add function name if available
        if hasattr(record, "func_name") and record.func_name:
            parts.append(f"[{record.func_name}]")

        # Add status code if available
        if hasattr(record, "status_code") and record.status_code:
            parts.append(f"(status={record.status_code})")

        parts.append(record.getMessage())

        # Add extra fields if present
        if hasattr(record, "extra_fields") and record.extra_fields:
            parts.append(f"fields={record.extra_fields}")

        formatted = " | ".join(parts)

        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def get_log_level() -> int:
    """Get log level from environment variable.

    Reads LOG_LEVEL environment variable, defaulting to INFO.
    Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL

    Returns:
        int: Logging level constant.
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging(
    app_name: str = "mealbot",
    use_json: bool | None = None,
) -> logging.Logger:
    """Configure application logging.

    Sets up structured logging with either JSON output (production) or
    human-readable output (development).

    Args:
        app_name: Name for the logger.
        use_json: Whether to use JSON format. If None, auto-detects based
                  on environment (ENVIRONMENT=production uses JSON).

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Determine format based on environment if not specified
    if use_json is None:
        use_json = os.getenv("ENVIRONMENT", "").lower() == "production"

    # Get or create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(get_log_level())

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(get_log_level())

    # Set formatter based on environment
    if use_json:
        formatter = StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
    else:
        formatter = DevelopmentFormatter(datefmt="%Y-%m-%d %H:%M:%S")

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context fields to log records.

    Provides methods that mirror the Go log.go functions:
    - log_error: Like LogAndWriteErr
    - log_success: Like LogAndWrite
    - log_with_context: General-purpose with custom fields
    """

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Process log message and kwargs.

        Args:
            msg: Log message.
            kwargs: Keyword arguments.

        Returns:
            Tuple of processed message and kwargs.
        """
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

    def log_error(
        self,
        error: Exception | str,
        status_code: int,
        function: str,
        **extra_fields: Any,
    ) -> None:
        """Log an error with context (mirrors Go LogAndWriteErr).

        Args:
            error: The error or error message.
            status_code: HTTP status code.
            function: Name of the function where error occurred.
            **extra_fields: Additional context fields.
        """
        extra = {
            "func_name": function,
            "status_code": status_code,
            "extra_fields": extra_fields if extra_fields else None,
        }
        self.error(str(error), extra=extra)

    def log_success(
        self,
        message: str,
        function: str,
        status_code: int | None = None,
        **extra_fields: Any,
    ) -> None:
        """Log a success message with context (mirrors Go LogAndWrite).

        Args:
            message: Success message.
            function: Name of the function.
            status_code: Optional HTTP status code.
            **extra_fields: Additional context fields.
        """
        extra = {
            "func_name": function,
            "status_code": status_code,
            "extra_fields": extra_fields if extra_fields else None,
        }
        self.debug(message, extra=extra)

    def log_with_context(
        self,
        level: int,
        message: str,
        function: str | None = None,
        status_code: int | None = None,
        **extra_fields: Any,
    ) -> None:
        """Log a message with context fields.

        Args:
            level: Logging level (e.g., logging.INFO).
            message: Log message.
            function: Optional function name.
            status_code: Optional HTTP status code.
            **extra_fields: Additional context fields.
        """
        extra = {
            "func_name": function,
            "status_code": status_code,
            "extra_fields": extra_fields if extra_fields else None,
        }
        self.log(level, message, extra=extra)


def get_logger(
    name: str = "mealbot",
    **context: Any,
) -> LoggerAdapter:
    """Get a logger adapter with optional context.

    Creates a LoggerAdapter that includes the specified context fields
    in all log entries.

    Args:
        name: Logger name.
        **context: Context fields to include in all log entries.

    Returns:
        LoggerAdapter: Logger adapter with context.
    """
    base_logger = logging.getLogger(name)
    return LoggerAdapter(base_logger, context)


# Convenience function for quick logging setup
def setup_logging() -> LoggerAdapter:
    """Quick setup for application logging.

    Configures logging and returns a logger adapter ready for use.

    Returns:
        LoggerAdapter: Configured logger adapter.

    Usage:
        from app.logging_config import setup_logging
        logger = setup_logging()
        logger.log_error(error, 500, "handle_request")
    """
    configure_logging()
    return get_logger()


__all__ = [
    "StructuredFormatter",
    "DevelopmentFormatter",
    "LoggerAdapter",
    "configure_logging",
    "get_log_level",
    "get_logger",
    "setup_logging",
]

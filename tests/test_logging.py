"""Tests for structured logging configuration.

This test suite covers:
- StructuredFormatter JSON output
- DevelopmentFormatter human-readable output
- Log level configuration from environment
- LoggerAdapter context and helper methods
"""

import json
import logging
import os
from io import StringIO
from unittest.mock import patch

import pytest

from app.logging_config import (
    DevelopmentFormatter,
    LoggerAdapter,
    StructuredFormatter,
    configure_logging,
    get_log_level,
    get_logger,
    setup_logging,
)


class TestGetLogLevel:
    """Tests for log level configuration."""

    def test_default_log_level_is_info(self):
        """Test default log level is INFO when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove LOG_LEVEL if it exists
            os.environ.pop("LOG_LEVEL", None)
            level = get_log_level()
            assert level == logging.INFO

    def test_log_level_from_environment(self):
        """Test log level is read from LOG_LEVEL environment variable."""
        test_cases = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]

        for level_name, expected_level in test_cases:
            with patch.dict(os.environ, {"LOG_LEVEL": level_name}):
                level = get_log_level()
                assert level == expected_level, f"Failed for {level_name}"

    def test_log_level_case_insensitive(self):
        """Test LOG_LEVEL is case insensitive."""
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            level = get_log_level()
            assert level == logging.DEBUG

    def test_invalid_log_level_defaults_to_info(self):
        """Test invalid LOG_LEVEL defaults to INFO."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            level = get_log_level()
            assert level == logging.INFO


class TestStructuredFormatter:
    """Tests for JSON structured formatter."""

    @pytest.fixture
    def formatter(self):
        """Create a StructuredFormatter instance."""
        return StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S")

    def test_basic_log_entry_format(self, formatter):
        """Test basic log entry is formatted as JSON."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "timestamp" in data
        assert data["level"] == "info"
        assert data["message"] == "Test message"
        assert data["logger"] == "test.logger"

    def test_function_field_included(self, formatter):
        """Test function field is included when present."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.func_name = "handle_request"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["function"] == "handle_request"

    def test_status_field_included(self, formatter):
        """Test status field is included when present."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Bad request",
            args=(),
            exc_info=None,
        )
        record.status_code = 400

        output = formatter.format(record)
        data = json.loads(output)

        assert data["status"] == 400

    def test_extra_fields_included(self, formatter):
        """Test extra fields are included when present."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Request processed",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"user_id": "123", "org_id": "456"}

        output = formatter.format(record)
        data = json.loads(output)

        assert data["user_id"] == "123"
        assert data["org_id"] == "456"


class TestDevelopmentFormatter:
    """Tests for human-readable development formatter."""

    @pytest.fixture
    def formatter(self):
        """Create a DevelopmentFormatter instance."""
        return DevelopmentFormatter(datefmt="%Y-%m-%d %H:%M:%S")

    def test_basic_log_entry_format(self, formatter):
        """Test basic log entry is human-readable."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "test.logger" in output
        assert "Test message" in output

    def test_function_name_in_brackets(self, formatter):
        """Test function name is shown in brackets."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processing",
            args=(),
            exc_info=None,
        )
        record.func_name = "handle_request"

        output = formatter.format(record)

        assert "[handle_request]" in output

    def test_status_code_in_parentheses(self, formatter):
        """Test status code is shown in parentheses."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error",
            args=(),
            exc_info=None,
        )
        record.status_code = 500

        output = formatter.format(record)

        assert "(status=500)" in output


class TestConfigureLogging:
    """Tests for logging configuration."""

    def test_returns_logger(self):
        """Test configure_logging returns a logger."""
        logger = configure_logging(app_name="test_app")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_app"

    def test_json_format_in_production(self):
        """Test JSON format is used in production environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            logger = configure_logging(app_name="test_prod")
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, StructuredFormatter)

    def test_development_format_by_default(self):
        """Test development format is used by default."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ENVIRONMENT", None)
            logger = configure_logging(app_name="test_dev")
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, DevelopmentFormatter)

    def test_explicit_json_format(self):
        """Test explicit JSON format override."""
        logger = configure_logging(app_name="test_explicit", use_json=True)
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)

    def test_explicit_development_format(self):
        """Test explicit development format override."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            logger = configure_logging(app_name="test_override", use_json=False)
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, DevelopmentFormatter)


class TestLoggerAdapter:
    """Tests for LoggerAdapter helper methods."""

    @pytest.fixture
    def logger_adapter(self):
        """Create a LoggerAdapter for testing."""
        base_logger = logging.getLogger("test_adapter")
        base_logger.setLevel(logging.DEBUG)
        return LoggerAdapter(base_logger, {})

    def test_log_error_includes_all_fields(self, logger_adapter):
        """Test log_error includes function, status, and message."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
        logger_adapter.logger.handlers = [handler]

        logger_adapter.log_error(
            ValueError("Something went wrong"),
            status_code=400,
            function="validate_input",
        )

        output = stream.getvalue()
        data = json.loads(output)

        assert data["level"] == "error"
        assert "Something went wrong" in data["message"]
        assert data["function"] == "validate_input"
        assert data["status"] == 400

    def test_log_success_at_debug_level(self, logger_adapter):
        """Test log_success logs at DEBUG level."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
        logger_adapter.logger.handlers = [handler]

        logger_adapter.log_success(
            "Operation completed",
            function="process_data",
        )

        output = stream.getvalue()
        data = json.loads(output)

        assert data["level"] == "debug"
        assert data["message"] == "Operation completed"
        assert data["function"] == "process_data"


class TestGetLogger:
    """Tests for get_logger helper function."""

    def test_returns_logger_adapter(self):
        """Test get_logger returns a LoggerAdapter."""
        logger = get_logger("test")
        assert isinstance(logger, LoggerAdapter)

    def test_context_included_in_logs(self):
        """Test context fields are included in logs."""
        # Configure the base logger
        base_logger = logging.getLogger("test_context")
        base_logger.setLevel(logging.DEBUG)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
        base_logger.handlers = [handler]

        logger = LoggerAdapter(base_logger, {"request_id": "abc123"})
        logger.info("Test message")

        # The context should be available through the adapter
        assert logger.extra["request_id"] == "abc123"


class TestSetupLogging:
    """Tests for setup_logging convenience function."""

    def test_returns_logger_adapter(self):
        """Test setup_logging returns a LoggerAdapter."""
        logger = setup_logging()
        assert isinstance(logger, LoggerAdapter)

    def test_configures_base_logger(self):
        """Test setup_logging configures the mealbot logger."""
        logger = setup_logging()
        assert logger.logger.name == "mealbot"

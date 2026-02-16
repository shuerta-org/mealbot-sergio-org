"""Logging utilities replacing Logrus-based functions from log.go.

Migrated from log.go:
- LogAndWriteErr(w, err, status, function)
- LogAndWrite(w, bytes, status, function)
- LogAndWriteStatusBadRequest(w, err, function)
- LogAndWriteStatusInternalServerError(w, err, function)

Uses Python's standard logging module. Logs to stdout/stderr for
Heroku log drain compatibility.
"""

import logging

from flask import make_response

from mealbot.utils import err_to_bytes

logger = logging.getLogger("mealbot")


def log_and_write_err(err, status, function):
    """Log an error with structured fields and return an error HTTP response.

    Go equivalent: LogAndWriteErr(w, err, status, function)

    Args:
        err: The exception or error object.
        status: HTTP status code.
        function: Name of the calling function (for structured logging).

    Returns:
        Flask Response with JSON error body and the given status code.
    """
    logger.error(
        "%s",
        str(err),
        extra={"status": status, "function": function},
    )
    response = make_response(err_to_bytes(err), status)
    response.content_type = "application/json"
    return response


def log_and_write(body, status, function):
    """Log a debug message and return an HTTP response with the given body.

    Go equivalent: LogAndWrite(w, bytes, status, function)

    Args:
        body: The response body (string or bytes).
        status: HTTP status code.
        function: Name of the calling function (for structured logging).

    Returns:
        Flask Response with the given body and a 200 status code.
    """
    logger.debug(
        "%s",
        str(status),
        extra={"function": function},
    )
    response = make_response(body, 200)
    response.content_type = "application/json"
    return response


def log_and_write_status_bad_request(err, function):
    """Convenience wrapper for 400 Bad Request errors.

    Go equivalent: LogAndWriteStatusBadRequest(w, err, function)

    Args:
        err: The exception or error object.
        function: Name of the calling function.

    Returns:
        Flask Response with 400 status and JSON error body.
    """
    return log_and_write_err(err, 400, function)


def log_and_write_status_internal_server_error(err, function):
    """Convenience wrapper for 500 Internal Server Error.

    Go equivalent: LogAndWriteStatusInternalServerError(w, err, function)

    Args:
        err: The exception or error object.
        function: Name of the calling function.

    Returns:
        Flask Response with 500 status and JSON error body.
    """
    return log_and_write_err(err, 500, function)

"""Utility functions for logging and query parameter handling.

This module provides helper functions that mirror the Go implementation's
log.go and utils.go files:
- Logging utilities with structured fields
- Query parameter parsing
- JSON response helpers (str_to_bytes, err_to_bytes)
"""

import json
import logging
from typing import Optional

from flask import Request, Response, request

# Configure logging with structured output similar to logrus
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mealbot")


def str_to_bytes(message: str) -> bytes:
    """Convert a string message to JSON bytes with {"message": ...} format.

    This mirrors the Go server.StrToBytes() function.

    Args:
        message: The message string to convert.

    Returns:
        JSON bytes in the format {"message": "text"}.
    """
    return json.dumps({"message": message}).encode("utf-8")


def err_to_bytes(err: Exception) -> bytes:
    """Convert an exception to JSON bytes with {"message": ...} format.

    This mirrors the Go server.ErrToBytes() function.

    Args:
        err: The exception to convert.

    Returns:
        JSON bytes in the format {"message": "error text"}.
    """
    return json.dumps({"message": str(err)}).encode("utf-8")


def log_and_write_err(
    err: Exception, status: int, function: str
) -> tuple[Response, int]:
    """Log an error and return a JSON response.

    This mirrors the Go LogAndWriteErr() function.

    Args:
        err: The exception to log and return.
        status: HTTP status code.
        function: Name of the function where error occurred.

    Returns:
        Tuple of (Flask Response with JSON body, status code).
    """
    logger.error(
        "Error in %s: %s",
        function,
        str(err),
        extra={"logger": "logrus", "status": status, "function": function},
    )
    response = Response(
        err_to_bytes(err),
        status=status,
        mimetype="application/json",
    )
    return response, status


def log_and_write(data: bytes, status: int, function: str) -> tuple[Response, int]:
    """Log a success and return a JSON response.

    This mirrors the Go LogAndWrite() function.

    Args:
        data: The bytes to write in the response body.
        status: HTTP status code.
        function: Name of the function.

    Returns:
        Tuple of (Flask Response, status code).
    """
    logger.debug(
        "Success in %s",
        function,
        extra={"logger": "logrus", "function": function},
    )
    response = Response(
        data,
        status=status,
        mimetype="application/json",
    )
    return response, status


def log_and_write_status_bad_request(
    err: Exception, function: str
) -> tuple[Response, int]:
    """Log and return a 400 Bad Request response.

    This mirrors the Go LogAndWriteStatusBadRequest() function.

    Args:
        err: The exception to log and return.
        function: Name of the function where error occurred.

    Returns:
        Tuple of (Flask Response with JSON body, 400 status code).
    """
    return log_and_write_err(err, 400, function)


def log_and_write_status_internal_server_error(
    err: Exception, function: str
) -> tuple[Response, int]:
    """Log and return a 500 Internal Server Error response.

    This mirrors the Go LogAndWriteStatusInternalServerError() function.

    Args:
        err: The exception to log and return.
        function: Name of the function where error occurred.

    Returns:
        Tuple of (Flask Response with JSON body, 500 status code).
    """
    return log_and_write_err(err, 500, function)


def get_query_param(req: Optional[Request] = None, key: str = "") -> str:
    """Get a single query parameter from the request.

    This mirrors the Go getQueryParam() function. Returns an error
    if the parameter is missing or if multiple values are provided.

    Args:
        req: Flask Request object. If None, uses the current request context.
        key: The query parameter key to retrieve.

    Returns:
        The query parameter value.

    Raises:
        ValueError: If the parameter is missing or has multiple values.
    """
    if req is None:
        req = request

    values = req.args.getlist(key)
    if not values or len(values) > 1:
        raise ValueError(f"Request query parameters must contain {key}")
    return values[0]


def get_query_params(req: Optional[Request] = None, keys: Optional[list[str]] = None) -> list[str]:
    """Get multiple query parameters from the request.

    This mirrors the Go getQueryParams() function. Returns an error
    if any parameter is missing or if multiple values are provided for any key.

    Args:
        req: Flask Request object. If None, uses the current request context.
        keys: List of query parameter keys to retrieve.

    Returns:
        List of query parameter values in the same order as keys.

    Raises:
        ValueError: If any parameter is missing or has multiple values.
    """
    if req is None:
        req = request
    if keys is None:
        keys = []

    values = []
    for key in keys:
        query_values = req.args.getlist(key)
        if not query_values or len(query_values) > 1:
            raise ValueError(f"Request query parameters does not contain {key}")
        values.append(query_values[0])
    return values

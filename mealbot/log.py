"""Logging setup and HTTP response helpers.

Ports the Go app's log.go helpers (LogAndWrite, LogAndWriteErr) and the
vendor server.StrToBytes / server.ErrToBytes response formatting. All
JSON error/success responses use the {"Message": "..."} shape to maintain
API contract parity with the Go implementation.
"""

import logging

from flask import jsonify, make_response

logger = logging.getLogger("mealbot")


def setup_logging():
    """Configure application logging.

    Sets up structured logging similar to the Go app's logrus usage.
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def str_to_response(message, status=200):
    """Create a JSON response with a Message field.

    Equivalent to Go's server.StrToBytes wrapped in an HTTP response.

    Args:
        message: The string message to include.
        status: HTTP status code (default 200).

    Returns:
        Flask Response with {"Message": "..."} JSON body.
    """
    response = make_response(jsonify({"Message": message}), status)
    return response


def err_to_response(err, status=500):
    """Create a JSON error response with a Message field.

    Equivalent to Go's server.ErrToBytes wrapped in an HTTP response.

    Args:
        err: The error (string or Exception) to include.
        status: HTTP status code (default 500).

    Returns:
        Flask Response with {"Message": "..."} JSON body.
    """
    message = str(err)
    response = make_response(jsonify({"Message": message}), status)
    return response


def log_and_write(data, status, function):
    """Log a successful response and return it.

    Equivalent to Go's LogAndWrite function.

    Args:
        data: The response data (dict or list) to return as JSON.
        status: HTTP status code.
        function: Name of the calling function (for log context).

    Returns:
        Flask Response with JSON body.
    """
    logger.debug("%s: %s", function, status)
    response = make_response(jsonify(data), status)
    return response


def log_and_write_err(err, status, function):
    """Log an error and return an error response.

    Equivalent to Go's LogAndWriteErr function.

    Args:
        err: The error (string or Exception).
        status: HTTP status code.
        function: Name of the calling function (for log context).

    Returns:
        Flask Response with {"Message": "..."} JSON body.
    """
    logger.error("status=%s function=%s error=%s", status, function, err)
    return err_to_response(err, status)


def log_and_write_status_bad_request(err, function):
    """Log and return a 400 Bad Request error response.

    Equivalent to Go's LogAndWriteStatusBadRequest.

    Args:
        err: The error message.
        function: Name of the calling function.

    Returns:
        Flask Response with 400 status.
    """
    return log_and_write_err(err, 400, function)


def log_and_write_status_internal_server_error(err, function):
    """Log and return a 500 Internal Server Error response.

    Equivalent to Go's LogAndWriteStatusInternalServerError.

    Args:
        err: The error message.
        function: Name of the calling function.

    Returns:
        Flask Response with 500 status.
    """
    return log_and_write_err(err, 500, function)

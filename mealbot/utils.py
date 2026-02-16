"""Response helpers and query parameter helpers.

Migrated from:
- vendor/github.com/johnamadeo/server/response.go (StrToBytes, ErrToBytes)
- vendor/github.com/johnamadeo/server/auth.go (Message struct)
- utils.go (getQueryParam, getQueryParams)
"""

import json

from flask import request


def str_to_bytes(message):
    """Convert a string message to a JSON-encoded bytes string matching Go's Message struct.

    Go equivalent: server.StrToBytes(message string) []byte
    Produces: {"Message": "..."}  (capital M to match Go struct serialization)

    Args:
        message: The string message to wrap.

    Returns:
        JSON string with the Message envelope.
    """
    return json.dumps({"Message": message})


def err_to_bytes(err):
    """Convert an exception to a JSON-encoded bytes string matching Go's Message struct.

    Go equivalent: server.ErrToBytes(err error) []byte
    Produces: {"Message": "..."}  (capital M to match Go struct serialization)

    Args:
        err: An exception or any object whose str() gives the error message.

    Returns:
        JSON string with the Message envelope.
    """
    return json.dumps({"Message": str(err)})


def get_query_param(key):
    """Retrieve a single query parameter from the current Flask request.

    Go equivalent: getQueryParam(r *http.Request, key string) (string, error)
    Raises an error if the parameter is missing or has multiple values.

    Args:
        key: The query parameter key to retrieve.

    Returns:
        The string value of the query parameter.

    Raises:
        ValueError: If the parameter is missing or has multiple values.
    """
    values = request.args.getlist(key)
    if len(values) == 0 or len(values) > 1:
        raise ValueError("Request query parameters must contain " + key)
    return values[0]


def get_query_params(keys):
    """Retrieve multiple query parameters from the current Flask request.

    Go equivalent: getQueryParams(r *http.Request, keys []string) ([]string, error)
    Raises an error if any parameter is missing or has multiple values.

    Args:
        keys: List of query parameter keys to retrieve.

    Returns:
        List of string values corresponding to each key.

    Raises:
        ValueError: If any parameter is missing or has multiple values.
    """
    values = []
    for key in keys:
        key_values = request.args.getlist(key)
        if len(key_values) == 0 or len(key_values) > 1:
            raise ValueError("Request query parameters does not contain " + key)
        values.append(key_values[0])
    return values

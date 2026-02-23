"""Shared utility helpers.

Ports the Go app's utils.go query parameter extraction functions.
"""

from flask import request


def get_query_param(key):
    """Extract a single query parameter from the current request.

    Equivalent to Go's getQueryParam. Returns an error if the parameter
    is missing or has multiple values.

    Args:
        key: The query parameter name.

    Returns:
        tuple: (value, None) on success, or (None, error_message) on failure.
    """
    values = request.args.getlist(key)
    if len(values) == 0 or len(values) > 1:
        return None, f"Request query parameters must contain {key}"
    return values[0], None


def get_query_params(keys):
    """Extract multiple query parameters from the current request.

    Equivalent to Go's getQueryParams. Returns an error if any parameter
    is missing or has multiple values.

    Args:
        keys: List of query parameter names.

    Returns:
        tuple: (values_list, None) on success, or (None, error_message) on failure.
    """
    values = []
    for key in keys:
        param_values = request.args.getlist(key)
        if len(param_values) == 0 or len(param_values) > 1:
            return None, f"Request query parameters does not contain {key}"
        values.append(param_values[0])
    return values, None

"""Consistent API response and error formatting utilities."""

from flask import jsonify


STATUS_CODE_TO_CODE = {
    400: "INVALID_REQUEST",
    404: "RESOURCE_NOT_FOUND",
    409: "STATE_CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    500: "INTERNAL_SERVER_ERROR",
}


def api_error(message, code=None, status_code=400, data=None):
    """Construct a consistent JSON error response.

    Format:
    {
        "success": False,
        "data": None,
        "error": {
            "code": "...",
            "message": "..."
        }
    }
    """
    if code is None:
        code = STATUS_CODE_TO_CODE.get(status_code, "ERROR")

    return jsonify({
        "success": False,
        "data": data,
        "error": {
            "code": code,
            "message": str(message),
        },
    }), status_code


def api_success(data=None, status_code=200, **kwargs):
    """Construct a consistent JSON success response."""
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload), status_code

"""Small WSGI API for container health checks and planner requests."""

import json
from datetime import datetime

from app.service import build_week_plan


def _response(start_response, status, data):
    body = json.dumps(data, ensure_ascii=False, default=lambda value: value.isoformat()).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def create_app(client=None):
    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")
        if method == "GET" and path == "/health":
            return _response(start_response, "200 OK", {"status": "ok"})
        if method != "POST" or path != "/plan":
            return _response(start_response, "404 Not Found", {"error": "not_found"})
        try:
            length = int(environ.get("CONTENT_LENGTH", "0"))
            if not 0 < length <= 65536:
                raise ValueError("invalid body length")
            payload = json.loads(environ["wsgi.input"].read(length))
            if not isinstance(payload, dict):
                raise ValueError("body must be an object")
            now = datetime.fromisoformat(payload["now"])
            result = build_week_plan(now, payload["busy"], payload["sleep"], payload["tasks"], client)
        except (ValueError, TypeError, KeyError, UnicodeDecodeError):
            return _response(start_response, "400 Bad Request", {"error": "invalid_request"})
        return _response(start_response, "200 OK", result)

    return application

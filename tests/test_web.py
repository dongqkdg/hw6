"""Exercise HTTP handling in memory, without opening a socket."""

import io
import json

from app.web import create_app


def request(app, method, path, payload=None):
    body = b"" if payload is None else json.dumps(payload).encode()
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    statuses = []
    response = b"".join(app(environ, lambda status, headers: statuses.append(status)))
    return statuses[0], json.loads(response)


def test_health_endpoint_is_ready_without_llm():
    status, body = request(create_app(), "GET", "/health")
    assert status == "200 OK"
    assert body == {"status": "ok"}


def test_plan_endpoint_returns_schedule_with_explicit_now():
    app = create_app()
    status, body = request(app, "POST", "/plan", {
        "now": "2026-11-23T09:00:00+09:00",
        "busy": "월 09:00-10:00",
        "sleep": "매일 23:00-07:00",
        "tasks": "보고서|60|월 12:00|2",
    })
    assert status == "200 OK"
    assert body["scheduled"][0]["start"] == "2026-11-23T10:00:00+09:00"
    assert body["metrics"]["fallbacks"] == 1


def test_plan_endpoint_rejects_bad_json():
    app = create_app()
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/plan",
        "CONTENT_LENGTH": "4",
        "wsgi.input": io.BytesIO(b"nope"),
    }
    statuses = []
    body = b"".join(app(environ, lambda status, headers: statuses.append(status)))
    assert statuses == ["400 Bad Request"]
    assert json.loads(body)["error"] == "invalid_request"

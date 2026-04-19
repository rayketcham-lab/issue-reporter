"""HTTP-level tests for server.py.

Spins up the real HTTPServer on an ephemeral port in a background thread,
then exercises every endpoint through http.client. create_issue is patched so
the tests don't need the `gh` CLI to be installed or authenticated.
"""

from __future__ import annotations

import http.client
import json
import threading
import time
from http.server import HTTPServer
from unittest.mock import patch

import pytest

import server


@pytest.fixture
def running_server():
    """Start an HTTPServer on an ephemeral port for the duration of one test."""
    server._rate_buckets.clear()
    handler = server.make_handler(
        repo_dir=".",
        allowed_origins="https://example.com",
        auth_token="",
    )
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def running_server_with_auth():
    server._rate_buckets.clear()
    handler = server.make_handler(
        repo_dir=".",
        allowed_origins="https://example.com",
        auth_token="s3cret",
    )
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()


def _post(httpd, path, body=None, headers=None, raw=None):
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    try:
        payload = raw if raw is not None else json.dumps(body or {}).encode("utf-8")
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        conn.request("POST", path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


def _get(httpd, path):
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


def _options(httpd, path, origin="https://example.com"):
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    try:
        conn.request("OPTIONS", path, headers={"Origin": origin})
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_valid_post_returns_200_and_issue_url(self, running_server):
        with patch("server.create_issue", return_value="https://github.com/o/r/issues/1"):
            status, _, body = _post(
                running_server, "/api/report",
                {"description": "Login is broken", "type": "bug", "severity": "high"},
            )
        assert status == 200
        payload = json.loads(body)
        assert payload["success"] is True
        assert payload["url"] == "https://github.com/o/r/issues/1"

    def test_health_endpoint(self, running_server):
        status, _, body = _get(running_server, "/health")
        assert status == 200
        assert json.loads(body) == {"status": "ok"}


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

class TestCORS:
    def test_preflight_returns_204_with_cors_headers(self, running_server):
        status, headers, _ = _options(running_server, "/api/report")
        assert status == 204
        assert headers.get("Access-Control-Allow-Origin") == "https://example.com"
        assert "POST" in headers.get("Access-Control-Allow-Methods", "")
        assert "OPTIONS" in headers.get("Access-Control-Allow-Methods", "")

    def test_post_response_includes_cors_header(self, running_server):
        with patch("server.create_issue", return_value="https://x/y/issues/1"):
            status, headers, _ = _post(
                running_server, "/api/report",
                {"description": "x"},
            )
        assert status == 200
        assert headers.get("Access-Control-Allow-Origin") == "https://example.com"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_missing_bearer_returns_401(self, running_server_with_auth):
        status, _, body = _post(
            running_server_with_auth, "/api/report",
            {"description": "x"},
        )
        assert status == 401
        assert json.loads(body)["success"] is False

    def test_wrong_token_returns_401(self, running_server_with_auth):
        status, _, _ = _post(
            running_server_with_auth, "/api/report",
            {"description": "x"},
            headers={"Authorization": "Bearer wrong"},
        )
        assert status == 401

    def test_correct_token_passes_auth(self, running_server_with_auth):
        with patch("server.create_issue", return_value="https://x/y/issues/1"):
            status, _, _ = _post(
                running_server_with_auth, "/api/report",
                {"description": "x"},
                headers={"Authorization": "Bearer s3cret"},
            )
        assert status == 200


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_six_requests_triggers_429(self, running_server):
        with patch("server.create_issue", return_value="https://x/y/issues/1"):
            statuses = []
            for _ in range(6):
                s, _, _ = _post(running_server, "/api/report", {"description": "x"})
                statuses.append(s)
        assert statuses[:5] == [200, 200, 200, 200, 200]
        assert statuses[5] == 429

    def test_rate_limit_is_per_ip(self, running_server):
        server._rate_buckets.clear()
        assert server._is_rate_limited("1.1.1.1") is False
        for _ in range(4):
            assert server._is_rate_limited("1.1.1.1") is False
        assert server._is_rate_limited("1.1.1.1") is True
        assert server._is_rate_limited("2.2.2.2") is False

    def test_rate_limit_window_expires(self, running_server):
        server._rate_buckets.clear()
        now = time.monotonic()
        server._rate_buckets["3.3.3.3"] = [now - 120] * 5  # all outside window
        assert server._is_rate_limited("3.3.3.3") is False


# ---------------------------------------------------------------------------
# Malformed payloads
# ---------------------------------------------------------------------------

class TestMalformedPayloads:
    def test_empty_body_returns_400(self, running_server):
        status, _, _ = _post(running_server, "/api/report", raw=b"")
        assert status == 400

    def test_oversized_body_returns_400(self, running_server):
        # Send bogus Content-Length header larger than 65536
        conn = http.client.HTTPConnection(
            "127.0.0.1", running_server.server_address[1], timeout=5,
        )
        try:
            conn.putrequest("POST", "/api/report")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", "100000")
            conn.endheaders()
            # Don't send body — we're only testing the Content-Length gate
            # Send something short so the server doesn't hang
            conn.send(b'{"description":"x"}')
            resp = conn.getresponse()
            assert resp.status == 400
        finally:
            conn.close()

    def test_invalid_json_returns_400(self, running_server):
        status, _, body = _post(running_server, "/api/report", raw=b"{not json")
        assert status == 400
        assert "Invalid JSON" in json.loads(body)["error"]

    def test_missing_description_returns_400(self, running_server):
        status, _, body = _post(running_server, "/api/report", {"type": "bug"})
        assert status == 400
        assert "description" in json.loads(body)["error"].lower()

    def test_invalid_type_falls_back_to_bug(self, running_server):
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return "https://x/y/issues/1"

        with patch("server.create_issue", side_effect=fake_create):
            status, _, _ = _post(
                running_server, "/api/report",
                {"description": "x", "type": "not-a-real-type"},
            )
        assert status == 200
        assert captured["issue_type"] == "bug"

    def test_unknown_path_returns_404(self, running_server):
        status, _, _ = _post(running_server, "/api/other", {"description": "x"})
        assert status == 404

    def test_unknown_get_path_returns_404(self, running_server):
        status, _, _ = _get(running_server, "/not-a-real-path")
        assert status == 404


# ---------------------------------------------------------------------------
# Sanitizers
# ---------------------------------------------------------------------------

class TestSanitizers:
    def test_sanitize_url_strips_javascript_scheme(self):
        assert server._sanitize_url("javascript:alert(1)") == ""

    def test_sanitize_url_strips_data_uri(self):
        assert server._sanitize_url("data:text/html,<script>") == ""

    def test_sanitize_url_allows_https(self):
        assert server._sanitize_url("https://example.com/foo") == "https://example.com/foo"

    def test_sanitize_url_allows_http(self):
        assert server._sanitize_url("http://example.com") == "http://example.com"

    def test_sanitize_url_strips_relative_path(self):
        assert server._sanitize_url("/just/a/path") == ""

    def test_sanitize_url_caps_length(self):
        long = "https://example.com/" + "a" * 3000
        assert len(server._sanitize_url(long)) <= 2000

    def test_sanitize_url_empty(self):
        assert server._sanitize_url("") == ""

    def test_sanitize_meta_strips_markdown_image(self):
        assert server._sanitize_meta("![x](https://evil.com/steal.png)") == "x"

    def test_sanitize_meta_strips_markdown_link(self):
        assert server._sanitize_meta("[click me](https://evil.com)") == "click me"

    def test_sanitize_meta_preserves_plain_text(self):
        assert server._sanitize_meta("hello world") == "hello world"

    def test_sanitize_meta_truncates_long_input(self):
        long = "a" * 1000
        assert len(server._sanitize_meta(long)) == 500


# ---------------------------------------------------------------------------
# Adversarial — XSS payloads in captured fields must not break the server
# ---------------------------------------------------------------------------

class TestAdversarial:
    @pytest.mark.parametrize("payload", [
        "<script>alert(1)</script>",
        "\"><img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "'; DROP TABLE issues; --",
        "\x00\x01\x02binary",
    ])
    def test_xss_payloads_do_not_crash_server(self, running_server, payload):
        with patch("server.create_issue", return_value="https://x/y/issues/1"):
            status, _, _ = _post(
                running_server, "/api/report",
                {
                    "description": payload,
                    "page_title": payload,
                    "element_text": payload,
                    "console_errors": payload,
                },
            )
        assert status == 200

    def test_markdown_injection_stripped_before_gh(self, running_server):
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return "https://x/y/issues/1"

        with patch("server.create_issue", side_effect=fake_create):
            _post(
                running_server, "/api/report",
                {
                    "description": "real bug",
                    "page_title": "![x](https://evil.com/a.png)",
                    "element_text": "[click](https://evil.com)",
                },
            )
        assert "evil.com" not in captured["page_title"]
        assert "evil.com" not in captured["element_text"]

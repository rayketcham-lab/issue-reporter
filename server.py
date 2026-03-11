#!/usr/bin/env python3
"""Lightweight issue-reporter backend server.

Accepts POST /api/report from the web widget, creates GitHub issues via `gh` CLI,
and returns the issue URL. Stdlib only -- no Flask, no FastAPI.

Usage:
    python server.py --repo /path/to/my-project --port 8787
    python server.py --repo . --allowed-origins "https://mysite.com"

Requires:
    - Python 3.10+
    - gh CLI (authenticated): https://cli.github.com
"""

from __future__ import annotations

import argparse
import hmac
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------

RATE_LIMIT = 5          # max requests per window
RATE_WINDOW = 60        # window in seconds

# IP -> list of request timestamps
_rate_buckets: dict[str, list[float]] = {}


def _is_rate_limited(ip: str) -> bool:
    """Return True if the IP has exceeded the rate limit."""
    now = time.monotonic()
    bucket = _rate_buckets.get(ip, [])
    # Prune timestamps outside the window
    bucket = [t for t in bucket if now - t < RATE_WINDOW]
    _rate_buckets[ip] = bucket

    if len(bucket) >= RATE_LIMIT:
        return True

    bucket.append(now)
    return False


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

VALID_TYPES = {"bug", "feature_request", "data_issue", "ui_bug", "broken_link", "performance", "other"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}

# Strip markdown image/link injection from structured metadata fields
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")  # ![alt](url)
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")    # [text](url)
_FIELD_MAX = 500  # max length for metadata fields


def _sanitize_meta(value: str) -> str:
    """Sanitize a metadata field — strip markdown injection, enforce length."""
    value = _MD_IMAGE_RE.sub(r"\1", value)  # ![alt](evil) → alt
    value = _MD_LINK_RE.sub(r"\1", value)   # [text](evil) → text
    return value[:_FIELD_MAX]


def _sanitize_url(value: str) -> str:
    """Validate URL starts with http(s) and sanitize."""
    value = value.strip()[:2000]
    if value and not value.startswith(("http://", "https://")):
        return ""
    return _sanitize_meta(value)


# ---------------------------------------------------------------------------
# Issue creation via gh CLI
# ---------------------------------------------------------------------------

# Map issue types to conventional-commit prefixes
_PREFIX_MAP = {
    "bug": "fix",
    "feature_request": "feat",
    "data_issue": "data",
    "ui_bug": "fix",
    "performance": "perf",
    "other": "issue",
}

# Map issue types to GitHub labels
_LABEL_MAP = {
    "bug": ["bug"],
    "feature_request": ["enhancement"],
    "data_issue": ["bug", "data"],
    "ui_bug": ["bug", "ui"],
    "performance": ["performance"],
    "other": ["bug"],
}


def create_issue(
    description: str,
    issue_type: str,
    severity: str,
    context: str,
    project_name: str,
    page_url: str,
    repo_dir: str,
    expected_behavior: str = "",
    page_title: str = "",
    page_type: str = "",
    section: str = "",
    element_text: str = "",
    console_errors: str = "",
    last_api_calls: str = "",
) -> str:
    """Create a GitHub issue. Returns the issue URL. Raises on failure."""

    prefix = _PREFIX_MAP.get(issue_type, "issue")

    # Build title: first 60 chars of description, single line
    title_text = description[:60].split("\n")[0]
    if len(description) > 60:
        title_text = title_text.rsplit(" ", 1)[0] + "..."
    title = f"{prefix}: {title_text}"

    # Build body — matches the format used by the JS widget's direct GitHub mode
    parts = [f"## Summary\n\n{description}"]

    # Context section
    context_lines: list[str] = []
    if page_url:
        context_lines.append(f"- **Page:** {page_url}")
    if page_title:
        context_lines.append(f"- **Page Title:** {page_title}")
    if section:
        context_lines.append(f"- **Section:** {section}")
    if element_text:
        context_lines.append(f"- **Element:** {element_text}")
    if context_lines:
        parts.append("\n## Context\n\n" + "\n".join(context_lines))

    # Expected behavior
    if expected_behavior:
        parts.append(f"\n## Expected Behavior\n\n{expected_behavior}")

    # Console errors
    if console_errors:
        parts.append(f"\n## Console Errors\n\n```\n{console_errors}\n```")

    # Recent API calls
    if last_api_calls:
        parts.append(f"\n## Recent API Calls\n\n```\n{last_api_calls}\n```")

    # Metadata
    meta_lines = [
        f"- **Type:** {issue_type}",
        f"- **Severity:** {severity}",
    ]
    if project_name:
        meta_lines.append(f"- **Project:** {project_name}")

    parts.append("\n## Metadata\n\n" + "\n".join(meta_lines))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts.append(f"\n---\n*Reported via issue-reporter on {timestamp}*")

    body = "\n".join(parts)

    # Labels
    labels = list(_LABEL_MAP.get(issue_type, ["bug"]))
    if severity == "critical":
        labels.append("critical")

    # Build gh command
    cmd: list[str] = ["gh", "issue", "create", "--title", title, "--body", body]
    for label in labels:
        cmd.extend(["--label", label])

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=15, cwd=repo_dir,
    )

    if result.returncode == 0:
        return result.stdout.strip()

    # Retry without labels if they don't exist in the repo yet
    if labels and "label" in result.stderr.lower():
        cmd_retry: list[str] = ["gh", "issue", "create", "--title", title, "--body", body]
        result2 = subprocess.run(
            cmd_retry, capture_output=True, text=True, timeout=15, cwd=repo_dir,
        )
        if result2.returncode == 0:
            return result2.stdout.strip()

    raise RuntimeError(f"gh issue create failed: {result.stderr.strip()}")


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class ReportHandler(BaseHTTPRequestHandler):
    """Handles POST /api/report and serves CORS preflight."""

    # Set by the factory function
    repo_dir: str = "."
    allowed_origins: str = "*"
    auth_token: str = ""

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", self.allowed_origins)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        """CORS preflight."""
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/api/report":
            self._send_json(404, {"success": False, "error": "Not found"})
            return

        # Auth check
        if self.auth_token:
            auth_header = self.headers.get("Authorization", "")
            if not hmac.compare_digest(auth_header, f"Bearer {self.auth_token}"):
                self._send_json(401, {"success": False, "error": "Unauthorized"})
                return

        # Rate limiting
        client_ip = self.client_address[0]
        if _is_rate_limited(client_ip):
            self._send_json(429, {
                "success": False,
                "error": "Rate limit exceeded. Try again in a minute.",
            })
            return

        # Read and parse body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0 or content_length > 65536:
            self._send_json(400, {"success": False, "error": "Invalid request body"})
            return

        try:
            raw = self.rfile.read(content_length)
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"success": False, "error": "Invalid JSON"})
            return

        # Validate required fields
        description = (data.get("description") or "").strip()
        if not description:
            self._send_json(400, {"success": False, "error": "description is required"})
            return

        # Validate and sanitize all fields
        issue_type = data.get("type", "bug")
        if issue_type not in VALID_TYPES:
            issue_type = "other"

        severity = data.get("severity", "medium")
        if severity not in VALID_SEVERITIES:
            severity = "medium"

        description = description[:5000]  # cap freeform text
        context = (data.get("context") or "").strip()[:2000]
        project_name = _sanitize_meta((data.get("project_name") or "").strip())
        page_url = _sanitize_url((data.get("page_url") or ""))
        expected_behavior = (data.get("expected_behavior") or "").strip()[:2000]
        page_title = _sanitize_meta((data.get("page_title") or "").strip())
        page_type = _sanitize_meta((data.get("page_type") or "").strip())
        section = _sanitize_meta((data.get("section") or "").strip())
        element_text = _sanitize_meta((data.get("element_text") or "").strip())
        console_errors = (data.get("console_errors") or "").strip()[:3000]
        last_api_calls = (data.get("last_api_calls") or "").strip()[:2000]

        # Create issue
        try:
            url = create_issue(
                description=description,
                issue_type=issue_type,
                severity=severity,
                context=context,
                project_name=project_name,
                page_url=page_url,
                repo_dir=self.repo_dir,
                expected_behavior=expected_behavior,
                page_title=page_title,
                page_type=page_type,
                section=section,
                element_text=element_text,
                console_errors=console_errors,
                last_api_calls=last_api_calls,
            )
            self._send_json(200, {"success": True, "url": url})
            self.log_message("Created issue: %s", url)
        except FileNotFoundError:
            self._send_json(500, {
                "success": False,
                "error": "gh CLI not found on server. Install from https://cli.github.com",
            })
        except subprocess.TimeoutExpired:
            self._send_json(504, {
                "success": False,
                "error": "GitHub API timed out. Try again.",
            })
        except Exception as exc:
            self.log_message("Issue creation failed: %s", str(exc))
            self._send_json(500, {"success": False, "error": "Failed to create issue. Please try again."})

    def do_GET(self) -> None:
        """Health check endpoint."""
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"success": False, "error": "Not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        """Override to add timestamp prefix."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        sys.stderr.write(f"[{timestamp}] {fmt % args}\n")


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

def make_handler(
    repo_dir: str,
    allowed_origins: str,
    auth_token: str,
) -> type[ReportHandler]:
    """Create a handler class with bound configuration."""

    class ConfiguredHandler(ReportHandler):
        pass

    ConfiguredHandler.repo_dir = repo_dir
    ConfiguredHandler.allowed_origins = allowed_origins
    ConfiguredHandler.auth_token = auth_token
    return ConfiguredHandler


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lightweight issue-reporter backend server",
    )
    parser.add_argument(
        "--port", type=int, default=8787,
        help="Port to listen on (default: 8787)",
    )
    parser.add_argument(
        "--repo", default=".",
        help="Repository directory for gh CLI (default: current directory)",
    )
    parser.add_argument(
        "--allowed-origins", default="*",
        help='CORS allowed origins (default: "*")',
    )
    parser.add_argument(
        "--token", default="",
        help="Optional auth token clients must send as Bearer token",
    )
    args = parser.parse_args()

    # Verify gh is available
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10, cwd=args.repo,
        )
    except FileNotFoundError:
        print("Error: 'gh' CLI not found. Install from https://cli.github.com", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Warning: gh auth status timed out, continuing anyway.", file=sys.stderr)

    handler = make_handler(args.repo, args.allowed_origins, args.token)
    server = HTTPServer(("0.0.0.0", args.port), handler)

    print(f"issue-reporter server listening on http://0.0.0.0:{args.port}")
    print(f"  POST /api/report  — create issues")
    print(f"  GET  /health      — health check")
    print(f"  Repo: {args.repo}")
    print(f"  CORS: {args.allowed_origins}")
    if args.token:
        print("  Auth: Bearer token required")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()

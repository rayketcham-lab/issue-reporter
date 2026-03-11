#!/usr/bin/env python3
"""Standalone GitHub issue reporter — creates structured issues from user feedback.

Only requirement: gh CLI (free, authenticated with your GitHub account).

Usage:
    # Interactive mode
    python issue_reporter.py

    # CLI mode
    python issue_reporter.py --type bug --severity high "The login button is broken"

    # Pipe mode
    echo "Description here" | python issue_reporter.py --type feature_request

    # As a library
    from issue_reporter import IssueReporter
    reporter = IssueReporter.from_config("issue-reporter.json")
    url = reporter.report("The button is broken", issue_type="bug")

Requirements:
    - gh CLI (authenticated): https://cli.github.com  (FREE)
    - Python 3.10+

Optional AI backend (for smarter formatting — works fine without):
    - Anthropic Claude: pip install httpx, set ANTHROPIC_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default issue types — override via config file or IssueReporter constructor
DEFAULT_ISSUE_TYPES: list[dict[str, str]] = [
    {"id": "bug", "label": "Bug Report", "description": "Something is broken or not working correctly"},
    {"id": "feature_request", "label": "Feature Request", "description": "I want something new or different"},
    {"id": "data_issue", "label": "Data Issue", "description": "Data is wrong, missing, or outdated"},
    {"id": "ui_bug", "label": "UI / Display Bug", "description": "Layout or visual issue"},
    {"id": "performance", "label": "Performance", "description": "Something is slow or unresponsive"},
    {"id": "other", "label": "Other", "description": "Something else"},
]

DEFAULT_LABELS: dict[str, list[str]] = {
    "bug": ["bug"],
    "feature_request": ["enhancement"],
    "data_issue": ["bug", "data"],
    "ui_bug": ["bug", "ui"],
    "performance": ["performance"],
    "other": ["bug"],
}

DEFAULT_SYSTEM_PROMPT = """You are a QA assistant. Take raw user feedback and structure it into a clean, actionable GitHub issue.

Respond with ONLY valid JSON (no markdown fencing), with these fields:
- "title": concise issue title under 70 chars, prefixed appropriately (e.g., "fix: ...", "feat: ...")
- "body": well-structured GitHub issue body in markdown with ## Summary, ## Steps to Reproduce (if applicable), ## Expected Behavior, ## Current Behavior sections
- "labels": array of 1-3 labels from: {valid_labels}"""


@dataclass
class IssueReporter:
    """Configurable issue reporter that creates GitHub issues from user feedback."""

    # Project context
    project_name: str = ""
    project_description: str = ""
    repo_dir: str = "."

    # Issue types and labels
    issue_types: list[dict[str, str]] = field(default_factory=lambda: list(DEFAULT_ISSUE_TYPES))
    label_map: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_LABELS))
    valid_labels: frozenset[str] = field(default_factory=lambda: frozenset({
        "bug", "enhancement", "data", "ui", "performance",
        "documentation", "critical",
    }))

    # AI configuration (optional — works fine without any AI)
    system_prompt: str = ""
    api_key: str = ""  # Anthropic API key (optional)
    model: str = "claude-sonnet-4-20250514"

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not self.system_prompt:
            self.system_prompt = DEFAULT_SYSTEM_PROMPT.format(
                valid_labels=", ".join(sorted(self.valid_labels))
            )
            if self.project_name:
                self.system_prompt = (
                    f"The project is called \"{self.project_name}\". "
                    f"{self.project_description}\n\n{self.system_prompt}"
                )

    # ------------------------------------------------------------------
    # Config file loading
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, path: str | Path) -> IssueReporter:
        """Load configuration from a YAML or JSON file."""
        path = Path(path)
        if not path.exists():
            return cls()

        text = path.read_text()
        if path.suffix in (".yml", ".yaml"):
            try:
                import yaml
                cfg = yaml.safe_load(text) or {}
            except ImportError:
                print("Warning: PyYAML not installed, trying JSON parse", file=sys.stderr)
                cfg = json.loads(text)
        else:
            cfg = json.loads(text)

        return cls(
            project_name=cfg.get("project_name", ""),
            project_description=cfg.get("project_description", ""),
            repo_dir=cfg.get("repo_dir", "."),
            issue_types=cfg.get("issue_types", DEFAULT_ISSUE_TYPES),
            label_map=cfg.get("label_map", DEFAULT_LABELS),
            valid_labels=frozenset(cfg.get("valid_labels", DEFAULT_LABELS.keys())),
            system_prompt=cfg.get("system_prompt", ""),
            api_key=cfg.get("api_key", ""),
            model=cfg.get("model", "claude-sonnet-4-20250514"),
        )

    # ------------------------------------------------------------------
    # Issue creation
    # ------------------------------------------------------------------

    def report(
        self,
        description: str,
        *,
        issue_type: str = "bug",
        severity: str = "medium",
        context: dict[str, str] | None = None,
    ) -> str | None:
        """Create a GitHub issue. Returns the issue URL or None on failure."""
        issue = self._structure_issue(description, issue_type, severity, context or {})
        return self._create_gh_issue(issue["title"], issue["body"], issue["labels"])

    def _structure_issue(
        self,
        description: str,
        issue_type: str,
        severity: str,
        context: dict[str, str],
    ) -> dict[str, Any]:
        """Structure user feedback into an issue.

        Tries Claude API first (if configured), then falls back to deterministic formatting.
        """
        if self.api_key:
            result = self._ai_structure(description, issue_type, severity, context)
            if result:
                return result
        # Deterministic fallback (always works)
        return self._fallback_structure(description, issue_type, severity, context)

    def _ai_structure(
        self,
        description: str,
        issue_type: str,
        severity: str,
        context: dict[str, str],
    ) -> dict[str, Any] | None:
        """Use Claude API to structure the issue. Returns None on failure."""
        try:
            import httpx
        except ImportError:
            return None

        context_lines = "\n".join(f"**{k}:** {v}" for k, v in context.items()) if context else "None"
        user_msg = (
            f"Structure this user feedback into a GitHub issue:\n\n"
            f"**Issue Type:** {issue_type}\n"
            f"**Severity:** {severity}\n"
            f"{context_lines}\n\n"
            f"**User Description:**\n{description}"
        )

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1024,
                        "system": self.system_prompt,
                        "messages": [{"role": "user", "content": user_msg}],
                    },
                )
                response.raise_for_status()

            data = response.json()
            content = data.get("content", [])
            if content and content[0].get("type") == "text":
                text = content[0]["text"].strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text.rsplit("\n", 1)[0] if "\n" in text else text[:-3]
                parsed = json.loads(text)
                return self._validate_ai_response(parsed, issue_type)
        except Exception as exc:
            print(f"AI structuring failed, using fallback: {exc}", file=sys.stderr)
        return None

    def _validate_ai_response(self, parsed: dict, issue_type: str) -> dict[str, Any] | None:
        """Validate AI-generated issue structure."""
        if not isinstance(parsed, dict):
            return None
        title = parsed.get("title", "")
        body = parsed.get("body", "")
        labels = parsed.get("labels", [])

        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(body, str) or not body.strip():
            return None

        title = title[:120]
        body = body[:10000]

        if not isinstance(labels, list):
            labels = self.label_map.get(issue_type, ["bug"])
        labels = [lb for lb in labels if isinstance(lb, str) and lb in self.valid_labels]
        if not labels:
            labels = self.label_map.get(issue_type, ["bug"])

        return {"title": title, "body": body, "labels": labels[:3]}

    def _fallback_structure(
        self,
        description: str,
        issue_type: str,
        severity: str,
        context: dict[str, str],
    ) -> dict[str, Any]:
        """Create a structured issue without AI."""
        prefix_map = {
            "bug": "fix",
            "feature_request": "feat",
            "data_issue": "data",
            "ui_bug": "fix",
            "performance": "perf",
            "other": "issue",
        }
        prefix = prefix_map.get(issue_type, "issue")

        title_text = description[:60].split("\n")[0]
        if len(description) > 60:
            title_text = title_text.rsplit(" ", 1)[0] + "..."
        title = f"{prefix}: {title_text}"

        body_parts = [f"## Summary\n\n{description}"]

        if context:
            ctx_lines = "\n".join(f"- **{k}:** {v}" for k, v in context.items())
            body_parts.append(f"\n## Context\n\n{ctx_lines}")

        body_parts.append(f"\n## Metadata\n\n- **Type:** {issue_type}\n- **Severity:** {severity}")

        labels = list(self.label_map.get(issue_type, ["bug"]))
        if severity == "critical":
            labels.append("critical")

        return {"title": title, "body": "\n".join(body_parts), "labels": labels}

    def _create_gh_issue(self, title: str, body: str, labels: list[str]) -> str | None:
        """Create a GitHub issue using the gh CLI. Returns the issue URL or None."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        body += f"\n\n---\n*Reported via issue-reporter on {timestamp}*"

        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        for label in labels:
            cmd.extend(["--label", label])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15, cwd=self.repo_dir,
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                print(f"Created issue: {url}")
                return url

            # Retry without labels if they don't exist yet
            if "--label" in " ".join(cmd) and "label" in result.stderr.lower():
                cmd_no_labels = ["gh", "issue", "create", "--title", title, "--body", body]
                result2 = subprocess.run(
                    cmd_no_labels, capture_output=True, text=True, timeout=15, cwd=self.repo_dir,
                )
                if result2.returncode == 0:
                    url = result2.stdout.strip()
                    print(f"Created issue (without labels): {url}")
                    return url

            print(f"gh issue create failed: {result.stderr}", file=sys.stderr)
        except FileNotFoundError:
            print("Error: 'gh' CLI not found. Install from https://cli.github.com", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print("Error: gh issue create timed out after 15s", file=sys.stderr)
        except Exception as exc:
            print(f"Error creating issue: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def _interactive_report(reporter: IssueReporter) -> str | None:
    """Run interactive issue reporting wizard in the terminal."""
    print("\n=== Issue Reporter ===\n")

    # Step 1: Issue type
    print("Issue type:")
    for i, it in enumerate(reporter.issue_types, 1):
        print(f"  {i}. {it['label']} — {it['description']}")

    while True:
        choice = input(f"\nSelect type [1-{len(reporter.issue_types)}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(reporter.issue_types):
                issue_type = reporter.issue_types[idx]["id"]
                break
        except ValueError:
            pass
        print("Invalid choice, try again.")

    # Step 2: Severity
    severities = ["low", "medium", "high", "critical"]
    print(f"\nSeverity: {', '.join(f'{i+1}.{s}' for i, s in enumerate(severities))}")
    sev_choice = input("Select severity [1-4, default=2]: ").strip()
    try:
        severity = severities[int(sev_choice) - 1]
    except (ValueError, IndexError):
        severity = "medium"

    # Step 3: Description
    print("\nDescribe the issue (press Enter twice to finish):")
    lines: list[str] = []
    empty_count = 0
    while True:
        line = input()
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append("")
        else:
            empty_count = 0
            lines.append(line)
    description = "\n".join(lines).strip()

    if not description:
        print("No description provided. Aborting.")
        return None

    # Step 4: Optional context
    context: dict[str, str] = {}
    add_ctx = input("\nAdd context? (file path, URL, etc.) [y/N]: ").strip().lower()
    if add_ctx in ("y", "yes"):
        while True:
            key = input("  Key (or empty to finish): ").strip()
            if not key:
                break
            value = input(f"  {key}: ").strip()
            if value:
                context[key] = value

    # Step 5: Confirm
    print(f"\n--- Preview ---")
    print(f"Type: {issue_type} | Severity: {severity}")
    print(f"Description: {description[:100]}{'...' if len(description) > 100 else ''}")
    if context:
        print(f"Context: {context}")

    confirm = input("\nCreate issue? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        print("Cancelled.")
        return None

    return reporter.report(description, issue_type=issue_type, severity=severity, context=context)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub issue reporter — structured issues from plain feedback",
        epilog="Examples:\n"
               "  %(prog)s                                    # Interactive mode\n"
               '  %(prog)s --type bug "Login is broken"       # Quick CLI mode\n'
               '  echo "Slow query" | %(prog)s --type perf    # Pipe mode\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("description", nargs="?", help="Issue description (or omit for interactive)")
    parser.add_argument("--type", "-t", default="bug", help="Issue type (default: bug)")
    parser.add_argument("--severity", "-s", default="medium", choices=["low", "medium", "high", "critical"])
    parser.add_argument("--config", "-c", default="issue-reporter.json", help="Config file path")
    parser.add_argument("--repo", "-r", default=".", help="Repository directory")
    parser.add_argument("--context", "-x", nargs=2, action="append", metavar=("KEY", "VALUE"),
                        help="Add context (repeatable): --context file src/app.py")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without creating")

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if config_path.exists():
        reporter = IssueReporter.from_config(config_path)
    else:
        reporter = IssueReporter()

    if args.repo != ".":
        reporter.repo_dir = args.repo

    # Get description from args, stdin, or interactive
    description = args.description
    if not description and not sys.stdin.isatty():
        description = sys.stdin.read().strip()

    if not description:
        # Interactive mode
        url = _interactive_report(reporter)
        sys.exit(0 if url else 1)

    # CLI mode
    context = dict(args.context) if args.context else {}

    if args.dry_run:
        issue = reporter._structure_issue(description, args.type, args.severity, context)
        print(f"Title: {issue['title']}")
        print(f"Labels: {issue['labels']}")
        print(f"\n{issue['body']}")
        return

    url = reporter.report(description, issue_type=args.type, severity=args.severity, context=context)
    sys.exit(0 if url else 1)


if __name__ == "__main__":
    main()

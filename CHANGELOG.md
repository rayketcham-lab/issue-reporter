# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.3.0] - 2026-04-19

### Removed
- **Bash CLI** (`issue-reporter.sh`) and **Python CLI** (`issue_reporter.py`) —
  use `gh issue create` directly if you need terminal access.
- **Reference backend** (`server.py`) and pip packaging (`pyproject.toml`) —
  the widget now ships only as a browser-embedded JS file.
- **Backend Integration** section from the README and docs site — the
  `endpoint:` init option remains in the widget as an undocumented escape
  hatch for anyone running a custom backend.
- Python test suite (`tests/`) and associated CI jobs (`ruff`, `shellcheck`,
  `pytest` on ubuntu/postgres/windows runners).
- `python` from CodeQL matrix, `pip` ecosystem from dependabot.

### Changed
- README + docs site pinned to `@v2.3.0` with refreshed SRI hashes.
- Threat Model simplified: single deployment mode (direct GitHub API).
- `SECURITY.md` scope narrowed to widget + CI/release workflows.
- `CONTRIBUTING.md` rewritten for a JS-only project — no Python tooling.

## [Prior] Added in 2.2.x
- `SECURITY.md` with private vulnerability disclosure policy.
- `CONTRIBUTING.md` covering release workflow.
- Threat Model + Content Security Policy sections in the README.
- Supply-chain pinning guidance (regenerate SRI on version bump).
- `.github/dependabot.yml` for weekly GitHub Actions updates.
- `.github/workflows/codeql.yml` scanning JavaScript.
- `.github/CODEOWNERS` requiring review on widget/workflows.
- `CHANGELOG.md` tracking user-visible changes.

## [2.2.0] - 2026-03-12

See the [v2.2.0 release](https://github.com/rayketcham-lab/issue-reporter/releases/tag/v2.2.0).

## [2.1.0] - 2026-03-01

### Security
- Validate `issue_type` against a whitelist (fixes #3).

## [2.0.0] - 2026-02-15

Initial tracked release — widget, CLIs, reference backend.

# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `SECURITY.md` with private vulnerability disclosure policy.
- `CONTRIBUTING.md` covering test, lint, and release workflow.
- Threat Model + Content Security Policy sections in the README.
- Supply-chain pinning guidance (regenerate SRI on version bump).
- `.github/dependabot.yml` for weekly GitHub Actions + pip updates.
- `.github/workflows/codeql.yml` scanning JavaScript + Python.
- `.github/CODEOWNERS` requiring review on widget/server/workflows.
- CI jobs for `ruff check` and `shellcheck`.
- `tests/test_server_http.py` — 34 new HTTP-level tests covering rate-limit,
  CORS, auth, malformed payloads, sanitizers, and adversarial XSS payloads.
- `PROJECT_NAME` and `REPO_DIR` config vars are now used by `issue-reporter.sh`.
- `CHANGELOG.md` tracking user-visible changes.

### Changed
- README script tags pinned back to `@v2.2.0` with `integrity=sha384-...` +
  `crossorigin="anonymous"` (reverts the `@main` change from #11).
- CLI `curl` examples pinned to the `v2.2.0` tag.
- README framework snippets now link to `server.py` as the production reference
  and list the must-have safeguards.

### Fixed
- `ruff` F541 in `issue_reporter.py:270`, `server.py:411-412` (f-strings with
  no placeholders).
- `shellcheck` SC2034 in `issue-reporter.sh` (`PROJECT_NAME`, `REPO_DIR`
  declared but unused — now wired up).

## [2.2.0] - 2026-03-12

See the [v2.2.0 release](https://github.com/rayketcham-lab/issue-reporter/releases/tag/v2.2.0).

## [2.1.0] - 2026-03-01

### Security
- Validate `issue_type` against a whitelist (fixes #3).

## [2.0.0] - 2026-02-15

Initial tracked release — widget, CLIs, reference backend.

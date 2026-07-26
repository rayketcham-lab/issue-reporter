# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Query strings and fragments are stripped from captured API URLs before they
  are written into the issue body. The fetch-capture wrapper records recent
  same-origin `/api/` calls, and query strings on host-app requests can carry
  secrets (`?token=`, `?sig=`, session ids) that would otherwise be exfiltrated
  into a potentially public issue. The path is still reported, so the debugging
  signal is preserved. (#34)

### Fixed
- **Accessibility:** the report modal now implements the full WAI-ARIA dialog
  focus-management pattern. Focus moves into the dialog on every step (not just
  step 1), `Tab`/`Shift+Tab` are trapped and wrap within the modal, the rest of
  the page is made `inert` + `aria-hidden` while the modal is open, and focus is
  restored to the triggering element on close by any path. Fixes a WCAG 2.1
  2.4.3 / 4.1.2 gap. (#26, #34)
- The `✕` and Done buttons passed the click `Event` as `closeModal`'s
  `silent` argument, which suppressed state reset and focus restoration. (#34)

### Added
- CI: `Validate widget + docs integrity` — checks JS syntax and asserts the SRI
  hash documented in `README.md` and `docs/index.html` matches the sha384 of
  `issue-reporter.js` at the pinned immutable tag, rejecting mutable refs like
  `@main`. (#27)
- CI: `A11y focus tests (jsdom)` — runs `tests/a11y_focus.test.mjs` and
  `tests/fetch_capture_redaction.test.mjs` on push and PR. (#34)

### Changed
- CI: `github/codeql-action` bumped to v4.37.2 and `actions/checkout` to v7.0.1,
  both SHA-pinned. Dependabot now groups the `codeql-action` sub-actions so
  `init` and `analyze` are bumped in a single PR — splitting them breaks the
  analyze step with a config-version mismatch. (#38, #40)

## [2.3.0] - 2026-04-19

### Removed
- **Bash CLI** (`issue-reporter.sh`) and **Python CLI** (`issue_reporter.py`) —
  use `gh issue create` directly if you need terminal access.
- **Reference backend** (`server.py`) and pip packaging (`pyproject.toml`) —
  the widget now ships only as a browser-embedded JS file.
- **Backend Integration** section from the README and docs site. The
  `endpoint:` init option remains in the widget source as an undocumented
  escape hatch for custom backends — it is not surfaced in JSDoc, error
  messages, or either doc site.
- Python test suite (`tests/`) and associated CI jobs (`ruff`, `shellcheck`,
  `pytest` on ubuntu/postgres/windows runners).
- `python` from CodeQL matrix, `pip` ecosystem from dependabot.

### Changed
- Widget header and JSDoc relicensed in-file from MIT to Apache-2.0 (the
  `LICENSE` file has been Apache-2.0 since 2.2.x; the in-file header was
  stale).
- README and docs site both pin `@v2.3.0` with matching SRI hashes
  (`sha384-0mXihXV5Gt…`). The docs site previously shipped `@main` without
  SRI; the README previously shipped a stale SRI from a prior build.
- Threat Model simplified: single deployment mode (direct GitHub API).
- `SECURITY.md` scope narrowed to widget + CI/release workflows.
- `CONTRIBUTING.md` rewritten for a JS-only project — no Python tooling.
- `.gitignore` trimmed to JS/OS/IDE entries (Python venv/egg entries removed).

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

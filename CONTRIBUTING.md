# Contributing

Thanks for your interest in contributing. This project is intentionally small:
zero-dependency JS widget, one Python reference server, two CLIs. Keep PRs
focused and the surface area tight.

## Prerequisites

- Python **3.12+** (3.10+ may work for `server.py`, 3.12 is what CI runs)
- [`gh`](https://cli.github.com) authenticated (`gh auth login`) — required by
  the CLIs and `server.py`
- [`ruff`](https://docs.astral.sh/ruff/) for linting Python
- [`shellcheck`](https://www.shellcheck.net/) for the bash CLI

## Running the test suite

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest tests/ -v
```

The suite runs in under 15 seconds and covers:

- Validation logic (`test_input_validation.py`)
- HTTP behaviour of `server.py` (`test_server_http.py`) — rate-limit, CORS,
  auth, malformed payloads, sanitizers, adversarial XSS payloads

## Linting

Before you push, run:

```bash
ruff check .
shellcheck issue-reporter.sh
```

Both are enforced by CI and must pass.

## Commit messages

Conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `ci:`,
`security:`). The first line is ≤ 72 characters. Explain *why* in the body when
the change is non-obvious.

## What we accept

- Bug fixes with a regression test
- New features that keep the zero-dependency, single-file-widget philosophy
- Documentation improvements
- Hardening (security, validation, error handling) with tests

## What we're careful about

- **No new runtime dependencies** in `issue-reporter.js`
- **No new Python packages** in `server.py` (stdlib only)
- **Breaking changes to `IssueReporter.init()`** require a major-version bump
  and a documented migration path

## Security

Do not open public issues for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for the disclosure process.

## Releasing

1. Bump the version in `pyproject.toml` and the README badge.
2. Update `CHANGELOG.md`.
3. Tag `vX.Y.Z` on `main`.
4. Regenerate the SRI hash in every README `<script>` example:
   ```bash
   curl -sL "https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@vX.Y.Z/issue-reporter.js" \
     | openssl dgst -sha384 -binary | openssl base64 -A
   ```
5. Open a PR updating the README script tags to the new tag + hash.

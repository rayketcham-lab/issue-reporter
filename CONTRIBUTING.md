# Contributing

Thanks for your interest in contributing. This project is intentionally small:
a zero-dependency JS widget in a single file. Keep PRs focused and the surface
area tight.

## Prerequisites

- A modern browser to open `docs/index.html` locally and exercise the widget.
- [`gh`](https://cli.github.com) authenticated — only needed if you want to
  file issues against a real repo while testing.

## Testing changes

The widget has no build step. Open `docs/index.html` in a browser, click the
demo button, and walk the wizard. CodeQL runs in CI over `issue-reporter.js`;
no local lint is enforced.

## Commit messages

Conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `ci:`,
`security:`). The first line is ≤ 72 characters. Explain *why* in the body when
the change is non-obvious.

## What we accept

- Bug fixes in the widget
- New features that keep the zero-dependency, single-file-widget philosophy
- Documentation improvements
- Hardening (security, validation, error handling)

## What we're careful about

- **No new runtime dependencies** in `issue-reporter.js`
- **Breaking changes to `IssueReporter.init()`** require a major-version bump
  and a documented migration path

## Security

Do not open public issues for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for the disclosure process.

## Releasing

1. Bump the version in the README badge and `<script>` tag examples.
2. Update `CHANGELOG.md`.
3. Tag `vX.Y.Z` on `main`.
4. Regenerate the SRI hash in every README `<script>` example:
   ```bash
   curl -sL "https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@vX.Y.Z/issue-reporter.js" \
     | openssl dgst -sha384 -binary | openssl base64 -A
   ```
5. Open a PR updating the README script tags to the new tag + hash.

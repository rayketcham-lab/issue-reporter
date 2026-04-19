# Security Policy

## Supported Versions

Security fixes are applied to the latest minor release line. Older tags do not
receive backports.

| Version | Supported |
| ------- | --------- |
| 2.2.x   | Yes       |
| < 2.2   | No        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's [Private Vulnerability Reporting](https://github.com/rayketcham-lab/issue-reporter/security/advisories/new)
to send a private report. You should receive an acknowledgement within 72 hours.

When reporting, include:

- A description of the issue and its impact
- Steps to reproduce (proof-of-concept welcome)
- Affected versions or commit SHAs
- Any known mitigations

## Scope

In scope:

- `issue-reporter.js` (embedded widget)
- `server.py` (reference backend)
- `issue-reporter.sh`, `issue_reporter.py` (CLIs)
- CI/release workflows in `.github/workflows/`

Out of scope:

- Vulnerabilities in consumer applications that embed the widget
- Abuse of a GitHub PAT that the consumer exposed in direct-mode
  (this is a documented tradeoff — see the README "Threat Model" section)
- Rate-limit exhaustion using a legitimately issued token

## Disclosure Policy

Once a fix is available:

1. A patch release is published with a pinned tag.
2. The release notes describe the issue class and credit the reporter
   (unless they request anonymity).
3. If the affected code ships via the jsDelivr CDN, the README `integrity=`
   hashes are rotated to the patched release.
4. A GitHub Security Advisory is published when warranted.

## Safe Harbor

Good-faith security research is welcomed. We will not pursue legal action for
research that:

- Respects user privacy and does not access data beyond what is required to
  demonstrate the issue.
- Does not disrupt service for other users.
- Gives reasonable time (30 days) to resolve before public disclosure.

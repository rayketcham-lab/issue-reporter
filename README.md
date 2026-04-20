# issue-reporter

![Version](https://img.shields.io/badge/version-2.3.0-blue) ![License](https://img.shields.io/badge/license-Apache%202.0-blue) ![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen) ![Size](https://img.shields.io/badge/size-~67kb-lightgrey) ![GitHub Stars](https://img.shields.io/github/stars/rayketcham-lab/issue-reporter?style=social)

Drop a feedback button on any web page. Reports become GitHub issues.

No backend required. No database. No API keys beyond a GitHub token scoped to issues.

## Demo

> [!TIP]
> **Try it live** at [rayketcham-lab.github.io/issue-reporter](https://rayketcham-lab.github.io/issue-reporter/#demo) — click through the wizard, see the exact issue body it would produce. Nothing is filed.

A bug reported through the widget produces this GitHub issue, verbatim:

**Title:** `fix: Checkout submit button does nothing when clicked.`
**Labels:** `bug`

````markdown
## Summary

Checkout submit button does nothing when clicked.

## Context

- **Page:** https://shop.example.com/checkout
- **Page Title:** Checkout — Your Cart
- **Section:** Checkout form
- **Element:** button#submit-order

## Expected Behavior

Clicking Submit should POST the order and redirect to the confirmation page.

## Console Errors

```
[error] Uncaught TypeError: Cannot read properties of null (reading 'submit')
```

## Recent API Calls

```
200 https://shop.example.com/api/cart
```

## Metadata

- **Type:** bug
- **Severity:** high
- **Project:** Example Shop

---
*Reported via [issue-reporter](https://github.com/rayketcham-lab/issue-reporter) on 2026-04-20 14:32 UTC*
````

No screenshot. No GIF. That's the real output — every field above is collected automatically or filled in through three wizard steps.

## Table of Contents

- [Demo](#demo)
- [Features](#features)
- [Quick Start](#quick-start)
  - [Creating the token](#creating-the-token)
  - [Threat Model](#threat-model)
  - [Content Security Policy](#content-security-policy)
  - [Supply-chain pinning](#supply-chain-pinning)
- [GitHub Enterprise & Multi-Flavor Support](#github-enterprise--multi-flavor-support)
- [Widget Options](#widget-options)
  - [Programmatic control](#programmatic-control)
  - [Self-hosting the JS](#self-hosting-the-js)
- [How It Works](#how-it-works)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Features

- Dark theme with backdrop blur
- Multi-step wizard (Type → Details → Review)
- Element inspector (click to capture DOM elements)
- Console error capture (automatic)
- API call capture (automatic)
- Page section detection
- Severity levels (Low / Medium / High / Critical)
- Expected behavior field
- Review step before submitting
- Direct GitHub API — no backend required
- Zero dependencies, single file

> [!TIP]
> Two lines of HTML is all you need — no build step, no framework, no dependencies.

## Quick Start

Add two lines to your page. The widget calls the GitHub API directly.

```html
<script
  src="https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@v2.3.0/issue-reporter.js"
  integrity="sha384-0mXihXV5GtYbZBfbGYg1BaV6HZHSK9BrvXQHDLm0x6Yl9J5x+7BR26wI3MPzCQgX"
  crossorigin="anonymous"></script>
<script>
  IssueReporter.init({
    github: {
      repo: "your-org/your-repo",
      token: "github_pat_xxxx"
    },
    projectName: "My App"
  });
</script>
```

That's it. A floating "Report Issue" button appears. Click it, fill out the form, GitHub issue created.

### Creating the token

1. Go to [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) (fine-grained tokens)
2. **Repository access**: select only the repo you want issues in
3. **Permissions**: Issues → Read and write (nothing else)
4. Copy the token into your `init()` call

This token can *only* create issues on that one repo. It can't read your code, push commits, or access anything else.

> [!WARNING]
> **Token visibility tradeoff:** The widget puts your GitHub token in page source. For internal tools, staging, or personal projects, that's fine — the worst anyone can do is create spam issues you can delete. For public-facing sites, use a dedicated triage repo and accept that anyone can spam issues up to the PAT's hourly budget.

### Threat Model

Read this before you put the widget on a public site.

| Where the token lives | Who can see it | Rate-limit enforcement | Recommended for |
| --------------------- | -------------- | ---------------------- | --------------- |
| Browser (page source) | Anyone who views source, any browser extension, any third-party script on the page (analytics, tag managers, ad SDKs) | None in browser — only GitHub's PAT limit (5000 req/hr) | Intranet, staging, demos, dedicated triage repo |

**If you ship in production:**

- **Scope the token to a dedicated triage repo**, not your production code repo. A leaked PAT that can only file issues to `your-org/feedback-intake` is a much smaller blast radius than one pointing at `your-org/main-app`.
- **Use a fine-grained token** with `Issues: read/write` only. No other permission.
- **Rotate on a schedule** (30 days is a reasonable default) and immediately if you see anomalous issue volume.
- **Accept that any page visitor can spam issues** up to the PAT's hourly budget. GitHub will throttle before your repo fills up, but you will need to delete/close the garbage.
- **Third-party scripts can exfiltrate the token.** If your page loads analytics, tag managers, chat widgets, or ad SDKs, those scripts run in the same origin and can read the widget's config. The widget is *not* safe when you do not fully trust every script on the page.

### Content Security Policy

The widget works with a strict CSP. Minimum directives:

```
connect-src 'self' https://api.github.com;          /* or your GHES host     */
style-src   'self' 'unsafe-inline';                 /* widget injects <style> */
img-src     'self' data:;                           /* for inline icons       */
script-src  'self' https://cdn.jsdelivr.net;        /* drop jsdelivr if you self-host the JS */
```

The widget does not use `eval`, inline event handlers, or `unsafe-eval`. If you self-host `issue-reporter.js` you can drop the jsDelivr origin from `script-src`.

### Supply-chain pinning

All `<script>` examples in this README pin a version tag and include an `integrity="sha384-..."` hash. **Do not replace the tag with `@main` in production** — `@main` auto-updates with every commit and has no integrity guarantee.

To upgrade, bump the tag and regenerate the hash:

```bash
curl -sL "https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@<TAG>/issue-reporter.js" \
  | openssl dgst -sha384 -binary | openssl base64 -A
```

---


## GitHub Enterprise & Multi-Flavor Support

The widget works with any GitHub-compatible instance. Pass `apiUrl` in the `github` config to target on-prem or alternative deployments:

```html
<script
  src="https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@v2.3.0/issue-reporter.js"
  integrity="sha384-0mXihXV5GtYbZBfbGYg1BaV6HZHSK9BrvXQHDLm0x6Yl9J5x+7BR26wI3MPzCQgX"
  crossorigin="anonymous"></script>
<script>
  IssueReporter.init({
    github: {
      repo: "YOUR-ORG/YOUR-REPO",
      token: "github_pat_xxxxx",
      apiUrl: "https://your-ghes-host/api/v3"  // GitHub Enterprise Server (on-prem)
    },
    projectName: "Your App Name"
  });
</script>
```

| Flavor | `apiUrl` value |
|--------|----------------|
| **GitHub.com** (default) | Omit — defaults to `https://api.github.com` |
| **GitHub Enterprise Server** (on-prem) | `https://<hostname>/api/v3` |
| **GitHub Enterprise Cloud** (GHEC) | Omit — same as github.com, org-scoped via token |
| **GitHub AE** | `https://<hostname>/api/v3` |

> [!NOTE]
> On GHES / GitHub AE, generate your personal access token from *that instance's* token settings page, not from github.com. Tokens are not transferable between instances.

**Token notes:**
- Token requirements are the same across all flavors — scope to `repo` (or fine-grained Issues read/write) at minimum
- On GHES / GitHub AE, generate the PAT from *that instance*, not github.com
- Fine-grained tokens are supported on GHES 3.10+ and github.com

---

## Widget Options

```html
<script
  src="https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@v2.3.0/issue-reporter.js"
  integrity="sha384-0mXihXV5GtYbZBfbGYg1BaV6HZHSK9BrvXQHDLm0x6Yl9J5x+7BR26wI3MPzCQgX"
  crossorigin="anonymous"></script>
<script>
  IssueReporter.init({
    github: {
      repo: "owner/repo",
      token: "github_pat_xxxx",
      apiUrl: "https://ghes.example.com/api/v3"  // optional — for GHES/GitHub AE
    },

    // --- Optional ---
    projectName: "My App",
    position: "bottom-right",             // or "bottom-left"
    buttonText: "Report Issue",
    issueTypes: [
      { id: "bug",             label: "Bug Report" },
      { id: "data_issue",      label: "Data Issue" },
      { id: "ui_bug",          label: "UI / Display Bug" },
      { id: "broken_link",     label: "Broken Link" },
      { id: "feature_request", label: "Feature Request" },
      { id: "performance",     label: "Performance" },
      { id: "other",           label: "Other" }
    ]
  });
</script>
```

### Programmatic control

```js
IssueReporter.open();    // Open the modal
IssueReporter.close();   // Close the modal
IssueReporter.destroy(); // Remove the widget entirely
```

### Self-hosting the JS

```bash
curl -O https://raw.githubusercontent.com/rayketcham-lab/issue-reporter/v2.3.0/issue-reporter.js
```

No build step. No dependencies. One file.

---

## How It Works

```
Browser widget ──→ GitHub API directly ──→ GitHub Issues
       or
Browser widget ──→ GitHub Enterprise API (on-prem, via apiUrl) ──→ Issues
```

## Security

See [SECURITY.md](SECURITY.md) for the disclosure policy and [Threat Model](#threat-model) above for the trust model.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit changes.

## License

Apache-2.0

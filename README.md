# issue-reporter

Drop a feedback button on any web page. Reports become GitHub issues.

No backend required. No database. No API keys beyond a GitHub token scoped to issues.

## Quick Start — Pure HTML (no backend)

Add two lines to your page. The widget calls the GitHub API directly.

```html
<script src="https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@main/issue-reporter.js"></script>
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

> **Token visibility tradeoff:** In direct mode the token is visible in your page source. For internal tools or personal projects, that's fine — the worst anyone can do is create spam issues you can delete. For public-facing sites, use **Backend Integration** below so the token never leaves your server.

---

## Backend Integration (recommended for public sites)

Token stays on your server. The widget POSTs JSON to a route on your app, your app runs `gh issue create`. No token in the browser, no extra process.

```html
<script src="https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@main/issue-reporter.js"></script>
<script>
  IssueReporter.init({ endpoint: "/api/report", projectName: "My App" });
</script>
```

Your backend receives:

```json
{
  "type": "bug",
  "severity": "high",
  "description": "The save button doesn't work",
  "context": "Was on the settings page",
  "project_name": "My App",
  "page_url": "https://mysite.com/settings"
}
```

And returns:

```json
{"success": true, "url": "https://github.com/you/repo/issues/42"}
```

The route is ~10 lines in any framework. Pick yours:

<details>
<summary><strong>FastAPI</strong></summary>

```python
import asyncio
from fastapi import FastAPI

app = FastAPI()

@app.post("/api/report")
async def report_issue(body: dict):
    desc = (body.get("description") or "").strip()
    if not desc:
        return {"success": False, "error": "description is required"}

    title = f"{body.get('type', 'bug')}: {desc[:60]}"
    issue_body = f"## Summary\n\n{desc}\n\n- **Severity:** {body.get('severity', 'medium')}"

    proc = await asyncio.create_subprocess_exec(
        "gh", "issue", "create", "--title", title, "--body", issue_body,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    url = stdout.decode().strip() if proc.returncode == 0 else None
    if url:
        return {"success": True, "url": url}
    return {"success": False, "error": "gh issue create failed"}
```
</details>

<details>
<summary><strong>Flask</strong></summary>

```python
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/api/report")
def report_issue():
    data = request.get_json()
    desc = (data.get("description") or "").strip()
    if not desc:
        return jsonify(success=False, error="description is required"), 400

    title = f"{data.get('type', 'bug')}: {desc[:60]}"
    body = f"## Summary\n\n{desc}\n\n- **Severity:** {data.get('severity', 'medium')}"

    result = subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        return jsonify(success=True, url=result.stdout.strip())
    return jsonify(success=False, error="gh issue create failed"), 500
```
</details>

<details>
<summary><strong>Express</strong></summary>

```js
const { execFile } = require("child_process");
const app = require("express")();
app.use(require("express").json());

app.post("/api/report", (req, res) => {
  const desc = (req.body.description || "").trim();
  if (!desc) return res.json({ success: false, error: "description is required" });

  const title = `${req.body.type || "bug"}: ${desc.slice(0, 60)}`;
  const body = `## Summary\n\n${desc}\n\n- **Severity:** ${req.body.severity || "medium"}`;

  execFile("gh", ["issue", "create", "--title", title, "--body", body], (err, stdout) => {
    if (err) return res.json({ success: false, error: "gh issue create failed" });
    res.json({ success: true, url: stdout.trim() });
  });
});
```
</details>

<details>
<summary><strong>Django</strong></summary>

```python
import json, subprocess
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def report_issue(request):
    data = json.loads(request.body)
    desc = (data.get("description") or "").strip()
    if not desc:
        return JsonResponse({"success": False, "error": "description is required"}, status=400)

    title = f"{data.get('type', 'bug')}: {desc[:60]}"
    body = f"## Summary\n\n{desc}\n\n- **Severity:** {data.get('severity', 'medium')}"

    result = subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        return JsonResponse({"success": True, "url": result.stdout.strip()})
    return JsonResponse({"success": False, "error": "gh issue create failed"}, status=500)
```
</details>

Backend mode requires `gh` CLI installed and authenticated on your server (`sudo apt install gh && gh auth login`).

For a more complete backend with rate limiting, CORS, labels, and conventional-commit prefixes, see `server.py` in this repo.

---

## Widget Options

```html
<script>
  IssueReporter.init({
    // --- Pick one mode ---
    github: { repo: "owner/repo", token: "github_pat_xxxx" },  // direct
    // endpoint: "/api/report",                                  // backend

    // --- Optional ---
    projectName: "My App",
    position: "bottom-right",             // or "bottom-left"
    buttonText: "Report Issue",
    issueTypes: [
      { id: "bug", label: "Bug Report" },
      { id: "feature_request", label: "Feature Request" },
      { id: "ui_bug", label: "UI Bug" },
      { id: "performance", label: "Performance" },
      { id: "other", label: "Other" }
    ],
    token: "your-secret-token"            // backend mode only — Bearer header
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
curl -O https://raw.githubusercontent.com/rayketcham-lab/issue-reporter/main/issue-reporter.js
```

No build step. No dependencies. One file.

---

## CLI Usage

Create issues from the terminal — no widget needed.

### Bash

```bash
curl -O https://raw.githubusercontent.com/rayketcham-lab/issue-reporter/main/issue-reporter.sh
chmod +x issue-reporter.sh

./issue-reporter.sh                                    # Interactive
./issue-reporter.sh "The login button doesn't work"    # One-liner
./issue-reporter.sh -t feature -s low "Add dark mode"  # Type + severity
tail -20 error.log | ./issue-reporter.sh -t bug -s high  # Pipe from logs
./issue-reporter.sh --dry-run "Test issue"             # Preview only
```

### Python

```bash
curl -O https://raw.githubusercontent.com/rayketcham-lab/issue-reporter/main/issue_reporter.py

python issue_reporter.py "The save button is broken"
python issue_reporter.py --type feature "Add export button"
python issue_reporter.py --dry-run "Test"
```

```python
# As a library
from issue_reporter import IssueReporter

reporter = IssueReporter(project_name="My App")
url = reporter.report("The save button doesn't work", issue_type="bug")
print(url)  # https://github.com/you/repo/issues/42
```

### pip install

```bash
pip install git+https://github.com/rayketcham-lab/issue-reporter.git
```

CLI requires `gh` CLI installed and authenticated.

---

## How It Works

```
Browser widget ──→ GitHub API directly (no backend)
       or
Browser widget ──→ Your backend route ──→ gh issue create ──→ GitHub Issues
       or
CLI (bash/python) ──→ gh issue create ──→ GitHub Issues
```

## License

MIT

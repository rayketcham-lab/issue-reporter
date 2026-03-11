# issue-reporter

Drop a feedback button on any web page. User reports become structured GitHub issues via `gh` CLI.

No database, no API keys, no third-party services. Just `gh`.

## Prerequisite

Install and authenticate the [GitHub CLI](https://cli.github.com) on whatever machine runs your backend:

```bash
sudo apt install gh          # Ubuntu/Debian
gh auth login                # One time — authenticates with your GitHub account
```

---

## Web Widget (add to any web app)

The widget is a single JS file — no framework, no build step. It renders a floating "Report Issue" button that opens a form. On submit, it POSTs JSON to a route on **your** backend, which runs `gh issue create`.

### 1. Add the script tag

```html
<script src="https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@main/issue-reporter.js"></script>
<script>
  IssueReporter.init({
    endpoint: "/api/report",       // route on YOUR backend (see step 2)
    projectName: "My App"
  });
</script>
```

A floating button appears in the bottom-right corner. Click → fill out form → submit → GitHub issue created.

### 2. Add one route to your backend

The widget POSTs JSON. Your backend receives it and runs `gh issue create`. That's the entire integration — one route.

**POST body from the widget:**
```json
{
  "type": "bug",
  "severity": "high",
  "description": "The save button doesn't work",
  "context": "Was editing a profile",
  "project_name": "My App",
  "page_url": "/settings"
}
```

**Expected response:**
```json
{"success": true, "url": "https://github.com/you/repo/issues/42"}
```

Pick your framework:

<details>
<summary><strong>FastAPI (Python)</strong></summary>

```python
import asyncio
from fastapi import FastAPI

app = FastAPI()

@app.post("/api/report")
async def report_issue(body: dict):
    description = body.get("description", "").strip()
    if not description:
        return {"success": False, "error": "description is required"}

    issue_type = body.get("type", "bug")
    severity = body.get("severity", "medium")
    title = f"{issue_type}: {description[:60]}"
    issue_body = f"## Summary\n\n{description}\n\n- **Severity:** {severity}"

    proc = await asyncio.create_subprocess_exec(
        "gh", "issue", "create", "--title", title, "--body", issue_body,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode == 0:
        return {"success": True, "url": stdout.decode().strip()}
    return {"success": False, "error": "gh issue create failed"}
```
</details>

<details>
<summary><strong>Flask (Python)</strong></summary>

```python
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/api/report")
def report_issue():
    data = request.get_json()
    description = (data.get("description") or "").strip()
    if not description:
        return jsonify(success=False, error="description is required"), 400

    issue_type = data.get("type", "bug")
    severity = data.get("severity", "medium")
    title = f"{issue_type}: {description[:60]}"
    body = f"## Summary\n\n{description}\n\n- **Severity:** {severity}"

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
<summary><strong>Express (Node.js)</strong></summary>

```js
const { execFile } = require("child_process");
const express = require("express");
const app = express();
app.use(express.json());

app.post("/api/report", (req, res) => {
  const { description, type = "bug", severity = "medium" } = req.body;
  if (!description) return res.json({ success: false, error: "description is required" });

  const title = `${type}: ${description.slice(0, 60)}`;
  const body = `## Summary\n\n${description}\n\n- **Severity:** ${severity}`;

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
# views.py
import json, subprocess
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def report_issue(request):
    data = json.loads(request.body)
    description = (data.get("description") or "").strip()
    if not description:
        return JsonResponse({"success": False, "error": "description is required"}, status=400)

    issue_type = data.get("type", "bug")
    severity = data.get("severity", "medium")
    title = f"{issue_type}: {description[:60]}"
    body = f"## Summary\n\n{description}\n\n- **Severity:** {severity}"

    result = subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        return JsonResponse({"success": True, "url": result.stdout.strip()})
    return JsonResponse({"success": False, "error": "gh issue create failed"}, status=500)

# urls.py
urlpatterns = [path("api/report", views.report_issue)]
```
</details>

That's it. The core logic is always the same: receive JSON, run `gh issue create`, return the URL.

The examples above are minimal. See `server.py` in this repo for a more complete implementation with rate limiting, CORS, label mapping, and conventional-commit title prefixes.

### Widget options

```html
<script>
  IssueReporter.init({
    endpoint: "/api/report",              // required — your backend route
    projectName: "My App",                // optional — included in issue metadata
    position: "bottom-right",             // "bottom-right" or "bottom-left"
    buttonText: "Report Issue",
    issueTypes: [
      { id: "bug", label: "Bug Report" },
      { id: "feature_request", label: "Feature Request" },
      { id: "ui_bug", label: "UI Bug" },
      { id: "performance", label: "Performance" },
      { id: "other", label: "Other" }
    ],
    token: "your-secret-token"            // sent as Authorization: Bearer header
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

## Standalone Server (no existing backend)

If you're running a static site or don't have a backend, `server.py` is a self-contained bridge between the widget and `gh`. Stdlib only — no pip install needed.

```bash
python server.py --repo /path/to/your-project --port 8787
```

| Flag | Default | Description |
|------|---------|-------------|
| `--repo` | `.` | Git repo directory (where `gh` creates issues) |
| `--port` | `8787` | Server port |
| `--allowed-origins` | `*` | CORS origins (lock to your domain in production) |
| `--token` | *(none)* | Optional Bearer token clients must send |

Then point the widget at it:

```html
<script>
  IssueReporter.init({
    endpoint: "https://your-server.com:8787/api/report"
  });
</script>
```

---

## CLI Usage

Create issues directly from the terminal — no web widget needed.

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

---

## Integration Examples

### CI — auto-report failures

```yaml
- name: Report failures
  if: failure()
  run: echo "CI failed on ${{ github.ref }}" | ./issue-reporter.sh -t bug -s high
```

### Python test suite

```python
from issue_reporter import IssueReporter

reporter = IssueReporter.from_config("issue-reporter.json")

def pytest_sessionfinish(session, exitstatus):
    if exitstatus != 0:
        reporter.report(f"{session.testsfailed} tests failed", issue_type="bug", severity="high")
```

### Git hook

```bash
# .git/hooks/post-commit
#!/bin/bash
read -rp "Report an issue? [y/N]: " answer
[[ "${answer,,}" == "y" ]] && /path/to/issue-reporter.sh
```

---

## Configuration Files

Optional config files customize issue types and labels.

**JSON** — copy `issue-reporter.example.json` to `issue-reporter.json`:

```json
{
  "project_name": "My App",
  "issue_types": [
    {"id": "bug", "label": "Bug", "description": "Something broken"},
    {"id": "feature_request", "label": "Feature", "description": "New idea"}
  ],
  "label_map": {
    "bug": ["bug"],
    "feature_request": ["enhancement"]
  }
}
```

**Bash** — copy `issue-reporter.example.conf` to `issue-reporter.conf`.

## How It Works

```
Browser widget / CLI / CI
         |
         v
    Your backend         (or standalone server.py)
         |
         v
    gh issue create
         |
         v
    GitHub Issues
```

The only external dependency is `gh` CLI (free, uses your existing GitHub auth). No database, no API keys, no third-party accounts.

## License

MIT

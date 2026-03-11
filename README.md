# issue-reporter

Drop a feedback button on any web page. User reports become structured GitHub issues.

## Quick Start — Add to Your Web Page

**1. Add the widget to your HTML:**

```html
<script src="https://cdn.jsdelivr.net/gh/rayketcham-lab/issue-reporter@main/issue-reporter.js"></script>
<script>
  IssueReporter.init({
    endpoint: "https://your-server.com/api/report",
    projectName: "My App"
  });
</script>
```

A floating "Report Issue" button appears in the bottom-right corner. Click it, fill out the form, done.

**2. Start the backend server** (receives reports, creates GitHub issues):

```bash
python server.py --repo /path/to/your-project --port 8787
```

That's it. Reports from the widget become GitHub issues in your repo.

## Server Setup

The server is a single Python file (stdlib only, no dependencies) that creates GitHub issues via `gh` CLI.

### Requirements

- Python 3.10+
- [GitHub CLI](https://cli.github.com) (free, authenticated with your account)

```bash
# Install gh if you don't have it
sudo apt install gh          # Ubuntu/Debian
gh auth login                # Authenticate (one time)
```

### Run the server

```bash
# Basic
python server.py --repo /path/to/your-project

# All options
python server.py \
  --repo /path/to/your-project \
  --port 8787 \
  --allowed-origins "https://mysite.com" \
  --token "your-secret-token"
```

| Flag | Default | Description |
|------|---------|-------------|
| `--repo` | `.` | Git repo directory (where `gh` creates issues) |
| `--port` | `8787` | Server port |
| `--allowed-origins` | `*` | CORS origins (use specific domain in production) |
| `--token` | *(none)* | Optional auth token — clients must send `Authorization: Bearer <token>` |

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/report` | Create an issue. Body: `{type, severity, description, context, project_name}` |
| `GET` | `/health` | Health check |

### Response format

```json
{"success": true, "url": "https://github.com/you/repo/issues/42"}
```

```json
{"success": false, "error": "description is required"}
```

Rate limited to 5 requests per minute per IP.

## Widget Configuration

### Minimal

```html
<script src="issue-reporter.js"></script>
<script>
  IssueReporter.init({
    endpoint: "https://your-server.com/api/report"
  });
</script>
```

### All options

```html
<script>
  IssueReporter.init({
    endpoint: "https://your-server.com/api/report",
    projectName: "My App",
    position: "bottom-right",      // "bottom-right" or "bottom-left"
    buttonText: "Report Issue",
    issueTypes: [
      { id: "bug", label: "Bug Report" },
      { id: "feature_request", label: "Feature Request" },
      { id: "ui_bug", label: "UI Bug" },
      { id: "performance", label: "Performance" },
      { id: "other", label: "Other" }
    ],
    token: "your-secret-token"     // sent as Authorization: Bearer header
  });
</script>
```

### Programmatic control

```js
IssueReporter.open();    // Open the modal
IssueReporter.close();   // Close the modal
IssueReporter.destroy(); // Remove the widget entirely
```

### Self-hosting the JS file

Download `issue-reporter.js` and serve it yourself:

```bash
curl -O https://raw.githubusercontent.com/rayketcham-lab/issue-reporter/main/issue-reporter.js
```

No build step. No dependencies. One file.

## Alternative: CLI Usage

If you don't need the web widget, the CLI tools create issues directly from the terminal.

### Bash

```bash
curl -O https://raw.githubusercontent.com/rayketcham-lab/issue-reporter/main/issue-reporter.sh
chmod +x issue-reporter.sh

# Interactive wizard
./issue-reporter.sh

# One-liner
./issue-reporter.sh "The login button doesn't work"

# Specify type + severity
./issue-reporter.sh -t feature -s low "Add dark mode"

# Pipe from logs
tail -20 error.log | ./issue-reporter.sh -t bug -s high

# Preview without creating
./issue-reporter.sh --dry-run "Test issue"
```

### Python

```bash
curl -O https://raw.githubusercontent.com/rayketcham-lab/issue-reporter/main/issue_reporter.py

# CLI
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

## Integration Examples

### Git hook

```bash
# .git/hooks/post-commit
#!/bin/bash
read -rp "Report an issue? [y/N]: " answer
[[ "${answer,,}" == "y" ]] && /path/to/issue-reporter.sh
```

### CI auto-report failures

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

## How It Works

```
Web page / CLI / CI
       |
       v
  issue-reporter  ──POST JSON──>  server.py  ──gh issue create──>  GitHub Issues
       |                                                                  |
       v                                                                  v
  "Issue created!"                                          github.com/you/repo/issues/42
```

1. User fills out the feedback form (or runs the CLI)
2. Report is structured into a proper issue with title, labels, and sections
3. `gh` CLI creates the issue in your repo
4. User gets back the issue URL

No database, no third-party accounts beyond GitHub. Just files.

## License

MIT

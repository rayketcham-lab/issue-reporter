# issue-reporter

Turn plain feedback into structured GitHub issues. One file, one dependency.

## Requirements

**Just one thing:** [GitHub CLI](https://cli.github.com) (free)

```bash
brew install gh       # macOS
sudo apt install gh   # Ubuntu/Debian
gh auth login         # authenticate (one time)
```

That's it. No API keys, no accounts, no payment. Issues get created directly in your GitHub repo.

## Install

**Option A — Copy one file** (recommended):

```bash
# Python version
curl -o issue-reporter.py https://raw.githubusercontent.com/rayketcham/issue-reporter/main/issue_reporter.py

# OR Bash version (zero Python needed)
curl -o issue-reporter.sh https://raw.githubusercontent.com/rayketcham/issue-reporter/main/issue-reporter.sh
chmod +x issue-reporter.sh
```

**Option B — pip install:**

```bash
pip install git+https://github.com/rayketcham/issue-reporter.git
# or from local clone
pip install /path/to/issue-reporter/
```

## Usage

### Bash

```bash
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

### Python (CLI)

```bash
python issue_reporter.py "The save button is broken"
python issue_reporter.py --type feature "Add export button"
python issue_reporter.py --dry-run "Test"
```

### Python (library)

```python
from issue_reporter import IssueReporter

reporter = IssueReporter(project_name="My App")
url = reporter.report("The save button doesn't work", issue_type="bug")
print(url)  # https://github.com/you/repo/issues/42
```

## Optional: AI formatting (free with Ollama)

Without AI, issues get clean deterministic formatting. With AI, you get smarter titles and better-structured bodies. **Both options below are free:**

### Ollama (local, free, private)

```bash
# Install Ollama (one time)
brew install ollama         # or curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3          # download a model (~4GB)

# Use it
./issue-reporter.sh --ollama llama3 "Button doesn't save"
python issue_reporter.py --ollama llama3 "Button doesn't save"

# Or set it as default
export OLLAMA_MODEL=llama3
```

### Anthropic Claude (paid API, best quality)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Now issue-reporter auto-uses Claude for formatting
```

**Priority order:** Ollama (free) → Anthropic (paid) → fallback (no AI). It always works.

## Configuration

Optional. Copy `issue-reporter.example.json` → `issue-reporter.json`:

```json
{
  "project_name": "My App",
  "project_description": "A web app for widgets",
  "ollama_model": "llama3",
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

For bash, copy `issue-reporter.example.conf` → `issue-reporter.conf`.

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

### Web app (any framework)

```python
from issue_reporter import IssueReporter

reporter = IssueReporter.from_config("issue-reporter.json")

# In your feedback endpoint:
def handle_feedback(description: str, issue_type: str = "bug"):
    url = reporter.report(description, issue_type=issue_type)
    return {"issue_url": url}
```

## How it works

```
User feedback → [Ollama/Claude/fallback] → Structured issue → gh issue create → GitHub
```

1. You describe the problem in plain text
2. (Optional) AI formats it into a proper issue with title, labels, sections
3. `gh` CLI creates the issue in your repo
4. You get back the issue URL

No database, no server, no accounts beyond GitHub. One file does everything.

## License

MIT

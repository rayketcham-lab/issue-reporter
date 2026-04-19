#!/usr/bin/env bash
set -euo pipefail

# issue-reporter.sh — Zero-dependency GitHub issue reporter (just needs gh CLI)
#
# Usage:
#   ./issue-reporter.sh                              # Interactive mode
#   ./issue-reporter.sh "Login page is broken"       # Quick mode (defaults to bug)
#   ./issue-reporter.sh -t feature "Add dark mode"   # Specify type
#   echo "Error desc" | ./issue-reporter.sh -t bug   # Pipe mode
#
# Config: Place issue-reporter.conf in the same directory to customize:
#   PROJECT_NAME="My App"
#   REPO_DIR="/path/to/repo"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="."
PROJECT_NAME=""
ISSUE_TYPE="bug"
SEVERITY="medium"
DRY_RUN=false

# Load config if present
CONF_FILE="${SCRIPT_DIR}/issue-reporter.conf"
if [[ -f "$CONF_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$CONF_FILE"
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

die() { echo "Error: $*" >&2; exit 1; }

check_deps() {
    command -v gh &>/dev/null || die "'gh' CLI not found. Install from https://cli.github.com"
    gh auth status &>/dev/null 2>&1 || die "'gh' is not authenticated. Run: gh auth login"
}

type_prefix() {
    case "$1" in
        bug|ui_bug)       echo "fix" ;;
        feature|feature_request) echo "feat" ;;
        data|data_issue)  echo "data" ;;
        performance|perf) echo "perf" ;;
        *)                echo "issue" ;;
    esac
}

labels_for_type() {
    case "$1" in
        bug)              echo "bug" ;;
        feature|feature_request) echo "enhancement" ;;
        data|data_issue)  echo "bug,data" ;;
        ui_bug)           echo "bug,ui" ;;
        performance|perf) echo "performance" ;;
        *)                echo "bug" ;;
    esac
}

# ---------------------------------------------------------------------------
# Issue structuring
# ---------------------------------------------------------------------------

structure_issue() {
    local description="$1"
    local issue_type="$2"
    local severity="$3"

    local prefix
    prefix=$(type_prefix "$issue_type")

    local title_text="${description:0:60}"
    title_text="${title_text%%$'\n'*}"
    if [[ ${#description} -gt 60 ]]; then
        title_text="${title_text% *}..."
    fi

    _TITLE="${prefix}: ${title_text}"
    _BODY="## Summary

${description}

## Metadata

- **Type:** ${issue_type}
- **Severity:** ${severity}"

    if [[ -n "$PROJECT_NAME" ]]; then
        _BODY="${_BODY}
- **Project:** ${PROJECT_NAME}"
    fi

    _LABELS=$(labels_for_type "$issue_type")
    if [[ "$severity" == "critical" ]]; then
        _LABELS="${_LABELS},critical"
    fi
}

# ---------------------------------------------------------------------------
# Create GitHub issue
# ---------------------------------------------------------------------------

create_issue() {
    local title="$1"
    local body="$2"
    local labels="$3"

    local timestamp
    timestamp=$(date -u '+%Y-%m-%d %H:%M UTC')
    body="${body}

---
*Reported via issue-reporter on ${timestamp}*"

    local -a cmd=(gh issue create --title "$title" --body "$body")

    IFS=',' read -ra label_arr <<< "$labels"
    for label in "${label_arr[@]}"; do
        label=$(echo "$label" | xargs)  # trim whitespace
        [[ -n "$label" ]] && cmd+=(--label "$label")
    done

    local url
    if url=$("${cmd[@]}" 2>/dev/null); then
        echo "$url"
        return 0
    fi

    # Retry without labels
    url=$(gh issue create --title "$title" --body "$body" 2>/dev/null) || return 1
    echo "$url"
}

# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

interactive() {
    echo ""
    echo "=== Issue Reporter ==="
    echo ""
    echo "Issue type:"
    echo "  1. Bug Report"
    echo "  2. Feature Request"
    echo "  3. Data Issue"
    echo "  4. UI Bug"
    echo "  5. Performance"
    echo "  6. Other"

    local choice
    read -rp "Select type [1-6]: " choice
    case "$choice" in
        1) ISSUE_TYPE="bug" ;;
        2) ISSUE_TYPE="feature_request" ;;
        3) ISSUE_TYPE="data_issue" ;;
        4) ISSUE_TYPE="ui_bug" ;;
        5) ISSUE_TYPE="performance" ;;
        6) ISSUE_TYPE="other" ;;
        *) echo "Invalid, defaulting to bug"; ISSUE_TYPE="bug" ;;
    esac

    read -rp "Severity [low/medium/high/critical, default=medium]: " SEVERITY
    SEVERITY="${SEVERITY:-medium}"

    echo "Describe the issue (Ctrl-D when done):"
    local description
    description=$(cat)

    if [[ -z "$description" ]]; then
        die "No description provided"
    fi

    read -rp "Create issue? [Y/n]: " confirm
    if [[ "${confirm,,}" == "n" ]]; then
        echo "Cancelled."
        exit 0
    fi

    do_report "$description"
}

# ---------------------------------------------------------------------------
# Main report flow
# ---------------------------------------------------------------------------

do_report() {
    local description="$1"

    structure_issue "$description" "$ISSUE_TYPE" "$SEVERITY"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "Title: ${_TITLE}"
        echo "Labels: ${_LABELS}"
        echo ""
        echo "$_BODY"
        return 0
    fi

    local url
    if url=$(create_issue "$_TITLE" "$_BODY" "$_LABELS"); then
        echo "Created issue: ${url}"
    else
        echo "Failed to create issue" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

usage() {
    cat <<USAGE
Usage: $(basename "$0") [options] [description]

GitHub issue reporter. Creates structured issues from plain feedback.

Options:
  -t, --type TYPE       Issue type: bug, feature, data, ui_bug, perf, other (default: bug)
  -s, --severity SEV    Severity: low, medium, high, critical (default: medium)
  -r, --repo DIR        Repository directory (default: .)
  -n, --dry-run         Show what would be created without creating
  -h, --help            Show this help

Examples:
  $(basename "$0")                                   # Interactive mode
  $(basename "$0") "Login button is broken"          # Quick bug report
  $(basename "$0") -t feature "Add dark mode"        # Feature request
  echo "Error details" | $(basename "$0") -t bug     # Pipe mode
USAGE
    exit 0
}

DESCRIPTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--type) ISSUE_TYPE="$2"; shift 2 ;;
        -s|--severity) SEVERITY="$2"; shift 2 ;;
        -r|--repo) REPO_DIR="$2"; shift 2 ;;
        -n|--dry-run) DRY_RUN=true; shift ;;
        -h|--help) usage ;;
        -*) die "Unknown option: $1" ;;
        *) DESCRIPTION="$1"; shift ;;
    esac
done

# Main
check_deps

if [[ "$REPO_DIR" != "." ]]; then
    cd "$REPO_DIR" || die "Cannot cd to REPO_DIR: $REPO_DIR"
fi

if [[ -n "$DESCRIPTION" ]]; then
    do_report "$DESCRIPTION"
elif [[ ! -t 0 ]]; then
    # Pipe mode
    DESCRIPTION=$(cat)
    [[ -z "$DESCRIPTION" ]] && die "Empty input"
    do_report "$DESCRIPTION"
else
    interactive
fi

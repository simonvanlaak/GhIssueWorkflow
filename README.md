# GhIssueWorkflow

Standalone multi-repo GitHub issue stage-label workflow automation.

## Features

- Ensure required `stage:*` labels exist.
- Deterministic issue selection priority:
  1. `stage:in-progress`
  2. `stage:backlog`
  3. `stage:ready-to-implement` (only when last label event was by an authorized owner)
- Single-select stage transitions.
- Remove `stage:*` labels from **closed** issues.
- Structured JSON logs to stdout.
- `--dry-run` support for safe previews.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Config

YAML or JSON:

```yaml
repos:
  - name: simonvanlaak/CyberneticAgents
    owner_logins: [simonvanlaak]
  - name: simonvanlaak/AnotherRepo
    owner_logins: [simonvanlaak]
```

## CLI

```bash
gh-issue-workflow --config config.yaml tick
gh-issue-workflow --config config.yaml ensure-labels
gh-issue-workflow --config config.yaml cleanup-closed
gh-issue-workflow --config config.yaml pick-next
gh-issue-workflow --config config.yaml set-status --repo owner/repo --issue 123 --status stage:in-progress
gh-issue-workflow --config config.yaml comment --repo owner/repo --issue 123 --body "When answered, set stage:ready-to-implement"
```

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest
```

#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from gh_issue_workflow.autopilot import build_cron_job

if __name__ == "__main__":
    print(
        json.dumps(
            build_cron_job(
                repo_path="/root/.openclaw/workspace/GhIssueWorkflow",
                repo_url="https://github.com/simonvanlaak/GhIssueWorkflow",
            ),
            indent=2,
        )
    )

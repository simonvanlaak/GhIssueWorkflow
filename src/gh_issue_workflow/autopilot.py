from __future__ import annotations


def build_worker_message(*, repo_path: str, repo_url: str) -> str:
    """Build the OpenClaw worker prompt for one orchestration tick."""
    return (
        "You are the GhIssueWorkflow autopilot (stage orchestration mode).\n\n"
        f"Repo: {repo_path} (origin: {repo_url})\n"
        "Source of truth: GitHub issue stage labels.\n\n"
        "Stages:\n"
        "- stage:backlog (parked)\n"
        "- stage:queued (triage queue)\n"
        "- stage:needs-clarification\n"
        "- stage:ready-to-implement (authorized)\n"
        "- stage:in-progress\n"
        "- stage:in-review\n"
        "- stage:blocked\n\n"
        "Algorithm (single run, then stop):\n"
        f"1) `cd {repo_path}` and `git pull --ff-only`.\n"
        "2) If any open issues are `stage:in-progress`, pick the oldest and continue it.\n"
        "3) Else, if any open issues are `stage:ready-to-implement`, pick the oldest.\n"
        "4) Else, if any open issues are `stage:queued`, pick the oldest and move it to `stage:needs-clarification` with one concise question comment.\n"
        "5) stage/label orchestration only: do not implement code changes in this repo.\n"
        "6) Run `bash scripts/quality_gate.sh` when code changed by a human before moving any issue to `stage:in-review`.\n"
        "7) Keep noise low: comment only when status changes or clarification is needed.\n\n"
        "Permissions/safety:\n"
        "- No PRs; commit directly to main if a manual fix is required.\n"
        "- Prefer GitHub REST APIs; avoid /search endpoints.\n"
        "- Low-noise: do not message Simon unless blocked.\n\n"
        "If blocked (missing info, API perms, etc.):\n"
        "- Move to `stage:blocked` and ask one concise question, then stop.\n\n"
        "If no actionable issues: exit quietly."
    )


def build_cron_job(*, repo_path: str, repo_url: str) -> dict[str, object]:
    """Return a cron job payload for the GhIssueWorkflow orchestration worker."""
    return {
        "name": "Autopilot: GhIssueWorkflow implementation worker (10m)",
        "schedule": {"kind": "every", "everyMs": 600000},
        "sessionTarget": "isolated",
        "payload": {
            "kind": "agentTurn",
            "timeoutSeconds": 3600,
            "message": build_worker_message(repo_path=repo_path, repo_url=repo_url),
        },
        "delivery": {"mode": "none"},
        "enabled": True,
    }

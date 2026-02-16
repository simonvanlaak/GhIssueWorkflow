from gh_issue_workflow.autopilot import build_cron_job, build_worker_message


def test_build_worker_message_is_stage_orchestration_only() -> None:
    message = build_worker_message(
        repo_path="/root/.openclaw/workspace/GhIssueWorkflow",
        repo_url="https://github.com/simonvanlaak/GhIssueWorkflow",
    )

    assert "stage/label orchestration only" in message
    assert "If no actionable issues: exit quietly." in message
    assert "Prefer GitHub REST APIs; avoid /search endpoints." in message


def test_build_cron_job_defaults_to_10_minute_schedule() -> None:
    job = build_cron_job(
        repo_path="/root/.openclaw/workspace/GhIssueWorkflow",
        repo_url="https://github.com/simonvanlaak/GhIssueWorkflow",
    )

    assert job["name"] == "Autopilot: GhIssueWorkflow implementation worker (10m)"
    assert job["sessionTarget"] == "isolated"
    assert job["schedule"] == {"kind": "every", "everyMs": 600000}
    assert job["payload"]["kind"] == "agentTurn"
    assert "stage/label orchestration only" in job["payload"]["message"]

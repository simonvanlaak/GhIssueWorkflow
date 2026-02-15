from gh_issue_workflow.stages import (
    STAGE_BACKLOG,
    STAGE_IN_PROGRESS,
    STAGE_READY_TO_IMPLEMENT,
    apply_stage_label,
    pick_next_issue,
)


def test_apply_stage_label_single_select() -> None:
    labels = ["bug", STAGE_BACKLOG, "priority:high"]
    out = apply_stage_label(labels, STAGE_IN_PROGRESS)
    assert out == {"bug", "priority:high", STAGE_IN_PROGRESS}


def test_pick_next_prioritizes_in_progress_then_backlog_then_ready() -> None:
    issues = [
        {
            "number": 3,
            "created_at": "2026-02-03T00:00:00Z",
            "labels": [STAGE_READY_TO_IMPLEMENT],
        },
        {
            "number": 2,
            "created_at": "2026-02-02T00:00:00Z",
            "labels": [STAGE_BACKLOG],
        },
        {
            "number": 1,
            "created_at": "2026-02-01T00:00:00Z",
            "labels": [STAGE_IN_PROGRESS],
        },
    ]

    pick = pick_next_issue(issues, authorized_ready_issue_numbers={3})
    assert pick is not None
    assert pick.number == 1
    assert pick.picked_from_stage == STAGE_IN_PROGRESS


def test_pick_next_ignores_unauthorized_ready_issue() -> None:
    issues = [
        {
            "number": 5,
            "created_at": "2026-02-05T00:00:00Z",
            "labels": [STAGE_READY_TO_IMPLEMENT],
        }
    ]

    assert pick_next_issue(issues, authorized_ready_issue_numbers=set()) is None

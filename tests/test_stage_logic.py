from gh_issue_workflow.stages import (
    KNOWN_STAGE_LABELS,
    STAGE_BACKLOG,
    STAGE_IN_PROGRESS,
    STAGE_QUEUED,
    STAGE_READY_TO_IMPLEMENT,
    apply_stage_label,
    pick_next_issue,
)


def test_apply_stage_label_single_select() -> None:
    labels = ["bug", STAGE_BACKLOG, "priority:high"]
    out = apply_stage_label(labels, STAGE_IN_PROGRESS)
    assert out == {"bug", "priority:high", STAGE_IN_PROGRESS}


def test_pick_next_prioritizes_in_progress_then_queued_then_ready() -> None:
    issues = [
        {
            "number": 4,
            "created_at": "2026-02-04T00:00:00Z",
            "labels": [STAGE_READY_TO_IMPLEMENT],
        },
        {
            "number": 3,
            "created_at": "2026-02-03T00:00:00Z",
            "labels": [STAGE_QUEUED],
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

    pick = pick_next_issue(issues, authorized_ready_issue_numbers={4})
    assert pick is not None
    assert pick.number == 1
    assert pick.picked_from_stage == STAGE_IN_PROGRESS


def test_pick_next_skips_backlog_when_queue_is_empty() -> None:
    issues = [
        {
            "number": 7,
            "created_at": "2026-02-07T00:00:00Z",
            "labels": [STAGE_BACKLOG],
        },
        {
            "number": 5,
            "created_at": "2026-02-05T00:00:00Z",
            "labels": [STAGE_READY_TO_IMPLEMENT],
        },
    ]

    pick = pick_next_issue(issues, authorized_ready_issue_numbers={5})
    assert pick is not None
    assert pick.number == 5
    assert pick.picked_from_stage == STAGE_READY_TO_IMPLEMENT


def test_known_stage_labels_include_queued() -> None:
    assert STAGE_QUEUED in KNOWN_STAGE_LABELS


def test_pick_next_ignores_unauthorized_ready_issue() -> None:
    issues = [
        {
            "number": 5,
            "created_at": "2026-02-05T00:00:00Z",
            "labels": [STAGE_READY_TO_IMPLEMENT],
        }
    ]

    assert pick_next_issue(issues, authorized_ready_issue_numbers=set()) is None

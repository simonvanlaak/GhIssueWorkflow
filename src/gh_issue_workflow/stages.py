from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

STAGE_LABEL_PREFIX = "stage:"

STAGE_BACKLOG = "stage:backlog"
STAGE_QUEUED = "stage:queued"
STAGE_NEEDS_CLARIFICATION = "stage:needs-clarification"
STAGE_READY_TO_IMPLEMENT = "stage:ready-to-implement"
STAGE_IN_PROGRESS = "stage:in-progress"
STAGE_IN_REVIEW = "stage:in-review"
STAGE_BLOCKED = "stage:blocked"

KNOWN_STAGE_LABELS = {
    STAGE_BACKLOG,
    STAGE_QUEUED,
    STAGE_NEEDS_CLARIFICATION,
    STAGE_READY_TO_IMPLEMENT,
    STAGE_IN_PROGRESS,
    STAGE_IN_REVIEW,
    STAGE_BLOCKED,
}


@dataclass(frozen=True)
class PickedIssue:
    number: int
    picked_from_stage: str


def apply_stage_label(existing_labels: Iterable[str], new_stage_label: str) -> set[str]:
    """Return labels with exactly one stage:* value."""
    if new_stage_label not in KNOWN_STAGE_LABELS:
        raise ValueError(f"Unknown stage label: {new_stage_label}")

    kept = {
        label for label in existing_labels if not label.startswith(STAGE_LABEL_PREFIX)
    }
    kept.add(new_stage_label)
    return kept


def pick_next_issue(
    issues: list[dict[str, object]],
    *,
    authorized_ready_issue_numbers: set[int],
) -> PickedIssue | None:
    """Pick next issue deterministically by priority + oldest creation time."""

    def sorted_oldest(items: list[dict[str, object]]) -> list[dict[str, object]]:
        return sorted(items, key=lambda i: str(i.get("created_at", "")))

    in_progress = []
    queued = []
    ready = []

    for issue in issues:
        labels = set(issue.get("labels", []))
        if STAGE_IN_PROGRESS in labels:
            in_progress.append(issue)
            continue
        if STAGE_QUEUED in labels:
            queued.append(issue)
            continue
        if (
            STAGE_READY_TO_IMPLEMENT in labels
            and int(issue["number"]) in authorized_ready_issue_numbers
        ):
            ready.append(issue)

    if in_progress:
        first = sorted_oldest(in_progress)[0]
        return PickedIssue(
            number=int(first["number"]), picked_from_stage=STAGE_IN_PROGRESS
        )
    if queued:
        first = sorted_oldest(queued)[0]
        return PickedIssue(number=int(first["number"]), picked_from_stage=STAGE_QUEUED)
    if ready:
        first = sorted_oldest(ready)[0]
        return PickedIssue(
            number=int(first["number"]), picked_from_stage=STAGE_READY_TO_IMPLEMENT
        )

    return None

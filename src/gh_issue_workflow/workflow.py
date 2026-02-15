from __future__ import annotations

from dataclasses import asdict
from typing import Any

from gh_issue_workflow.config import RepoConfig
from gh_issue_workflow.gh_client import GhClient
from gh_issue_workflow.stages import (
    KNOWN_STAGE_LABELS,
    STAGE_BACKLOG,
    STAGE_IN_PROGRESS,
    STAGE_NEEDS_CLARIFICATION,
    STAGE_READY_TO_IMPLEMENT,
    apply_stage_label,
    pick_next_issue,
)

STAGE_COLORS = {
    "stage:backlog": "cfd3d7",
    "stage:needs-clarification": "fbca04",
    "stage:ready-to-implement": "0e8a16",
    "stage:in-progress": "1d76db",
    "stage:in-review": "5319e7",
    "stage:blocked": "d93f0b",
}


class Workflow:
    def __init__(self, client: GhClient) -> None:
        self.client = client

    def ensure_stage_labels(self, repo: str) -> None:
        owner, repo_name = repo.split("/", 1)
        labels = self.client.api("GET", f"repos/{owner}/{repo_name}/labels", fields={"per_page": 100})
        existing = {row["name"] for row in labels}

        for label in sorted(KNOWN_STAGE_LABELS):
            if label in existing:
                continue
            self.client.api(
                "POST",
                f"repos/{owner}/{repo_name}/labels",
                fields={
                    "name": label,
                    "color": STAGE_COLORS[label],
                    "description": "automation stage label",
                },
            )

    def cleanup_closed_issue_stage_labels(self, repo: str) -> int:
        cleaned = 0
        for stage_label in sorted(KNOWN_STAGE_LABELS):
            q = f'repo:{repo} is:issue is:closed label:"{stage_label}"'
            result = self.client.api("GET", "search/issues", fields={"q": q, "per_page": 100})
            for issue in result.get("items", []):
                self.set_status(repo, int(issue["number"]), None)
                cleaned += 1
        return cleaned

    def list_open_issues(self, repo: str) -> list[dict[str, Any]]:
        q = f"repo:{repo} is:issue is:open"
        data = self.client.api("GET", "search/issues", fields={"q": q, "per_page": 100})
        out: list[dict[str, Any]] = []
        for issue in data.get("items", []):
            out.append(
                {
                    "number": int(issue["number"]),
                    "created_at": issue["created_at"],
                    "labels": [lab["name"] for lab in issue.get("labels", [])],
                }
            )
        return out

    def is_ready_authorized(self, repo: str, issue_number: int, owner_logins: list[str]) -> bool:
        owner, repo_name = repo.split("/", 1)
        events = self.client.api(
            "GET",
            f"repos/{owner}/{repo_name}/issues/{issue_number}/events",
            fields={"per_page": 100},
        )
        for event in reversed(events):
            if event.get("event") != "labeled":
                continue
            label = (event.get("label") or {}).get("name")
            if label != STAGE_READY_TO_IMPLEMENT:
                continue
            actor = (event.get("actor") or {}).get("login")
            return actor in owner_logins
        return False

    def pick_next(self, repo_cfg: RepoConfig) -> dict[str, Any] | None:
        issues = self.list_open_issues(repo_cfg.name)
        authorized_ready = {
            int(i["number"])
            for i in issues
            if STAGE_READY_TO_IMPLEMENT in set(i.get("labels", []))
            and self.is_ready_authorized(repo_cfg.name, int(i["number"]), repo_cfg.owner_logins)
        }
        pick = pick_next_issue(issues, authorized_ready_issue_numbers=authorized_ready)
        if pick is None:
            return None
        return asdict(pick)

    def set_status(self, repo: str, issue_number: int, new_status: str | None) -> None:
        owner, repo_name = repo.split("/", 1)
        issue = self.client.api("GET", f"repos/{owner}/{repo_name}/issues/{issue_number}")
        existing = [label["name"] for label in issue.get("labels", [])]
        if new_status is None:
            target_labels = sorted([label for label in existing if not label.startswith("stage:")])
        else:
            target_labels = sorted(apply_stage_label(existing, new_status))
        self.client.api_patch_json(f"repos/{owner}/{repo_name}/issues/{issue_number}", {"labels": target_labels})

    def post_comment(self, repo: str, issue_number: int, body: str) -> None:
        owner, repo_name = repo.split("/", 1)
        self.client.api(
            "POST",
            f"repos/{owner}/{repo_name}/issues/{issue_number}/comments",
            fields={"body": body},
        )

    def run_tick(self, repo_cfg: RepoConfig) -> dict[str, Any]:
        self.ensure_stage_labels(repo_cfg.name)
        cleaned = self.cleanup_closed_issue_stage_labels(repo_cfg.name)
        pick = self.pick_next(repo_cfg)
        if not pick:
            return {"repo": repo_cfg.name, "cleaned_closed": cleaned, "action": "no-work"}

        number = int(pick["number"])
        stage = str(pick["picked_from_stage"])

        if stage == STAGE_BACKLOG:
            self.set_status(repo_cfg.name, number, STAGE_NEEDS_CLARIFICATION)
            return {
                "repo": repo_cfg.name,
                "cleaned_closed": cleaned,
                "action": "moved-to-needs-clarification",
                "issue": number,
            }

        if stage == STAGE_READY_TO_IMPLEMENT:
            self.set_status(repo_cfg.name, number, STAGE_IN_PROGRESS)
            return {
                "repo": repo_cfg.name,
                "cleaned_closed": cleaned,
                "action": "moved-to-in-progress",
                "issue": number,
            }

        return {
            "repo": repo_cfg.name,
            "cleaned_closed": cleaned,
            "action": "continue-in-progress",
            "issue": number,
        }

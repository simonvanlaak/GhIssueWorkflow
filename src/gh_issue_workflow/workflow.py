from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

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

SECURITY_STAGE_QUEUED = "stage:queued"
SECURITY_LABEL = "security"
SEVERITY_PREFIX = "severity:"

SECURITY_LABEL_DEFAULTS: dict[str, tuple[str, str]] = {
    SECURITY_STAGE_QUEUED: ("cfd3d7", "workflow queue stage"),
    SECURITY_LABEL: ("b60205", "security alert tracking"),
}

SEVERITY_COLORS: dict[str, str] = {
    "critical": "7f1d1d",
    "high": "d93f0b",
    "medium": "fbca04",
    "low": "0e8a16",
    "warning": "fbca04",
    "error": "d93f0b",
    "note": "1d76db",
    "unknown": "cfd3d7",
}


class Workflow:
    def __init__(self, client: GhClient) -> None:
        self.client = client

    @staticmethod
    def _split_repo(repo: str) -> tuple[str, str]:
        return repo.split("/", 1)

    def _list_repo_labels(self, repo: str) -> set[str]:
        owner, repo_name = self._split_repo(repo)
        rows = self.client.api("GET", f"repos/{owner}/{repo_name}/labels", fields={"per_page": 100})
        if not isinstance(rows, list):
            return set()

        names: set[str] = set()
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                names.add(str(row["name"]))
        return names

    def _create_label(self, repo: str, name: str, color: str, description: str) -> None:
        owner, repo_name = self._split_repo(repo)
        self.client.api(
            "POST",
            f"repos/{owner}/{repo_name}/labels",
            fields={"name": name, "color": color, "description": description},
        )

    def _ensure_labels_exist(self, repo: str, existing: set[str], labels: Iterable[str]) -> None:
        for label in labels:
            if label in existing:
                continue

            if label in SECURITY_LABEL_DEFAULTS:
                color, description = SECURITY_LABEL_DEFAULTS[label]
            elif label.startswith(SEVERITY_PREFIX):
                severity = label[len(SEVERITY_PREFIX) :].strip().lower() or "unknown"
                color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["unknown"])
                description = f"security severity: {severity}"
            else:
                color = "cfd3d7"
                description = "automation label"

            self._create_label(repo, label, color, description)
            existing.add(label)

    def ensure_stage_labels(self, repo: str) -> None:
        existing = self._list_repo_labels(repo)
        for label in sorted(KNOWN_STAGE_LABELS):
            if label in existing:
                continue
            self._create_label(repo, label, STAGE_COLORS[label], "automation stage label")

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
        owner, repo_name = self._split_repo(repo)
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
        owner, repo_name = self._split_repo(repo)
        issue = self.client.api("GET", f"repos/{owner}/{repo_name}/issues/{issue_number}")
        existing = [label["name"] for label in issue.get("labels", [])]
        if new_status is None:
            target_labels = sorted([label for label in existing if not label.startswith("stage:")])
        else:
            target_labels = sorted(apply_stage_label(existing, new_status))
        self.client.api_patch_json(f"repos/{owner}/{repo_name}/issues/{issue_number}", {"labels": target_labels})

    def post_comment(self, repo: str, issue_number: int, body: str) -> None:
        owner, repo_name = self._split_repo(repo)
        self.client.api(
            "POST",
            f"repos/{owner}/{repo_name}/issues/{issue_number}/comments",
            fields={"body": body},
        )

    def _list_issue_bodies(self, repo: str) -> list[str]:
        owner, repo_name = self._split_repo(repo)
        issues = self.client.api(
            "GET",
            f"repos/{owner}/{repo_name}/issues",
            fields={"state": "all", "per_page": 100},
        )
        if not isinstance(issues, list):
            return []

        bodies: list[str] = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            if issue.get("pull_request"):
                continue
            body = issue.get("body")
            if isinstance(body, str) and body:
                bodies.append(body)
        return bodies

    @staticmethod
    def _severity_from_alert(alert: dict[str, Any]) -> str:
        rule = alert.get("rule") if isinstance(alert.get("rule"), dict) else {}
        severity_raw = rule.get("security_severity_level") or rule.get("severity") or "unknown"
        severity = str(severity_raw).strip().lower() or "unknown"
        return severity

    @staticmethod
    def _alert_title(alert: dict[str, Any]) -> str:
        rule = alert.get("rule") if isinstance(alert.get("rule"), dict) else {}
        rule_id = str(rule.get("id") or "").strip()
        description = str(rule.get("description") or "").strip()

        headline = rule_id or description or f"code-scanning-alert-{alert.get('number', 'unknown')}"
        return f"security: {headline}"

    @staticmethod
    def _alert_location(alert: dict[str, Any]) -> str:
        most_recent_instance = alert.get("most_recent_instance")
        if not isinstance(most_recent_instance, dict):
            return "n/a"

        location = most_recent_instance.get("location")
        if not isinstance(location, dict):
            return "n/a"

        path = str(location.get("path") or "").strip()
        if not path:
            return "n/a"

        start_line = location.get("start_line") or location.get("line")
        end_line = location.get("end_line")

        if isinstance(start_line, int):
            if isinstance(end_line, int) and end_line > start_line:
                return f"{path}:{start_line}-{end_line}"
            return f"{path}:{start_line}"

        return path

    def _build_alert_issue_body(self, alert: dict[str, Any]) -> str:
        rule = alert.get("rule") if isinstance(alert.get("rule"), dict) else {}
        rule_id = str(rule.get("id") or "unknown")
        severity = self._severity_from_alert(alert)
        state = str(alert.get("state") or "unknown")
        created_at = str(alert.get("created_at") or "unknown")
        alert_url = str(alert.get("html_url") or "")
        location = self._alert_location(alert)

        return (
            "Auto-created from GitHub Advanced Security code scanning alert.\n\n"
            f"- Alert URL: {alert_url}\n"
            f"- Rule ID: {rule_id}\n"
            f"- Severity: {severity}\n"
            f"- State: {state}\n"
            f"- Created at: {created_at}\n"
            f"- Affected file(s): {location}\n"
        )

    def sync_code_scanning_alerts(self, repo: str) -> dict[str, int]:
        owner, repo_name = self._split_repo(repo)
        alerts_payload = self.client.api(
            "GET",
            f"repos/{owner}/{repo_name}/code-scanning/alerts",
            fields={"state": "open", "per_page": 100},
        )
        alerts = [alert for alert in alerts_payload if isinstance(alert, dict)] if isinstance(alerts_payload, list) else []

        existing_bodies = self._list_issue_bodies(repo)
        existing_labels = self._list_repo_labels(repo)

        created = 0
        skipped_existing = 0

        for alert in alerts:
            alert_url = str(alert.get("html_url") or "").strip()
            if alert_url and any(alert_url in body for body in existing_bodies):
                skipped_existing += 1
                continue

            severity_label = f"{SEVERITY_PREFIX}{self._severity_from_alert(alert)}"
            issue_labels = [SECURITY_STAGE_QUEUED, SECURITY_LABEL, severity_label]
            self._ensure_labels_exist(repo, existing_labels, issue_labels)

            issue_payload = {
                "title": self._alert_title(alert),
                "body": self._build_alert_issue_body(alert),
                "labels": issue_labels,
            }
            self.client.api_post_json(f"repos/{owner}/{repo_name}/issues", issue_payload)
            existing_bodies.append(issue_payload["body"])
            created += 1

        return {"created": created, "skipped_existing": skipped_existing}

    def run_tick(self, repo_cfg: RepoConfig) -> dict[str, Any]:
        self.ensure_stage_labels(repo_cfg.name)
        security_sync = self.sync_code_scanning_alerts(repo_cfg.name)
        cleaned = self.cleanup_closed_issue_stage_labels(repo_cfg.name)
        pick = self.pick_next(repo_cfg)

        base = {
            "repo": repo_cfg.name,
            "cleaned_closed": cleaned,
            "security_created": security_sync["created"],
            "security_skipped_existing": security_sync["skipped_existing"],
        }

        if not pick:
            return {**base, "action": "no-work"}

        number = int(pick["number"])
        stage = str(pick["picked_from_stage"])

        if stage == STAGE_BACKLOG:
            self.set_status(repo_cfg.name, number, STAGE_NEEDS_CLARIFICATION)
            return {**base, "action": "moved-to-needs-clarification", "issue": number}

        if stage == STAGE_READY_TO_IMPLEMENT:
            self.set_status(repo_cfg.name, number, STAGE_IN_PROGRESS)
            return {**base, "action": "moved-to-in-progress", "issue": number}

        return {**base, "action": "continue-in-progress", "issue": number}

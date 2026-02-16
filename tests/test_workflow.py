from __future__ import annotations

from typing import Any

from gh_issue_workflow.config import RepoConfig
from gh_issue_workflow.workflow import Workflow


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def api(
        self, method: str, path: str, *, fields: dict[str, Any] | None = None
    ) -> Any:
        self.calls.append((method, path, fields))

        if path.endswith("/labels") and method == "GET":
            return []

        if path.endswith("/code-scanning/alerts") and method == "GET":
            return []

        if path.startswith("repos/") and path.endswith("/issues") and method == "GET":
            state = (fields or {}).get("state")
            if state == "closed":
                return []
            if state == "open":
                return [
                    {
                        "number": 10,
                        "created_at": "2026-02-10T00:00:00Z",
                        "labels": [{"name": "stage:queued"}],
                    }
                ]
            if state == "all":
                return []
            return []

        if path.endswith("/issues/10/events"):
            return [
                {
                    "event": "labeled",
                    "label": {"name": "stage:ready-to-implement"},
                    "actor": {"login": "simonvanlaak"},
                }
            ]

        if path.endswith("/issues/10"):
            return {"labels": [{"name": "stage:queued"}]}

        return {}

    def api_patch_json(self, path: str, body: dict[str, Any]) -> Any:
        self.calls.append(("PATCH", path, body))
        return {}

    def api_post_json(self, path: str, body: dict[str, Any]) -> Any:
        self.calls.append(("POST_JSON", path, body))
        return {}


class FakeCodeScanningClient:
    def __init__(self, *, existing_issue_body: str | None = None) -> None:
        self.existing_issue_body = existing_issue_body
        self.created_labels: list[dict[str, Any]] = []
        self.created_issues: list[dict[str, Any]] = []

    def api(
        self, method: str, path: str, *, fields: dict[str, Any] | None = None
    ) -> Any:
        if path.endswith("/labels") and method == "GET":
            return [
                {"name": "stage:queued"},
                {"name": "security"},
            ]

        if path.endswith("/code-scanning/alerts") and method == "GET":
            return [
                {
                    "number": 2,
                    "html_url": "https://github.com/acme/repo/security/code-scanning/2",
                    "state": "open",
                    "created_at": "2026-02-15T22:48:31Z",
                    "rule": {
                        "id": "py/clear-text-logging-sensitive-data",
                        "description": "Sensitive data is logged in clear text",
                        "security_severity_level": "high",
                    },
                    "most_recent_instance": {
                        "location": {
                            "path": "src/app.py",
                            "start_line": 42,
                        }
                    },
                }
            ]

        if path.endswith("/issues") and method == "GET":
            if self.existing_issue_body is None:
                return []
            return [{"body": self.existing_issue_body}]

        if path.endswith("/labels") and method == "POST":
            self.created_labels.append(fields or {})
            return {}

        raise AssertionError(f"Unexpected API call: {method} {path} {fields}")

    def api_patch_json(self, path: str, body: dict[str, Any]) -> Any:
        raise AssertionError(f"Unexpected PATCH call: {path} {body}")

    def api_post_json(self, path: str, body: dict[str, Any]) -> Any:
        if path.endswith("/issues"):
            self.created_issues.append(body)
            return {"number": 99}
        raise AssertionError(f"Unexpected POST JSON call: {path} {body}")


def test_run_tick_moves_queued_to_needs_clarification_without_search_api() -> None:
    fake = FakeClient()
    wf = Workflow(fake)  # type: ignore[arg-type]
    result = wf.run_tick(RepoConfig(name="acme/repo", owner_logins=["simonvanlaak"]))

    assert result["action"] == "moved-to-needs-clarification"
    assert result["issue"] == 10

    patch_calls = [c for c in fake.calls if c[0] == "PATCH"]
    assert patch_calls
    assert patch_calls[-1][2] == {"labels": ["stage:needs-clarification"]}
    assert all(path != "search/issues" for _, path, _ in fake.calls)


def test_sync_code_scanning_alerts_creates_issue_with_labels() -> None:
    fake = FakeCodeScanningClient()
    wf = Workflow(fake)  # type: ignore[arg-type]

    result = wf.sync_code_scanning_alerts("acme/repo")

    assert result == {"created": 1, "skipped_existing": 0}
    assert fake.created_labels and fake.created_labels[0]["name"] == "severity:high"
    assert len(fake.created_issues) == 1

    created = fake.created_issues[0]
    assert created["title"] == "security: py/clear-text-logging-sensitive-data"
    assert set(created["labels"]) == {"stage:queued", "security", "severity:high"}

    body = created["body"]
    assert "https://github.com/acme/repo/security/code-scanning/2" in body
    assert "rule id: py/clear-text-logging-sensitive-data" in body.lower()
    assert "severity: high" in body.lower()
    assert "src/app.py:42" in body


def test_sync_code_scanning_alerts_dedupes_by_alert_url() -> None:
    alert_url = "https://github.com/acme/repo/security/code-scanning/2"
    fake = FakeCodeScanningClient(existing_issue_body=f"Already tracked: {alert_url}")
    wf = Workflow(fake)  # type: ignore[arg-type]

    result = wf.sync_code_scanning_alerts("acme/repo")

    assert result == {"created": 0, "skipped_existing": 1}
    assert fake.created_issues == []


class FakeClosedSecurityIssueClient:
    def __init__(self, *, alert_state: str = "open") -> None:
        self.alert_state = alert_state
        self.dismiss_calls: list[tuple[str, dict[str, Any]]] = []

    def api(
        self, method: str, path: str, *, fields: dict[str, Any] | None = None
    ) -> Any:
        if path.endswith("/issues") and method == "GET":
            state = (fields or {}).get("state")
            labels = (fields or {}).get("labels")
            if state == "all":
                return []
            if state == "closed" and labels == "security":
                return [
                    {
                        "number": 15,
                        "body": "Auto-created from GitHub Advanced Security code scanning alert.\n"
                        "- Alert URL: https://github.com/acme/repo/security/code-scanning/2\n",
                    }
                ]
            return []

        if path.endswith("/labels") and method == "GET":
            return []

        if path.endswith("/code-scanning/alerts") and method == "GET":
            return []

        if path.endswith("/code-scanning/alerts/2") and method == "GET":
            return {"number": 2, "state": self.alert_state}

        if path == "search/issues":
            query = (fields or {}).get("q", "")
            if "is:closed" in query:
                return {"items": []}
            return {"items": []}

        raise AssertionError(f"Unexpected API call: {method} {path} {fields}")

    def api_patch_json(self, path: str, body: dict[str, Any]) -> Any:
        if path.endswith("/code-scanning/alerts/2"):
            self.dismiss_calls.append((path, body))
            return {}
        if path.endswith("/issues/15"):
            return {}
        raise AssertionError(f"Unexpected PATCH call: {path} {body}")

    def api_post_json(self, path: str, body: dict[str, Any]) -> Any:
        raise AssertionError(f"Unexpected POST JSON call: {path} {body}")


def test_sync_closed_security_issues_dismisses_open_alert() -> None:
    fake = FakeClosedSecurityIssueClient(alert_state="open")
    wf = Workflow(fake)  # type: ignore[arg-type]

    result = wf.sync_closed_security_issues("acme/repo")

    assert result == {"dismissed": 1, "already_resolved": 0, "missing_link": 0}
    assert fake.dismiss_calls == [
        (
            "repos/acme/repo/code-scanning/alerts/2",
            {
                "state": "dismissed",
                "dismissed_reason": "false positive",
                "dismissed_comment": "Auto-dismissed: linked tracking issue #15 was closed.",
            },
        )
    ]


def test_sync_closed_security_issues_skips_already_resolved_alert() -> None:
    fake = FakeClosedSecurityIssueClient(alert_state="dismissed")
    wf = Workflow(fake)  # type: ignore[arg-type]

    result = wf.sync_closed_security_issues("acme/repo")

    assert result == {"dismissed": 0, "already_resolved": 1, "missing_link": 0}
    assert fake.dismiss_calls == []

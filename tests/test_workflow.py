from __future__ import annotations

from gh_issue_workflow.config import RepoConfig
from gh_issue_workflow.workflow import Workflow


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []

    def api(self, method: str, path: str, *, fields: dict | None = None):
        self.calls.append((method, path, fields))

        if path.endswith("/labels") and method == "GET":
            return []

        if path == "search/issues":
            query = (fields or {}).get("q", "")
            if "is:closed" in query:
                return {"items": []}
            return {
                "items": [
                    {
                        "number": 10,
                        "created_at": "2026-02-10T00:00:00Z",
                        "labels": [{"name": "stage:backlog"}],
                    }
                ]
            }

        if path.endswith("/issues/10/events"):
            return [
                {
                    "event": "labeled",
                    "label": {"name": "stage:ready-to-implement"},
                    "actor": {"login": "simonvanlaak"},
                }
            ]

        if path.endswith("/issues/10"):
            return {"labels": [{"name": "stage:backlog"}]}

        return {}

    def api_patch_json(self, path: str, body: dict):
        self.calls.append(("PATCH", path, body))
        return {}


def test_run_tick_moves_backlog_to_needs_clarification() -> None:
    fake = FakeClient()
    wf = Workflow(fake)  # type: ignore[arg-type]
    result = wf.run_tick(RepoConfig(name="acme/repo", owner_logins=["simonvanlaak"]))

    assert result["action"] == "moved-to-needs-clarification"
    assert result["issue"] == 10

    patch_calls = [c for c in fake.calls if c[0] == "PATCH"]
    assert patch_calls
    assert patch_calls[-1][2] == {"labels": ["stage:needs-clarification"]}

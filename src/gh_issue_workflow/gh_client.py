from __future__ import annotations

import json
import subprocess
import time
from typing import Any


class GhApiError(RuntimeError):
    """Raised when gh api fails permanently."""


class GhClient:
    def __init__(self, *, dry_run: bool = False, max_retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.dry_run = dry_run
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def api(self, method: str, path: str, *, fields: dict[str, Any] | None = None) -> Any:
        args = ["gh", "api", "--method", method.upper(), path]
        if fields:
            for key, value in fields.items():
                args.extend(["-f", f"{key}={value}"])

        return self._run_json(args)

    def api_patch_json(self, path: str, body: dict[str, Any]) -> Any:
        args = ["gh", "api", "--method", "PATCH", path]
        return self._run_json(args, stdin_json=body)

    def _run_json(self, args: list[str], *, stdin_json: dict[str, Any] | None = None) -> Any:
        if self.dry_run and any(flag in args for flag in ["POST", "PATCH", "PUT", "DELETE"]):
            return {"dry_run": True, "args": args, "body": stdin_json}

        for attempt in range(self.max_retries + 1):
            proc = subprocess.run(
                args,
                input=json.dumps(stdin_json) if stdin_json else None,
                text=True,
                capture_output=True,
                check=False,
            )
            if proc.returncode == 0:
                out = proc.stdout.strip()
                return json.loads(out) if out else {}

            stderr = proc.stderr.lower()
            rate_limited = "rate limit" in stderr or "secondary rate limit" in stderr
            if rate_limited and attempt < self.max_retries:
                time.sleep(self.backoff_seconds * (2**attempt))
                continue

            raise GhApiError(proc.stderr.strip() or proc.stdout.strip() or f"command failed: {' '.join(args)}")

        raise GhApiError("unreachable")

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gh_issue_workflow.config import load_config
from gh_issue_workflow.gh_client import GhClient
from gh_issue_workflow.stages import KNOWN_STAGE_LABELS
from gh_issue_workflow.workflow import Workflow


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-repo GitHub issue stage workflow")
    parser.add_argument("--config", type=Path, required=True, help="JSON/YAML config path")
    parser.add_argument("--dry-run", action="store_true", help="Simulate writes")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tick", help="Process one deterministic tick across repos")
    sub.add_parser("ensure-labels", help="Ensure stage labels exist in all repos")
    sub.add_parser("cleanup-closed", help="Remove stage:* labels from closed issues")

    set_status = sub.add_parser("set-status", help="Set a stage on one issue")
    set_status.add_argument("--repo", required=True)
    set_status.add_argument("--issue", type=int, required=True)
    set_status.add_argument("--status", required=True, choices=sorted(KNOWN_STAGE_LABELS))

    comment = sub.add_parser("comment", help="Post comment to one issue")
    comment.add_argument("--repo", required=True)
    comment.add_argument("--issue", type=int, required=True)
    comment.add_argument("--body", required=True)

    sub.add_parser("pick-next", help="Show next actionable issue per repo")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    cfg = load_config(args.config)
    workflow = Workflow(GhClient(dry_run=args.dry_run))

    if args.cmd == "ensure-labels":
        for repo in cfg.repos:
            workflow.ensure_stage_labels(repo.name)
            print(json.dumps({"event": "ensure-labels", "repo": repo.name}))
        return 0

    if args.cmd == "cleanup-closed":
        for repo in cfg.repos:
            cleaned = workflow.cleanup_closed_issue_stage_labels(repo.name)
            print(json.dumps({"event": "cleanup-closed", "repo": repo.name, "cleaned": cleaned}))
        return 0

    if args.cmd == "pick-next":
        for repo in cfg.repos:
            pick = workflow.pick_next(repo)
            print(json.dumps({"event": "pick-next", "repo": repo.name, "pick": pick}))
        return 0

    if args.cmd == "set-status":
        workflow.set_status(args.repo, args.issue, args.status)
        print(json.dumps({"event": "set-status", "repo": args.repo, "issue": args.issue, "status": args.status}))
        return 0

    if args.cmd == "comment":
        workflow.post_comment(args.repo, args.issue, args.body)
        print(json.dumps({"event": "comment", "repo": args.repo, "issue": args.issue}))
        return 0

    if args.cmd == "tick":
        for repo in cfg.repos:
            print(json.dumps({"event": "tick", **workflow.run_tick(repo)}))
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

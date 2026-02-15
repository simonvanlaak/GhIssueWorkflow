from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RepoConfig:
    name: str
    owner_logins: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppConfig:
    repos: list[RepoConfig]


def load_config(path: Path) -> AppConfig:
    """Load app config from JSON or YAML."""
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    repos = []
    for repo in payload.get("repos", []):
        repos.append(
            RepoConfig(
                name=str(repo["name"]),
                owner_logins=[str(v) for v in repo.get("owner_logins", [])],
            )
        )

    return AppConfig(repos=repos)

from pathlib import Path

from gh_issue_workflow.config import load_config


def test_load_config_json(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(
        '{"repos": [{"name": "acme/repo1", "owner_logins": ["alice"]}]}',
        encoding="utf-8",
    )

    parsed = load_config(cfg)
    assert len(parsed.repos) == 1
    assert parsed.repos[0].name == "acme/repo1"
    assert parsed.repos[0].owner_logins == ["alice"]


def test_load_config_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "repos:\n"
        "  - name: acme/repo2\n"
        "    owner_logins: [bob]\n",
        encoding="utf-8",
    )

    parsed = load_config(cfg)
    assert len(parsed.repos) == 1
    assert parsed.repos[0].name == "acme/repo2"
    assert parsed.repos[0].owner_logins == ["bob"]

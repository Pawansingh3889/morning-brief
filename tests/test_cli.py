"""CLI tests for `preview`, `why`, and the query builder."""
import json

import yaml
from typer.testing import CliRunner

from morning_brief.cli import _build_query, app

runner = CliRunner()


def _write_rules(path):
    path.write_text(
        yaml.safe_dump(
            {
                "high_priority_senders": ["@canonical.com"],
                "high_keywords": ["review requested"],
                "github_sender": "notifications@github.com",
                "github_low_keywords": ["starred"],
                "spam_senders": ["@myexpertify.org"],
                "spam_keywords": ["reaching out to connect"],
            }
        )
    )


def test_build_query_uses_days_by_default():
    assert _build_query(None, 1, True) == "newer_than:1d is:unread"


def test_build_query_hours_overrides_days():
    assert _build_query(4, 1, True) == "newer_than:4h is:unread"


def test_build_query_drops_unread_clause():
    assert _build_query(None, 2, False) == "newer_than:2d"


def test_preview_reports_high_bucket(tmp_path):
    home = tmp_path
    _write_rules(home / "rules.yaml")
    result = runner.invoke(
        app,
        [
            "preview",
            "--home", str(home),
            "--sender", "hr@canonical.com",
            "--subject", "Interview next week",
        ],
    )
    assert result.exit_code == 0
    assert "Bucket: HIGH" in result.stdout
    assert "high_sender:@canonical.com" in result.stdout


def test_preview_reports_default_medium(tmp_path):
    home = tmp_path
    _write_rules(home / "rules.yaml")
    result = runner.invoke(
        app,
        [
            "preview",
            "--home", str(home),
            "--sender", "x@y.com",
            "--subject", "anything",
        ],
    )
    assert result.exit_code == 0
    assert "Bucket: MEDIUM" in result.stdout
    assert "Reason: default" in result.stdout


def test_preview_missing_rules_exits_one(tmp_path):
    result = runner.invoke(
        app,
        [
            "preview",
            "--home", str(tmp_path),
            "--sender", "x@y.com",
            "--subject", "z",
        ],
    )
    assert result.exit_code == 1


def test_why_explains_stored_message(tmp_path):
    home = tmp_path
    _write_rules(home / "rules.yaml")
    state = {
        "processed": {
            "abc123": {
                "date": "2026-04-26",
                "from": "hr@canonical.com",
                "subject": "Interview",
                "bucket": "HIGH",
                "thread_id": "t1",
            }
        }
    }
    (home / "state.json").write_text(json.dumps(state))
    result = runner.invoke(app, ["why", "abc123", "--home", str(home)])
    assert result.exit_code == 0
    assert "Stored:  HIGH" in result.stdout
    assert "Now:     HIGH" in result.stdout


def test_why_unknown_msg_id_exits_one(tmp_path):
    home = tmp_path
    _write_rules(home / "rules.yaml")
    (home / "state.json").write_text('{"processed": {}}')
    result = runner.invoke(app, ["why", "nope", "--home", str(home)])
    assert result.exit_code == 1

"""Unit tests for the label-store module."""
from morning_brief.labels import append, load_all, load_latest


def test_append_and_load(tmp_path):
    p = tmp_path / "labels.jsonl"
    append(p, {"msg_id": "a", "stars": 5, "from": "x", "subject": "y", "date": "2026-04-19"})
    append(p, {"msg_id": "b", "stars": 1, "from": "z", "subject": "w", "date": "2026-04-19"})
    latest = load_latest(p)
    assert latest["a"]["stars"] == 5
    assert latest["b"]["stars"] == 1


def test_latest_overrides_earlier(tmp_path):
    p = tmp_path / "labels.jsonl"
    append(p, {"msg_id": "a", "stars": 1, "from": "x", "subject": "y", "date": "2026-04-19"})
    append(p, {"msg_id": "a", "stars": 5, "from": "x", "subject": "y", "date": "2026-04-19"})
    latest = load_latest(p)
    assert latest["a"]["stars"] == 5


def test_load_all_keeps_history(tmp_path):
    p = tmp_path / "labels.jsonl"
    append(p, {"msg_id": "a", "stars": 1, "from": "x", "subject": "y", "date": "2026-04-19"})
    append(p, {"msg_id": "a", "stars": 5, "from": "x", "subject": "y", "date": "2026-04-19"})
    assert len(load_all(p)) == 2


def test_missing_file_returns_empty(tmp_path):
    p = tmp_path / "does-not-exist.jsonl"
    assert load_latest(p) == {}
    assert load_all(p) == []

"""Append-only JSONL store for per-message star ratings."""
from __future__ import annotations

import json
from pathlib import Path


def append(labels_path: Path, entry: dict) -> None:
    with labels_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def load_latest(labels_path: Path) -> dict[str, dict]:
    """Map msg_id to its most recent label entry; later lines override earlier."""
    if not labels_path.exists():
        return {}
    latest: dict[str, dict] = {}
    with labels_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            latest[entry["msg_id"]] = entry
    return latest


def load_all(labels_path: Path) -> list[dict]:
    if not labels_path.exists():
        return []
    entries: list[dict] = []
    with labels_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries

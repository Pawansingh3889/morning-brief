"""Persistent state: processed message IDs and their classifications."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


def load(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"processed": {}}


def prune(state: dict, days: int = 7) -> dict:
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    state["processed"] = {
        k: v for k, v in state["processed"].items() if v.get("date", "") >= cutoff
    }
    return state


def save(state: dict, path: Path) -> None:
    path.write_text(json.dumps(state, indent=2))

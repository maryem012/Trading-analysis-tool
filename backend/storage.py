"""
Small atomic-write JSON storage helpers, shared by alerts.py and broker.py.

This is local-disk storage, not a database — fine for a single-process
personal app, but it does NOT survive a Railway redeploy (no volume is
mounted). Only use it for state that's acceptable to lose on redeploy.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)  # atomic on the same filesystem

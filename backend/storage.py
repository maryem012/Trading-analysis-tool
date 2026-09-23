"""
Small atomic-write JSON storage helpers, shared by alerts.py and broker.py.

This is local-disk storage, not a database — fine for a single-process
personal app. In production, DATA_DIR should point at a mounted Railway
Volume (set via the DATA_DIR env var) so this survives redeploys; locally
it defaults to backend/data/, which does NOT survive anything (gitignored,
and there's no volume outside Railway) but that's fine for dev.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent / "data")))


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

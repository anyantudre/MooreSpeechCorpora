"""JSONL manifests: the single format every step reads and writes.

One line per item. Common keys:
  id, audio_filepath (relative to the recipe's output_dir), text, duration, language, source,
plus step-specific keys (start, end, score, translation, ...).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def write(path: str | Path, rows: Iterable[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def total_hours(rows: Iterable[dict]) -> float:
    return sum(r.get("duration", 0.0) for r in rows) / 3600

"""Merge the final clips of several runs into one folder, so speakers can be labelled and the dataset
exported in one go (e.g. a corpus built from proverbs, tales and riddles recipes).

Each run's clips are linked (or copied when links are not possible) under `clips/<run>/`, and clip ids
get the run name in front, so ids and speaker groups stay unique across runs. The filter's extra views
(final_<name>.jsonl, e.g. final_asr.jsonl) are merged the same way, for the runs that have them.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import manifest

AUDIO_KEYS = ("audio_filepath", "voice_filepath", "untrimmed_audio_filepath")


def _place(src: Path, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def _merge(run: Path, out: Path, rows: list[dict]) -> list[dict]:
    merged = []
    for r in rows:
        r = {**r, "id": f"{run.name}_{r['id']}", "run": run.name}
        for key in AUDIO_KEYS:
            if r.get(key):
                dest = f"clips/{run.name}/{Path(r[key]).parent.name}_{Path(r[key]).name}"
                _place(run / r[key], out / dest)
                r[key] = dest
        merged.append(r)
    return merged


def combine(runs: list[str | Path], output: str | Path) -> list[dict]:
    out = Path(output)
    rows, views = [], {}
    for run in map(Path, runs):
        final = manifest.read(run / "final.jsonl")
        if not final:
            raise FileNotFoundError(f"No clips in {run / 'final.jsonl'}: run the recipe up to `filter` first")
        rows += _merge(run, out, final)
        for view in sorted(run.glob("final_*.jsonl")):
            views.setdefault(view.name, []).extend(_merge(run, out, manifest.read(view)))
    manifest.write(out / "final.jsonl", rows)
    for name, view_rows in views.items():
        manifest.write(out / name, view_rows)
    return rows

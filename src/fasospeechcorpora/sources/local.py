"""Your own recordings: a folder of audio files, each with an optional `<name>.txt` next to it.

The text file can be
  - a transcript: plain text, split into sentences, then aligned to the audio;
  - an Audacity label file (File > Export > Labels): one `start<TAB>end<TAB>text` line per clip
    (commas also work: `0.00, 5.35, "text"`). Those clips are cut as they are, with no alignment.
Audio without a text file is cut at pauses and can be transcribed.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..text import normalize, split_sentences
from .base import Source, register

AUDIO_EXT = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".webm", ".mp4"}
LABEL = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[\t,]\s*(\d+(?:\.\d+)?)\s*[\t,]\s*(.*?)\s*$")


def read_text_file(path: Path, lang) -> dict:
    """Return {"segments": [...]} for a label file, else {"lines": [...]}."""
    raw = [x for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    labels = [LABEL.match(x) for x in raw]
    if raw and all(labels):
        return {"segments": [{"start": float(m[1]), "end": float(m[2]), "text": normalize(m[3].strip('"'))}
                             for m in labels if m[3].strip('"').strip()]}
    return {"lines": [s for x in raw for s in split_sentences(x, lang)]}


@register("local")
class Local(Source):
    """Params: path (folder)."""

    def fetch(self, raw_dir: Path) -> list[dict]:
        folder = Path(self.params["path"])
        records = []
        for src in sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXT):
            dest = raw_dir / src.name
            if not dest.exists():
                raw_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            txt = src.with_suffix(".txt")
            text = read_text_file(txt, self.lang) if txt.exists() else {"lines": None}
            records.append({"id": src.stem, "audio_filepath": dest.name, "source": "local", **text})
            if self.limit and len(records) >= self.limit:
                break
        return records

"""Your own recordings: a folder of audio files, each with an optional `<name>.txt` transcript."""
from __future__ import annotations

import shutil
from pathlib import Path

from ..text import normalize
from .base import Source, register

AUDIO_EXT = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".webm", ".mp4"}


@register("local")
class Local(Source):
    """Params: path (folder). Text files hold one sentence per line."""

    def fetch(self, raw_dir: Path) -> list[dict]:
        folder = Path(self.params["path"])
        records = []
        for src in sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXT):
            dest = raw_dir / src.name
            if not dest.exists():
                raw_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            txt = src.with_suffix(".txt")
            lines = ([normalize(x) for x in txt.read_text(encoding="utf-8").splitlines() if x.strip()]
                     if txt.exists() else None)
            records.append({"id": src.stem, "audio_filepath": dest.name, "lines": lines, "source": "local"})
            if self.limit and len(records) >= self.limit:
                break
        return records

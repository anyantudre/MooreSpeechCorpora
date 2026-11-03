"""Clips from an existing Hugging Face dataset, to re-process them (trim, clean, filter, relabel).

Reads the parquet files directly (no audio decoding library needed) and writes each clip's audio
bytes to `raw/`. Each clip becomes one record whose single segment is the whole clip, so `align`
copies it as is and `trim` can then cut it to its speech. Needs `pip install "fasospeechcorpora[hub]"`
and HF_TOKEN for gated or private datasets.
"""
from __future__ import annotations

import re
from pathlib import Path

import soundfile as sf

from ..text import normalize
from .base import Source, register


def _ext(data: bytes, path: str | None) -> str:
    if path and Path(path).suffix:
        return Path(path).suffix.lower()
    head = data[:4]
    return ".flac" if head == b"fLaC" else ".wav" if head == b"RIFF" else ".ogg" if head == b"OggS" else ".mp3"


@register("hf_dataset")
class HFDataset(Source):
    """Params: repo ("user/name"), splits (list, default ["train"]), audio_column ("audio"),
    text_column ("text"), keep_columns (list of columns copied into each clip, e.g. [chapter]),
    subset (the folder of one config, e.g. "contes", when several configs share split names)."""

    @staticmethod
    def pattern(repo: str, split: str, subset: str | None = None) -> str:
        return f"datasets/{repo}/{subset}/{split}-*.parquet" if subset else f"datasets/{repo}/**/{split}-*.parquet"

    def fetch(self, raw_dir: Path) -> list[dict]:
        import pyarrow.parquet as pq
        from huggingface_hub import HfFileSystem

        from ..export import hf_token

        p = self.params
        repo, audio_col, text_col = p["repo"], p.get("audio_column", "audio"), p.get("text_column", "text")
        keep = list(p.get("keep_columns", []))
        fs = HfFileSystem(token=hf_token())
        raw_dir.mkdir(parents=True, exist_ok=True)
        records = []
        for split in p.get("splits", ["train"]):
            files = sorted(fs.glob(self.pattern(repo, split, p.get("subset"))))
            where = f"{repo}/{p['subset']}" if p.get("subset") else repo
            if not files:
                raise FileNotFoundError(f"No parquet files for split '{split}' in {where}")
            for f in files:
                pf = pq.ParquetFile(fs.open(f, "rb"))
                for g in range(pf.num_row_groups):
                    for i, row in enumerate(pf.read_row_group(g, columns=[audio_col, text_col, *keep]).to_pylist()):
                        if self.limit and len(records) >= self.limit:
                            return records
                        text = normalize(row[text_col] or "")
                        if not text:
                            continue
                        rid = re.sub(r"\W", "_", f"{split}_{Path(f).stem}_{g}_{i}")
                        audio = row[audio_col]
                        dest = raw_dir / f"{rid}{_ext(audio['bytes'], audio.get('path'))}"
                        if not dest.exists():
                            dest.write_bytes(audio["bytes"])
                        duration = sf.info(dest).duration if dest.suffix != ".mp3" else None
                        rec = {"id": rid, "audio_filepath": dest.name, "source": f"hf:{where}/{split}",
                               "meta": {"hf_split": split, **{k: row[k] for k in keep}}}
                        rec["segments"] = [{"start": 0.0, "end": duration if duration else 1e9, "text": text}]
                        records.append(rec)
        return records

"""Clips from an existing Hugging Face dataset, to re-process them (trim, clean, filter, relabel).

Reads the parquet files directly (no audio decoding library needed) and writes each clip's audio
bytes to `raw/`. Each clip becomes one record whose single segment is the whole clip, so `align`
copies it as is and `trim` can then cut it to its speech. Needs `pip install "fasospeechcorpora[hub]"`
and HF_TOKEN for gated or private datasets.

With `rejoin: chapter` the clips of each chapter (a column listed in keep_columns) are joined back,
in dataset order, into one recording whose text is the clips' texts, so `align` cuts it again. Use it
when the published clips are cut in the wrong places. `dedupe_lines: true` also drops the lines that
repeat a passage (see text.drop_repeated_lines), as in moore-speech-contes vol5.
"""
from __future__ import annotations

import re
from pathlib import Path

import soundfile as sf

from ..text import drop_repeated_lines, normalize, split_sentences
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
    subset (the folder of one config, e.g. "contes", when several configs share split names),
    rejoin (a column: join each group's clips into one recording to align again), dedupe_lines."""

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
        return self._rejoin(records, raw_dir) if p.get("rejoin") else records

    def _rejoin(self, records: list[dict], raw_dir: Path) -> list[dict]:
        import numpy as np

        from .. import audio

        key, out, groups = self.params["rejoin"], [], {}
        for r in records:
            groups.setdefault((r["meta"]["hf_split"], str(r["meta"][key])), []).append(r)
        for (split, value), rs in groups.items():
            rid = re.sub(r"\W", "_", f"{split}_{value}")
            dest = raw_dir / "rejoined" / f"{rid}.wav"
            if not dest.exists():
                audio.save(dest, np.concatenate([audio.load(raw_dir / r["audio_filepath"], 16_000) for r in rs]), 16_000)
            lines = [r["segments"][0]["text"] for r in rs]
            if self.params.get("dedupe_lines"):
                lines = drop_repeated_lines(lines)
            out.append({"id": rid, "audio_filepath": f"rejoined/{rid}.wav", "source": rs[0]["source"],
                        "meta": rs[0]["meta"], "pieces": len(rs),
                        "lines": [s for x in lines for s in split_sentences(x, self.lang)]})
        return out

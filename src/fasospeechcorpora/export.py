"""Write the final clips in the formats people train with.

  manifest   final.jsonl (always written by the filter step; NeMo-style)
  ljspeech   ljspeech/wavs/*.wav + ljspeech/metadata.csv (id|text|text), for TTS recipes
  hf         a Hugging Face `datasets` folder in hf/, pushed to the Hub when `repo_id` is set
             (token from the HF_TOKEN environment variable or a .env file). `gated: manual`
             (or `auto`) makes people request access before they can download it.

With `layout: corpora_v1` the hf export uses the MooreSpeechCorpora columns, in order:
audio, text, duration, voice, speaker_id, denoised_audio (the voice-only copy from `trim`), then
source, chapter, alignment_score and cer. Run the `speakers` step first to fill voice and speaker_id.

With `pairs: {translation: fra}` the hf export holds speech translation pairs instead of single
clips: every clip in the recipe's language next to the translation spoken beside it (see make_pairs).
The filter must keep both languages (`filter.languages: [mos, fra]`).
"""
from __future__ import annotations

import os
import shutil
from collections import defaultdict
from pathlib import Path

from . import manifest

KEEP = ("id", "text", "duration", "language", "source", "source_id", "translation", "score")


def hf_token() -> str | None:
    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"]
    for folder in [Path.cwd(), *Path.cwd().parents]:
        env = folder / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                key, _, value = line.partition("=")
                if key.strip() == "HF_TOKEN" and value.strip():
                    return value.strip().strip("'\"")
    return None


def make_pairs(rows: list[dict], source_lang: str, translation: str,
               prefixes: tuple[str, str] | None = None) -> list[dict]:
    """Pair each clip in `source_lang` with the translation clip next to it in the same recording:
    the one right after it, or else the one right before it. A proverb read "Mooré, French, Mooré"
    gives two pairs that share the French clip, like the published moore-speech-proverbes dataset."""
    sp, tp = prefixes or (source_lang, translation)
    by_source = defaultdict(list)
    for r in rows:
        by_source[r.get("source_id", r["id"])].append(r)
    pairs = []
    for sid, rs in by_source.items():
        rs.sort(key=lambda r: r.get("start", 0.0))
        for i, r in enumerate(rs):
            if r.get("language") != source_lang:
                continue
            nxt = rs[i + 1] if i + 1 < len(rs) else None
            prev = rs[i - 1] if i > 0 else None
            t = nxt if nxt and nxt.get("language") == translation else \
                prev if prev and prev.get("language") == translation else None
            if t is None:
                continue
            pairs.append({"id": r["id"], f"{sp}_audio": r["audio_filepath"], f"{sp}_text": r["text"],
                          f"{tp}_text": t["text"], f"{tp}_audio": t["audio_filepath"],
                          f"duration_{sp}": r["duration"], f"duration_{tp}": t["duration"], "chapter": sid})
    return pairs


def to_ljspeech(rows: list[dict], root: Path, out: Path) -> Path:
    wavs = out / "wavs"
    wavs.mkdir(parents=True, exist_ok=True)
    lines = []
    for r in rows:
        dest = wavs / f"{r['id']}.wav"
        if not dest.exists():
            shutil.copy2(root / r["audio_filepath"], dest)
        text = r["text"].replace("|", " ")
        lines.append(f"{r['id']}|{text}|{text}")
    (out / "metadata.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def to_hf(rows: list[dict], root: Path, out: Path, repo_id: str | None = None, private: bool = True,
          test_size: float | None = None, seed: int = 42, config_name: str = "default", gated: str | None = None,
          audio_columns: dict[str, str] | None = None, keep: tuple[str, ...] | None = None,
          order: list[str] | None = None):
    """`audio_columns` maps dataset column -> row key holding a path (default: audio <- audio_filepath)."""
    from datasets import Audio, Dataset

    audio_columns = audio_columns or {"audio": "audio_filepath"}
    keep = keep or KEEP
    columns = {k: [r.get(k) for r in rows] for k in keep if any(k in r for r in rows)}
    for col, key in audio_columns.items():
        columns[col] = [str(root / r[key]) for r in rows]
    if order:
        columns = {k: columns[k] for k in order if k in columns}
    ds = Dataset.from_dict(columns)
    for col in audio_columns:
        ds = ds.cast_column(col, Audio(sampling_rate=16_000))
    ds = ds.train_test_split(test_size=test_size, seed=seed) if test_size else ds
    ds.save_to_disk(str(out))
    if repo_id:
        token = hf_token()
        if not token:
            raise RuntimeError("Set HF_TOKEN (environment or .env file) to push to the Hub.")
        ds.push_to_hub(repo_id, config_name=config_name, private=private, token=token)
        if gated:
            from huggingface_hub import HfApi
            HfApi(token=token).update_repo_settings(repo_id, repo_type="dataset", gated=gated)
    return ds


def export(rows: list[dict], root: Path, cfg: dict, language: str = "") -> None:
    formats = cfg.get("formats", ["manifest"])
    hub = dict(repo_id=cfg.get("repo_id"), private=cfg.get("private", True), test_size=cfg.get("test_size"),
               config_name=cfg.get("config_name", "default"), gated=cfg.get("gated"))
    pairs_cfg = cfg.get("pairs")
    if pairs_cfg:
        tr = pairs_cfg["translation"]
        sp, tp = pairs_cfg.get("prefixes", (language, tr))
        pairs = make_pairs(rows, language, tr, (sp, tp))
        manifest.write(root / "pairs.jsonl", pairs)
        if "hf" in formats:
            keep = (f"{sp}_text", f"{tp}_text", f"duration_{sp}", f"duration_{tp}", "chapter")
            to_hf(pairs, root, root / "hf", **hub, keep=keep,
                  audio_columns={f"{sp}_audio": f"{sp}_audio", f"{tp}_audio": f"{tp}_audio"},
                  order=[k for k in pairs[0] if k != "id"] if pairs else None)
        rows = [r for r in rows if r.get("language") == language]      # ljspeech stays monolingual
    elif "hf" in formats and cfg.get("layout") == "corpora_v1":
        v1 = [{"audio": r["audio_filepath"], "text": r["text"], "duration": r["duration"],
               "voice": r.get("voice"), "speaker_id": r.get("speaker_id"),
               "denoised_audio": r.get("voice_filepath", r["audio_filepath"]),
               "source": r.get("source"), "chapter": r.get("chapter", r.get("source_id")),
               "alignment_score": r.get("score"), "cer": r.get("cer")} for r in rows]
        order = ["audio", "text", "duration", "voice", "speaker_id", "denoised_audio",
                 "source", "chapter", "alignment_score", "cer"]
        to_hf(v1, root, root / "hf", **hub, audio_columns={"audio": "audio", "denoised_audio": "denoised_audio"},
              keep=tuple(k for k in order if k not in ("audio", "denoised_audio")), order=order)
    elif "hf" in formats:
        to_hf(rows, root, root / "hf", **hub)
    if "ljspeech" in formats:
        to_ljspeech(rows, root, root / "ljspeech")

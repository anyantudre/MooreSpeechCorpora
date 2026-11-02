"""Write the final clips in the formats people train with.

  manifest   final.jsonl (always written by the filter step; NeMo-style)
  ljspeech   ljspeech/wavs/*.wav + ljspeech/metadata.csv (id|text|text), for TTS recipes
  hf         a Hugging Face `datasets` folder in hf/, pushed to the Hub when `repo_id` is set
             (token from the HF_TOKEN environment variable or a .env file). `gated: manual`
             (or `auto`) makes people request access before they can download it.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

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
          test_size: float | None = None, seed: int = 42, config_name: str = "default", gated: str | None = None):
    from datasets import Audio, Dataset

    columns = {k: [r.get(k) for r in rows] for k in KEEP if any(k in r for r in rows)}
    columns["audio"] = [str(root / r["audio_filepath"]) for r in rows]
    ds = Dataset.from_dict(columns).cast_column("audio", Audio(sampling_rate=16_000))
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


def export(rows: list[dict], root: Path, cfg: dict) -> None:
    formats = cfg.get("formats", ["manifest"])
    if "ljspeech" in formats:
        to_ljspeech(rows, root, root / "ljspeech")
    if "hf" in formats:
        to_hf(rows, root, root / "hf", repo_id=cfg.get("repo_id"), private=cfg.get("private", True),
              test_size=cfg.get("test_size"), config_name=cfg.get("config_name", "default"),
              gated=cfg.get("gated"))

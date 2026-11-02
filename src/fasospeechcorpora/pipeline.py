"""Run a recipe step by step. Every step reads and writes a JSONL manifest in the output folder,
so any step can be re-run alone, and finished work is skipped on the next run.

  fetch       -> raw/ + raw.jsonl            download audio (and text) from the source
  prepare     -> wav/ + prepared.jsonl       decode to mono 16 kHz wav
  enhance     -> voice/ + prepared.jsonl     optional: keep only the voice (removes background music)
  align       -> clips/ + aligned.jsonl      known text: one clip per sentence (forced alignment)
  segment     -> clips/ + segmented.jsonl    no text: one clip per pause-delimited utterance
  transcribe  -> segmented.jsonl             no text: pseudo-labels from an ASR model
  filter      -> final.jsonl                 drop bad clips, print a summary
  export      -> ljspeech/, hf/              training formats, optional Hub upload
"""
from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from tqdm import tqdm

from . import audio, manifest
from .config import Recipe
from .text import foreign_ratio

log = logging.getLogger("fasospeechcorpora")
STEPS = ["fetch", "prepare", "enhance", "align", "segment", "transcribe", "filter", "export"]


class Pipeline:
    def __init__(self, recipe: Recipe, limit: int | None = None):
        self.r = recipe
        self.lang = recipe.language
        self.root = Path(recipe.output_dir)
        self.limit = limit
        self.sr = recipe.sample_rate

    def path(self, name: str) -> Path:
        return self.root / name

    def run(self, steps: list[str] | None = None) -> None:
        steps = steps or self.r.steps
        for step in steps:
            if step not in STEPS:
                raise ValueError(f"Unknown step '{step}'. Steps: {', '.join(STEPS)}")
        for step in STEPS:                      # always run in pipeline order
            if step in steps:
                log.info("== %s", step)
                getattr(self, step)()

    # ---- steps -------------------------------------------------------------------------------

    def fetch(self) -> None:
        from .sources import get_source

        params = dict(self.r.source)
        if self.limit is not None:
            params["limit"] = self.limit
        records = get_source(self.lang, params).fetch(self.path("raw"))
        for rec in records:
            rec["audio_filepath"] = f"raw/{rec['audio_filepath']}"
        n = manifest.write(self.path("raw.jsonl"), records)
        log.info("%d recordings fetched", n)

    def prepare(self) -> None:
        rows = []
        for rec in tqdm(manifest.read(self.path("raw.jsonl")), desc="prepare"):
            dest = self.path(f"wav/{rec['id']}.wav")
            if not dest.exists():
                audio.save(dest, audio.load(self.root / rec["audio_filepath"], self.sr), self.sr)
            rows.append({**rec, "audio_filepath": f"wav/{rec['id']}.wav", "duration": audio.duration(dest)})
        manifest.write(self.path("prepared.jsonl"), rows)
        log.info("%d recordings, %.2f h", len(rows), manifest.total_hours(rows))

    def enhance(self) -> None:
        from .enhance import VoiceExtractor

        cfg = self.r.enhance
        rows = manifest.read(self.path("prepared.jsonl"))
        extractor = None
        for rec in tqdm(rows, desc="enhance"):
            if rec.get("original_audio_filepath"):
                continue                                    # already enhanced
            dest = self.path(f"voice/{rec['id']}.wav")
            if not dest.exists():
                extractor = extractor or VoiceExtractor(cfg.get("model", "htdemucs"), cfg.get("device"))
                audio.save(dest, extractor(audio.load(self.root / rec["audio_filepath"], self.sr), self.sr), self.sr)
            rec["original_audio_filepath"], rec["audio_filepath"] = rec["audio_filepath"], f"voice/{rec['id']}.wav"
        manifest.write(self.path("prepared.jsonl"), rows)
        log.info("%d recordings reduced to voice", len(rows))

    def align(self) -> None:
        records = [r for r in manifest.read(self.path("prepared.jsonl")) if r.get("lines") or r.get("segments")]
        cfg = self.r.align
        backend = cfg.get("backend", "mms")
        aligner = None
        out = []
        for rec in tqdm(records, desc=f"align ({backend})"):
            cache = self.path(f"clips/{rec['id']}/clips.jsonl")
            if cache.exists():
                out += manifest.read(cache)
                continue
            if rec.get("segments"):                    # timestamps given (e.g. Audacity labels): just cut
                rows = self._cut_segments(rec)
            elif backend == "fairseq":
                rows = self._align_fairseq(rec, cfg)
            else:
                if aligner is None:
                    from .align import MMSAligner
                    aligner = MMSAligner(device=cfg.get("device"), window=cfg.get("window", 30.0),
                                         use_star=cfg.get("star", True))
                rows = self._align_mms(rec, aligner, cfg)
            manifest.write(cache, rows)
            out += rows
        manifest.write(self.path("aligned.jsonl"), out)
        log.info("%d clips, %.2f h", len(out), manifest.total_hours(out))

    def _clip_row(self, rec: dict, k: int, text: str, start: float, end: float, **extra) -> dict:
        langs = rec.get("line_languages")
        return {"id": f"{rec['id']}_{k:04d}", "audio_filepath": f"clips/{rec['id']}/{rec['id']}_{k:04d}.wav",
                "text": text, "duration": round(end - start, 3), "start": round(start, 3), "end": round(end, 3),
                "language": langs[k] if langs else self.lang.code, "source": rec.get("source"),
                "source_id": rec["id"], **({"translation": rec["translation"]} if rec.get("translation") else {}),
                **extra}

    def _align_mms(self, rec: dict, aligner, cfg: dict) -> list[dict]:
        from .align import pad_spans

        wav = audio.load(self.root / rec["audio_filepath"], aligner.sample_rate)
        spans = aligner.align(wav, rec["lines"], self.lang)
        spans = pad_spans(spans, len(wav) / aligner.sample_rate, cfg.get("pad", 0.15))
        rows = []
        for k, (line, sp) in enumerate(zip(rec["lines"], spans)):
            if sp is None:
                continue
            row = self._clip_row(rec, k, line, sp.start, sp.end, score=round(sp.score, 4))
            a, b = int(sp.start * self.sr), int(sp.end * self.sr)
            audio.save(self.root / row["audio_filepath"], wav[a:b], self.sr)
            rows.append(row)
        return rows

    def _cut_segments(self, rec: dict) -> list[dict]:
        wav = audio.load(self.root / rec["audio_filepath"], self.sr)
        rows = []
        for k, seg in enumerate(rec["segments"]):
            row = self._clip_row(rec, k, seg["text"], seg["start"], seg["end"])
            audio.save(self.root / row["audio_filepath"], wav[int(seg["start"] * self.sr):int(seg["end"] * self.sr)],
                       self.sr)
            rows.append(row)
        return rows

    def _align_fairseq(self, rec: dict, cfg: dict) -> list[dict]:
        from .align import align_fairseq

        folder = self.path(f"clips/{rec['id']}")
        folder.mkdir(parents=True, exist_ok=True)
        text_path = folder / "text.txt"
        text_path.write_text("\n".join(rec["lines"]) + "\n", encoding="utf-8")
        segs = align_fairseq(self.root / rec["audio_filepath"], text_path, folder / "fairseq", self.lang, cfg)
        wav = audio.load(self.root / rec["audio_filepath"], self.sr)
        rows = []
        for k, seg in enumerate(segs):
            row = self._clip_row(rec, k, seg["text"], seg["start"], seg["end"])
            audio.save(self.root / row["audio_filepath"], wav[int(seg["start"] * self.sr):int(seg["end"] * self.sr)],
                       self.sr)
            rows.append(row)
        return rows

    def segment(self) -> None:
        from .segment import split_on_silence

        cfg = self.r.segment
        records = [r for r in manifest.read(self.path("prepared.jsonl")) if not r.get("lines") and not r.get("segments")]
        out = []
        for rec in tqdm(records, desc="segment"):
            wav = audio.load(self.root / rec["audio_filepath"], self.sr)
            for k, (s, e) in enumerate(split_on_silence(wav, self.sr, **cfg)):
                row = self._clip_row(rec, k, None, s, e)
                dest = self.root / row["audio_filepath"]
                if not dest.exists():
                    audio.save(dest, wav[int(s * self.sr):int(e * self.sr)], self.sr)
                out.append(row)
        manifest.write(self.path("segmented.jsonl"), out)
        log.info("%d clips, %.2f h", len(out), manifest.total_hours(out))

    def transcribe(self) -> None:
        from .transcribe import ASR

        cfg = self.r.transcribe
        model = cfg.get("model") or self.lang.asr_model
        if not model:
            raise ValueError("transcribe needs `transcribe.model` in the recipe or `asr_model` in the language file")
        rows = manifest.read(self.path("segmented.jsonl"))
        todo = [r for r in rows if not r.get("text")]
        asr = ASR(model, cfg.get("target_lang"), cfg.get("device"), cfg.get("batch_size", 8))
        step = 64
        for i in tqdm(range(0, len(todo), step), desc="transcribe"):
            batch = todo[i:i + step]
            texts = asr([audio.load(self.root / r["audio_filepath"], self.sr) for r in batch], self.sr)
            for r, t in zip(batch, texts):
                r["text"] = t
            manifest.write(self.path("segmented.jsonl"), rows)      # save progress

    def filter(self) -> None:
        cfg = {"min_duration": 0.5, "max_duration": 30.0, "min_score": 0.2, "max_foreign_ratio": None,
               "min_chars_per_second": 3.0, "max_chars_per_second": None, "languages": [self.lang.code], **self.r.filter}
        rows = manifest.read(self.path("aligned.jsonl")) + manifest.read(self.path("segmented.jsonl"))
        kept, dropped = [], Counter()
        for r in rows:
            reason = self._reject(r, cfg)
            if reason:
                dropped[reason] += 1
            else:
                kept.append(r)
        manifest.write(self.path("final.jsonl"), kept)
        log.info("kept %d clips (%.2f h), dropped %s", len(kept), manifest.total_hours(kept),
                 dict(dropped) or "none")

    def _reject(self, r: dict, cfg: dict) -> str | None:
        text, d = (r.get("text") or "").strip(), r["duration"]
        if not text:
            return "no_text"
        if cfg["languages"] and r.get("language") not in cfg["languages"]:
            return "other_language"
        if d < cfg["min_duration"]:
            return "too_short"
        if d > cfg["max_duration"]:
            return "too_long"
        if cfg["min_score"] is not None and r.get("score") is not None and r["score"] < cfg["min_score"]:
            return "low_score"
        if cfg["min_chars_per_second"] and len(text) / d < cfg["min_chars_per_second"]:
            return "too_little_text"            # music or noise labelled with a stray letter
        if cfg["max_chars_per_second"] and len(text) / d > cfg["max_chars_per_second"]:
            return "too_fast"
        if cfg["max_foreign_ratio"] is not None and foreign_ratio(text, self.lang) > cfg["max_foreign_ratio"]:
            return "foreign_text"
        return None

    def export(self) -> None:
        from .export import export

        rows = manifest.read(self.path("final.jsonl"))
        export(rows, self.root, self.r.export, self.lang.code)
        log.info("exported %d clips (%.2f h)", len(rows), manifest.total_hours(rows))

    # ---- quality check -----------------------------------------------------------------------

    def check(self, sample: int = 50, model: str | None = None, target_lang: str | None = None, seed: int = 0) -> dict:
        """Transcribe a random sample of final clips and compare with their text (CER)."""
        import random

        from .transcribe import ASR, cer

        rows = manifest.read(self.path("final.jsonl"))
        random.Random(seed).shuffle(rows)
        rows = rows[:sample]
        model = model or self.r.transcribe.get("model") or self.lang.asr_model or "facebook/mms-1b-all"
        if target_lang is None and model == "facebook/mms-1b-all":
            target_lang = self.lang.mms_code or self.lang.code
        asr = ASR(model, target_lang)
        hyps = asr([audio.load(self.root / r["audio_filepath"], self.sr) for r in rows], self.sr)
        results = [{"id": r["id"], "text": r["text"], "asr": h, "cer": round(cer(r["text"], h), 4),
                    "score": r.get("score")} for r, h in zip(rows, hyps)]
        manifest.write(self.path("check.jsonl"), results)
        cers = sorted(x["cer"] for x in results)
        summary = {"clips": len(results), "model": model, "target_lang": target_lang,
                   "mean_cer": round(sum(cers) / max(len(cers), 1), 4),
                   "median_cer": cers[len(cers) // 2] if cers else None}
        log.info("check: %s", summary)
        return summary

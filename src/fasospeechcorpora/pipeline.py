"""Run a recipe step by step. Every step reads and writes a JSONL manifest in the output folder,
so any step can be re-run alone, and finished work is skipped on the next run.

  fetch       -> raw/ + raw.jsonl            download audio (and text) from the source
  prepare     -> wav/ + prepared.jsonl       decode to mono 16 kHz wav
  enhance     -> voice/ + prepared.jsonl     optional: keep only the voice (removes background music)
  align       -> clips/ + aligned.jsonl      known text: one clip per sentence (forced alignment)
  segment     -> clips/ + segmented.jsonl    no text: one clip per pause-delimited utterance
  trim        -> trimmed/ + both manifests   cut each clip to its speech (no music or long silence at the ends)
  verify      -> both manifests              CER of every clip against one or more ASR models
  transcribe  -> segmented.jsonl             no text: pseudo-labels from an ASR model
  filter      -> final.jsonl                 drop bad clips, print a summary
  speakers    -> final.jsonl + speakers/     group clips by speaker, suggest male/female voices
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
STEPS = ["fetch", "prepare", "enhance", "align", "segment", "trim", "transcribe", "verify", "filter", "speakers", "export"]


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
                **rec.get("meta", {}), **extra}

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
            end = min(seg["end"], len(wav) / self.sr)
            row = self._clip_row(rec, k, seg["text"], seg["start"], end)
            audio.save(self.root / row["audio_filepath"], wav[int(seg["start"] * self.sr):int(end * self.sr)], self.sr)
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

    def trim(self) -> None:
        from .enhance import VoiceExtractor
        from .trim import speech_bounds

        cfg = {"margin": 0.2, "model": "htdemucs", "device": None, **self.r.trim}
        extractor = None
        for name in ("aligned.jsonl", "segmented.jsonl"):
            rows = manifest.read(self.path(name))
            todo = [r for r in rows if not r.get("trimmed")]
            for r in tqdm(todo, desc=f"trim {name}"):
                extractor = extractor or VoiceExtractor(cfg["model"], cfg["device"])
                wav = audio.load(self.root / r["audio_filepath"], self.sr)
                voice, music = extractor.split(wav, self.sr)
                b = speech_bounds(voice, music, self.sr)
                r["trimmed"] = True
                if b is None:
                    r["no_voice"] = True
                    continue
                a = max(0, int((b.start - cfg["margin"]) * self.sr))
                z = min(len(wav), int((b.end + cfg["margin"]) * self.sr))
                path, vpath = f"trimmed/{r['id']}.wav", f"trimmed_voice/{r['id']}.wav"
                audio.save(self.root / path, wav[a:z], self.sr)
                audio.save(self.root / vpath, voice[a:z], self.sr)
                r.update({"untrimmed_audio_filepath": r["audio_filepath"], "audio_filepath": path,
                          "voice_filepath": vpath, "duration": round((z - a) / self.sr, 3),
                          "start": round(r.get("start", 0.0) + a / self.sr, 3),
                          "end": round(r.get("start", 0.0) + z / self.sr, 3),
                          "lead_music": round(b.lead_music, 2), "trail_music": round(b.trail_music, 2),
                          "music_under_voice_db": round(b.music_under_voice_db, 1)})
            manifest.write(self.path(name), rows)
            if todo:
                cut = sum(1 for r in todo if not r.get("no_voice"))
                log.info("%s: %d clips trimmed, %d with no voice found", name, cut, len(todo) - cut)

    def transcribe(self) -> None:
        from .transcribe import ASR

        cfg = self.r.transcribe
        model = cfg.get("model") or self.lang.asr_model
        if not model:
            raise ValueError("transcribe needs `transcribe.model` in the recipe or `asr_model` in the language file")
        rows = manifest.read(self.path("segmented.jsonl"))
        todo = [r for r in rows if not r.get("text")]
        asr = ASR(model, cfg.get("target_lang"), cfg.get("device"), cfg.get("batch_size", 8),
                  cfg.get("max_batch_seconds", 60.0))
        step = 64
        for i in tqdm(range(0, len(todo), step), desc="transcribe"):
            batch = todo[i:i + step]
            texts = asr([audio.load(self.root / r["audio_filepath"], self.sr) for r in batch], self.sr)
            for r, t in zip(batch, texts):
                r["text"] = t
            manifest.write(self.path("segmented.jsonl"), rows)      # save progress

    def verify(self) -> None:
        """CER of every clip with text, for each model in `verify.models`; `cer` is the best of them.
        Models run one at a time and are freed before the next loads; scores are saved after each model."""
        import gc

        from .transcribe import ASR, cer

        models = self.r.verify.get("models") or [{"model": "facebook/mms-1b-all",
                                                    "target_lang": self.lang.mms_code or self.lang.code}]
        names = ("aligned.jsonl", "segmented.jsonl")
        for m in models:
            key = "cer_" + m["model"].split("/")[-1]
            asr = None
            for name in names:
                rows = manifest.read(self.path(name))
                todo = [r for r in rows if r.get("text") and key not in r and not r.get("no_voice")]
                if not todo:
                    continue
                asr = asr or ASR(m["model"], m.get("target_lang"), m.get("device"), m.get("batch_size", 8),
                                 m.get("max_batch_seconds", 60.0))
                for i in tqdm(range(0, len(todo), 64), desc=f"verify {key}"):
                    batch = todo[i:i + 64]
                    hyps = asr([audio.load(self.root / r["audio_filepath"], self.sr) for r in batch], self.sr)
                    for r, h in zip(batch, hyps):
                        r[key] = round(cer(r["text"], h), 4)
                    manifest.write(self.path(name), rows)          # save progress
            del asr
            gc.collect()
            try:
                import torch
                torch.cuda.empty_cache()
            except ImportError:
                pass
        for name in names:
            rows = manifest.read(self.path(name))
            for r in rows:
                scores = [v for k, v in r.items() if k.startswith("cer_")]
                if scores:
                    r["cer"] = min(scores)
            manifest.write(self.path(name), rows)

    def filter(self) -> None:
        cfg = {"min_duration": 0.5, "max_duration": 30.0, "min_score": 0.2, "max_foreign_ratio": None,
               "min_chars_per_second": 3.0, "max_chars_per_second": None,
               "max_music_under_voice_db": None, "max_cer": None, "clean_text": False, "no_digits": False,
               "languages": [self.lang.code], **self.r.filter}
        rows = manifest.read(self.path("aligned.jsonl")) + manifest.read(self.path("segmented.jsonl"))
        if cfg["clean_text"]:
            from .text import clean_text
            for r in rows:
                if r.get("text"):
                    r["raw_text"], r["text"] = r["text"], clean_text(r["text"])
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
        if r.get("no_voice"):
            return "no_voice"
        if cfg["languages"] and r.get("language") not in cfg["languages"]:
            return "other_language"           # before the CER check, so translation lines are counted here
        if cfg["no_digits"] and any(c.isdigit() for c in text):
            return "digits"
        if cfg["max_cer"] is not None and r.get("cer") is not None and r["cer"] > cfg["max_cer"]:
            return "high_cer"
        if cfg["max_music_under_voice_db"] is not None and r.get("music_under_voice_db", -99) > cfg["max_music_under_voice_db"]:
            return "music_under_voice"
        if d <cfg["min_duration"]:
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

    def speakers(self) -> None:
        """Label speakers in final.jsonl. Writes speakers/summary.json and a few example clips per group
        to listen to. Put corrections in speakers/labels.yaml ({group: {speaker_id: 1, voice: male}})
        and run the step again to apply them."""
        import shutil

        import numpy as np
        import yaml

        from .speakers import SpeakerEmbedder, cluster, median_f0

        cfg = {"model": "microsoft/wavlm-base-plus-sv", "threshold": 0.75, "male_below_hz": 165, **self.r.speakers}
        rows = manifest.read(self.path("final.jsonl"))
        if not rows:
            return
        out = self.path("speakers")
        out.mkdir(exist_ok=True)
        if not all("speaker_group" in r for r in rows):
            clips = [audio.load(self.root / r.get("voice_filepath", r["audio_filepath"]), self.sr) for r in rows]
            emb = SpeakerEmbedder(cfg["model"])(clips, self.sr)
            groups = cluster(emb, cfg["threshold"])
            for r, g, c in zip(rows, groups, clips):
                r["speaker_group"], r["f0"] = int(g), median_f0(c, self.sr)
        summary = {}
        for g in sorted({r["speaker_group"] for r in rows}):
            members = [r for r in rows if r["speaker_group"] == g]
            f0 = [r["f0"] for r in members if r.get("f0")]
            med = float(np.median(f0)) if f0 else None
            examples = sorted(members, key=lambda r: -r["duration"])[:3]
            for k, r in enumerate(examples):
                shutil.copy2(self.root / r["audio_filepath"], out / f"group{g}_example{k + 1}.wav")
            summary[g] = {"clips": len(members), "hours": round(sum(r["duration"] for r in members) / 3600, 3),
                          "median_f0_hz": round(med, 1) if med else None,
                          "suggested_voice": None if med is None else ("male" if med < cfg["male_below_hz"] else "female"),
                          "sources": sorted({str(r.get("source")) for r in members})[:5],
                          "examples": [f"group{g}_example{k + 1}.wav" for k in range(len(examples))]}
        (out / "summary.json").write_text(__import__("json").dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        labels_file = out / "labels.yaml"
        labels = yaml.safe_load(labels_file.read_text(encoding="utf-8")) if labels_file.exists() else {}
        for r in rows:
            lab = (labels or {}).get(r["speaker_group"], {})
            r["speaker_id"] = int(lab.get("speaker_id", r["speaker_group"] + 1))
            r["voice"] = lab.get("voice", summary[r["speaker_group"]]["suggested_voice"])
        manifest.write(self.path("final.jsonl"), rows)
        log.info("%d speaker groups; listen to speakers/*.wav and edit speakers/labels.yaml to confirm", len(summary))

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

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
  detect_cs   -> both manifests              optional: language of every token (code-switching)
  filter      -> final.jsonl (+ views)       drop bad clips, print a summary
  speakers    -> final.jsonl + speakers/     group clips by speaker, suggest male/female voices
  export      -> ljspeech/, hf/              training formats, optional Hub upload
"""
from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from tqdm import tqdm

from . import audio, manifest, nonspeech
from .config import Recipe
from .text import foreign_ratio

log = logging.getLogger("fasospeechcorpora")
STEPS = ["fetch", "prepare", "enhance", "align", "segment", "trim", "transcribe", "verify", "detect_cs", "filter",
         "speakers", "export"]


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
                          "trim_start": round(a / self.sr, 3), "trim_end": round(z / self.sr, 3),
                          "untrimmed_duration": round(len(wav) / self.sr, 3),
                          "lead_music": round(b.lead_music, 2), "trail_music": round(b.trail_music, 2),
                          "music_under_voice_db": round(b.music_under_voice_db, 1)})
            self._backfill_trim(rows)
            for r in rows:
                if r.get("trimmed"):
                    nonspeech.annotate(r)
            manifest.write(self.path(name), rows)
            if todo:
                cut = sum(1 for r in todo if not r.get("no_voice"))
                log.info("%s: %d clips trimmed, %d with no voice found", name, cut, len(todo) - cut)

    def _backfill_trim(self, rows: list[dict]) -> None:
        """Clips trimmed before trim_start was recorded: find the cut by matching the audio."""
        todo = [r for r in rows if r.get("trimmed") and not r.get("no_voice") and r.get("trim_start") is None
                and r.get("untrimmed_audio_filepath")]
        for r in tqdm(todo, desc="find trim offsets"):
            whole = audio.load(self.root / r["untrimmed_audio_filepath"], self.sr)
            part = audio.load(self.root / r["audio_filepath"], self.sr)
            a = nonspeech.locate(part, whole)
            if a is None:
                log.warning("trim offset not found for %s", r["id"])
                continue
            r.update({"trim_start": round(a / self.sr, 3), "trim_end": round((a + len(part)) / self.sr, 3),
                      "untrimmed_duration": round(len(whole) / self.sr, 3)})

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
        Models run one at a time and are freed before the next loads; scores are saved after each model.
        A model can be limited to some clip languages (`languages: [fra]`) and named (`name: mms-fra`),
        e.g. to score translation lines with a French adapter; its scores go in cer_<name>."""
        import gc

        from .transcribe import ASR, cer

        models = self.r.verify.get("models") or [{"model": "facebook/mms-1b-all",
                                                    "target_lang": self.lang.mms_code or self.lang.code}]
        names = ("aligned.jsonl", "segmented.jsonl")
        for m in models:
            key = "cer_" + m.get("name", m["model"].split("/")[-1])
            langs = m.get("languages")
            asr = None
            for name in names:
                rows = manifest.read(self.path(name))
                todo = [r for r in rows if r.get("text") and key not in r and not r.get("no_voice")
                        and (not langs or r.get("language") in langs)]
                if not todo:
                    continue
                asr = asr or ASR(m["model"], m.get("target_lang"), m.get("device"), m.get("batch_size", 8),
                                 m.get("max_batch_seconds", 60.0))
                for i in tqdm(range(0, len(todo), 64), desc=f"verify {key}"):
                    batch = todo[i:i + 64]
                    hyps = asr([audio.load(self.root / r["audio_filepath"], self.sr) for r in batch], self.sr)
                    for r, h in zip(batch, hyps):
                        r[key] = round(cer(r["text"], h), 4)
                        r["hyp_" + key[4:]] = h        # kept so scores can be recomputed without the model
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

    def detect_cs(self) -> None:
        """Label the language of every token (see codeswitch.py), tag French spans in `text_tagged`,
        and score code-switched clips on their matrix-language words (`cer_matrix`). With `audio: true`,
        MMS-LID checks each clip of at least `audio_min_seconds`; a clip whose audio and text disagree
        gets `cs_review: true`. Tokens labelled as embedded inside matrix-language lines are listed in
        codeswitch/candidates.tsv, and lexicon words that are also common French words (possible
        insertions the lexicon hides) in codeswitch/lexicon_overlap.tsv, to review and grow the loan list."""
        from . import codeswitch as cs

        cfg = {"embedded": ["fra"], "min_zipf": 3.0, "lexicon_min_count": 3, "lexicon_from": [], "loans": None,
               "glotlid": True, "audio": False, "audio_model": "facebook/mms-lid-256", "audio_margin": 4.0,
               "audio_min_seconds": 2.0, "device": None, **self.r.detect_cs}
        names = ("aligned.jsonl", "segmented.jsonl")
        tables = {n: manifest.read(self.path(n)) for n in names}
        rows = [r for n in names for r in tables[n] if r.get("text")]
        mat, emb = self.lang.code, tuple(cfg["embedded"])
        texts = [r["text"] for r in rows if r.get("language", mat) == mat]
        for p in cfg["lexicon_from"]:
            texts += [r["text"] for r in manifest.read(p) if r.get("text") and r.get("language", mat) == mat]
        lexicon = cs.build_lexicon(texts, cfg["lexicon_min_count"])
        label = cs.Labeller(mat, lexicon, emb, cs.read_loans(cfg["loans"]), cfg["min_zipf"])
        # frequent French words in Mooré text land in the lexicon and stop counting as French: list them
        overlap = sorted((w for w in lexicon if len(w) >= 4 and any(label.zipf(w, e) >= 4.5 for e in emb)),
                         key=lambda w: -max(label.zipf(w, e) for e in emb))
        glot = _glotlid() if cfg["glotlid"] else None
        found = Counter()
        for r in rows:
            labels = label(r["text"], r.get("language"))
            r.update(cs.metrics(r["text"], labels, mat))
            r["text_tagged"] = cs.tag_text(r["text"], labels, emb)
            r["lang_source"] = "markup" if r.get("language") in emb else "lexicon"
            if glot:
                r["lid_text"], r["lid_text_p"] = glot(r["text"])
            r.pop("cer_matrix", None)
            if r["cs_type"] != "none":
                scores = [cs.span_cer(r["text"], h, labels, r["matrix_lang"]) for k, h in r.items()
                          if k.startswith("hyp_") and h is not None]
                scores = [x for x in scores if x is not None]
                r["cer_matrix"] = min(scores) if scores else None
            if r.get("language", mat) == mat:
                found.update(t.lower() for t, lab in zip(r["text"].split(), labels) if lab in emb)
        if cfg["audio"]:
            self._audio_lid(rows, cfg, mat, emb[0])
        for n in names:
            manifest.write(self.path(n), tables[n])
        out = self.path("codeswitch")
        out.mkdir(exist_ok=True)
        (out / "candidates.tsv").write_text("token\tcount\n" + "".join(f"{t}\t{c}\n" for t, c in found.most_common()),
                                            encoding="utf-8")
        (out / "lexicon_overlap.tsv").write_text("word\n" + "".join(f"{w}\n" for w in overlap), encoding="utf-8")
        kinds = Counter(r["cs_type"] for r in rows if r.get("language", mat) == mat)
        log.info("%s lines: %s; %d embedded-language tokens (%d distinct), see codeswitch/candidates.tsv",
                 mat, dict(kinds), sum(found.values()), len(found))

    def _audio_lid(self, rows: list[dict], cfg: dict, mat: str, emb: str) -> None:
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

        device = cfg["device"] or ("cuda" if torch.cuda.is_available() else "cpu")
        fe = AutoFeatureExtractor.from_pretrained(cfg["audio_model"])
        model = AutoModelForAudioClassification.from_pretrained(cfg["audio_model"]).to(device).eval()
        ids = {v: int(k) for k, v in model.config.id2label.items()}       # label2id can be missing
        todo = [r for r in rows if r["duration"] >= cfg["audio_min_seconds"] and not r.get("no_voice")
                and "lid_audio_margin" not in r]
        for r in tqdm(todo, desc="audio LID"):
            wav = audio.load(self.root / r["audio_filepath"], 16_000)
            x = fe(wav, sampling_rate=16_000, return_tensors="pt").to(device)
            with torch.inference_mode():
                logits = model(**x).logits[0].float().cpu()
            r["lid_audio_margin"] = round(float(logits[ids[emb]] - logits[ids[mat]]), 3)
        for r in rows:
            m = r.get("lid_audio_margin")
            if m is None:
                continue
            r["lid_audio"] = emb if m > cfg["audio_margin"] else mat if m < 0 else "unsure"
            text_lang = r["matrix_lang"] if r["cs_type"] == "none" else None
            r["cs_review"] = text_lang is not None and r["lid_audio"] not in ("unsure", text_lang)

    VIEWS = ("variants", "negatives", "tagged")

    def filter(self) -> None:
        """Keep the good clips in final.jsonl. Extra views, each written to final_<name>.jsonl:

          variants:  {asr: {max_music_under_voice_db: null}, fra: {languages: [fra], max_cer: null}}
                     the same rules with some overrides
          negatives: {of: asr, max_share: 0.1, min_len: 1.0}   -> final_asr_negatives.jsonl
                     music-only clips with empty text, at most max_share of the `of` view
          tagged:    {of: asr, min_music: 0.5}                -> final_asr_tagged.jsonl
                     the `of` view on untrimmed audio, with <MUSIC> on edges that had music
        """
        cfg = {"min_duration": 0.5, "max_duration": 30.0, "min_score": 0.2, "max_foreign_ratio": None,
               "min_chars_per_second": 3.0, "max_chars_per_second": None,
               "max_music_under_voice_db": None, "max_cer": None, "clean_text": False, "no_digits": False,
               "languages": [self.lang.code], **{k: v for k, v in self.r.filter.items() if k not in self.VIEWS}}
        rows = manifest.read(self.path("aligned.jsonl")) + manifest.read(self.path("segmented.jsonl"))
        if cfg["clean_text"]:
            from .text import clean_text
            for r in rows:
                if r.get("text"):
                    r["raw_text"], r["text"] = r["text"], clean_text(r["text"])
        for r in rows:
            r.update(self.r.metadata)
            if "segment_type" not in r:
                nonspeech.annotate(r)
        views = {None: self._keep(rows, cfg, "final.jsonl")}
        for name, over in (self.r.filter.get("variants") or {}).items():
            views[name] = self._keep(rows, {**cfg, **(over or {})}, f"final_{name}.jsonl")
        neg = self.r.filter.get("negatives")
        if neg:
            neg = {"of": None, "max_share": 0.1, "min_len": 1.0, "seed": 0, **neg}
            out = nonspeech.negatives(rows, views[neg["of"]], self.root, self.sr, neg["min_len"],
                                      neg["max_share"], neg["seed"])
            name = f"{neg['of']}_negatives" if neg["of"] else "negatives"
            manifest.write(self.path(f"final_{name}.jsonl"), out)
            log.info("%s: %d music-only clips (%.2f h)", name, len(out), manifest.total_hours(out))
        tag = self.r.filter.get("tagged")
        if tag:
            tag = {"of": None, "min_music": 0.5, **tag}
            out = nonspeech.tagged(views[tag["of"]], tag["min_music"])
            name = f"{tag['of']}_tagged" if tag["of"] else "tagged"
            manifest.write(self.path(f"final_{name}.jsonl"), out)
            log.info("%s: %d clips, %d with a <MUSIC> tag", name, len(out),
                     sum("<MUSIC>" in r["text"] for r in out))

    def _keep(self, rows: list[dict], cfg: dict, name: str) -> list[dict]:
        kept, dropped = [], Counter()
        for r in rows:
            reason = self._reject(r, cfg)
            if reason:
                dropped[reason] += 1
            else:
                kept.append(r)
        manifest.write(self.path(name), kept)
        log.info("%s: kept %d clips (%.2f h), dropped %s", name, len(kept), manifest.total_hours(kept),
                 dict(dropped) or "none")
        return kept

    @staticmethod
    def _in_languages(r: dict, languages: list[str]) -> bool:
        """A clip counts as in `languages` when its language is, or when detect_cs found it mixes one in."""
        if r.get("language") in languages:
            return True
        return r.get("cs_type") not in (None, "none") and r.get("matrix_lang") in languages

    def _reject(self, r: dict, cfg: dict) -> str | None:
        text, d = (r.get("text") or "").strip(), r["duration"]
        if not text:
            return "no_text"
        if r.get("no_voice"):
            return "no_voice"
        if cfg["languages"] and not self._in_languages(r, cfg["languages"]):
            return "other_language"           # before the CER check, so translation lines are counted here
        if cfg["no_digits"] and any(c.isdigit() for c in text):
            return "digits"
        # code-switched clips are scored on their matrix-language words only (see codeswitch.span_cer)
        c = r.get("cer_matrix") if r.get("cs_type") not in (None, "none") and r.get("cer_matrix") is not None \
            else r.get("cer")
        if cfg["max_cer"] is not None and c is not None and c > cfg["max_cer"]:
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
        """Label speakers in final.jsonl. Clips are grouped chapter by chapter (see speakers.py).
        Writes speakers/summary.json and a few example clips per group to listen to. Put corrections
        in speakers/labels.yaml ({group: {speaker_id: 1, voice: male}}) and run the step again to
        apply them. The grouping is redone when the model, threshold or units change."""
        import json
        import shutil

        import numpy as np
        import yaml

        from . import speakers as sp

        cfg = {"model": "ecapa", "threshold": 0.55, "by_chapter": True, "min_unit_clips": 3, "device": None,
               "male_below_hz": 165, **self.r.speakers}
        rows = manifest.read(self.path("final.jsonl"))
        if not rows:
            return
        out = self.path("speakers")
        out.mkdir(exist_ok=True)
        method = {k: cfg[k] for k in ("model", "threshold", "by_chapter", "min_unit_clips")}
        method_file = out / "method.json"
        done = method_file.exists() and json.loads(method_file.read_text(encoding="utf-8")) == method
        if not (done and all("speaker_group" in r for r in rows)):
            clips = [audio.load(self.root / r.get("voice_filepath", r["audio_filepath"]), self.sr) for r in rows]
            if cfg["model"] == "ecapa":
                embedder = sp.EcapaEmbedder(device=cfg["device"], savedir=str(out / "model"))
            else:
                embedder = sp.SpeakerEmbedder(cfg["model"], cfg["device"])
            emb = embedder(clips, self.sr)
            units = sp.chapter_units(rows, cfg["min_unit_clips"]) if cfg["by_chapter"] else None
            groups = sp.cluster(emb, units, cfg["threshold"])
            for r, g, c in zip(rows, groups, clips):
                r["speaker_group"] = int(g)
                if r.get("f0") is None:
                    r["f0"] = sp.median_f0(c, self.sr)
            for old in out.glob("group*_example*.wav"):
                old.unlink()
            method_file.write_text(json.dumps(method), encoding="utf-8")
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
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        labels_file = out / "labels.yaml"
        labels = yaml.safe_load(labels_file.read_text(encoding="utf-8")) if labels_file.exists() else {}
        for r in rows:
            lab = (labels or {}).get(r["speaker_group"], {})
            r["speaker_id"] = int(lab.get("speaker_id", r["speaker_group"] + 1))
            r["voice"] = lab.get("voice", summary[r["speaker_group"]]["suggested_voice"])
        manifest.write(self.path("final.jsonl"), rows)
        self._label_views(rows, sp.chapter_units(rows, cfg["min_unit_clips"]))
        log.info("%d speaker groups; listen to speakers/*.wav and edit speakers/labels.yaml to confirm", len(summary))

    def _label_views(self, rows: list[dict], units: list[str]) -> None:
        """Give the filter's extra views the speaker of the same clip in final.jsonl, or else the
        speaker of most clips in the same chapter; music-only clips get no speaker."""
        from . import speakers as sp

        keys = ("speaker_group", "speaker_id", "voice")
        by_id = {r["id"]: r for r in rows}
        votes: dict[str, Counter] = {}
        for r, u in zip(rows, units):
            votes.setdefault(u, Counter())[r["speaker_group"]] += 1
        info = {r["speaker_group"]: {k: r[k] for k in keys} for r in rows}
        for view in sorted(self.root.glob("final_*.jsonl")):
            vrows = manifest.read(view)
            vunits = sp.chapter_units(vrows, 1)
            for r, u in zip(vrows, vunits):
                if r.get("is_nonspeech"):
                    r.update(dict.fromkeys(keys))
                elif r["id"] in by_id:
                    r.update({k: by_id[r["id"]][k] for k in keys})
                else:
                    coarse = "|".join(u.split("|")[:3])
                    vote = votes.get(u) or sum((c for k, c in votes.items() if k.startswith(coarse)), Counter())
                    r.update(info[vote.most_common(1)[0][0]] if vote else dict.fromkeys(keys))
            manifest.write(view, vrows)

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


def _glotlid():
    """GlotLID text LID: returns (label, probability). Calls the fasttext core directly
    because fasttext's predict() breaks on NumPy 2."""
    import fasttext
    from huggingface_hub import hf_hub_download

    model = fasttext.load_model(hf_hub_download("cis-lmu/glotlid", "model.bin"))

    def predict(text: str) -> tuple[str, float]:
        p, lab = model.f.predict(text.replace("\n", " ") + "\n", 1, 0.0, "strict")[0]
        return lab.replace("__label__", ""), round(float(p), 3)
    return predict

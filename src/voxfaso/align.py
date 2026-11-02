"""Forced alignment: find where each line of a known text is spoken in a long recording.

Backends
  mms      (default) Meta's MMS aligner through torchaudio, with the pure-Python `uroman`
           romanizer. Works for any language written in (or romanizable to) Latin letters.
           pip install "voxfaso[align]"; CPU or GPU, Linux, macOS, Windows.
  fairseq  (legacy) the original pipeline used to build MooreSpeechCorpora v1: fairseq's
           `examples.mms.data_prep.align_and_segment` + the Perl uroman. Linux only.
           Needs `align.fairseq_dir` and `align.uroman_dir` in the recipe.

Note: the MMS aligner weights are licensed CC-BY-NC 4.0.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import Language


@dataclass
class Span:
    start: float      # seconds
    end: float
    score: float      # mean probability of the line's characters (0 to 1)


class MMSAligner:
    def __init__(self, device: str | None = None, window: float = 30.0, context: float = 2.0, use_star: bool = True):
        import torch
        import torchaudio
        import uroman

        self.torch, self.F = torch, torchaudio.functional
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        bundle = torchaudio.pipelines.MMS_FA
        self.sample_rate = bundle.sample_rate
        self.model = bundle.get_model(with_star=use_star).to(self.device).eval()
        self.dictionary = bundle.get_dict(star="*" if use_star else None)
        self.use_star = use_star
        self.window, self.context = window, context
        self.uroman = uroman.Uroman()

    def romanize(self, line: str, lang: Language) -> str:
        roman = self.uroman.romanize_string(line, lcode=lang.uroman_code or lang.code).lower()
        roman = roman.replace("’", "'").replace("`", "'")
        roman = re.sub(r"[^a-z' ]", " ", roman)
        return re.sub(r"\s+", " ", roman).strip()

    def emissions(self, wav: np.ndarray):
        """Log-probabilities for the whole file, computed in overlapping windows to bound memory."""
        torch = self.torch
        sr, n = self.sample_rate, len(wav)
        win, ctx = int(self.window * sr), int(self.context * sr)
        chunks = []
        with torch.inference_mode():
            for s in range(0, n, win):
                e = min(s + win, n)
                a, b = max(0, s - ctx), min(n, e + ctx)
                x = torch.from_numpy(wav[a:b]).float().unsqueeze(0).to(self.device)
                em, _ = self.model(x)
                em = em[0]
                fps = em.shape[0] / (b - a)                     # frames per sample in this chunk
                lo, hi = round((s - a) * fps), round((e - a) * fps)
                chunks.append(em[lo:hi])
        emission = torch.cat(chunks)
        return torch.log_softmax(emission, dim=-1), n / emission.shape[0]

    def align(self, wav: np.ndarray, lines: list[str], lang: Language) -> list[Span | None]:
        torch = self.torch
        roman = [self.romanize(line, lang) for line in lines]
        tokens, owner = [], []                         # owner[i] = line index of token i
        for i, r in enumerate(roman):
            ids = [self.dictionary[c] for c in r.replace(" ", "") if c in self.dictionary]
            tokens += ids
            owner += [i] * len(ids)
        if not tokens:
            return [None] * len(lines)
        log_probs, samples_per_frame = self.emissions(wav)
        if self.use_star:                              # a leading star absorbs unscripted intros
            tokens = [self.dictionary["*"]] + tokens
            owner = [-1] + owner
        targets = torch.tensor([tokens], dtype=torch.int32, device=log_probs.device)
        alignment, scores = self.F.forced_align(log_probs.unsqueeze(0), targets, blank=0)
        spans = self.F.merge_tokens(alignment[0], scores[0].exp())
        per_line: dict[int, list] = {}
        for k, sp in enumerate(spans):
            line = owner[k]
            if line >= 0:
                per_line.setdefault(line, []).append(sp)
        to_sec = samples_per_frame / self.sample_rate
        out: list[Span | None] = []
        for i in range(len(lines)):
            sps = per_line.get(i)
            if not sps:
                out.append(None)
                continue
            out.append(Span(sps[0].start * to_sec, sps[-1].end * to_sec,
                            float(np.mean([s.score for s in sps]))))
        return out


def pad_spans(spans: list[Span | None], total: float, pad: float = 0.15) -> list[Span | None]:
    """Widen each span to the midpoint of the silence before/after it, so words are not clipped."""
    kept = [s for s in spans if s]
    for prev, cur in zip([None] + kept[:-1], kept):
        lo = cur.start - pad if prev is None else (prev.end + cur.start) / 2
        cur.start = max(0.0, max(lo, cur.start - 1.0))
    for cur, nxt in zip(kept, kept[1:] + [None]):
        hi = cur.end + pad if nxt is None else (cur.end + nxt.start) / 2
        cur.end = min(total, min(hi, cur.end + 1.0))
    return spans


def align_fairseq(wav_path: Path, text_path: Path, out_dir: Path, lang: Language, cfg: dict) -> list[dict]:
    """Legacy backend: run fairseq's MMS align_and_segment and read back its manifest."""
    fairseq_dir, uroman_dir = Path(cfg["fairseq_dir"]).resolve(), Path(cfg["uroman_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "examples.mms.data_prep.align_and_segment",
           "--audio_filepath", str(wav_path.resolve()), "--text_filepath", str(text_path.resolve()),
           "--lang", lang.mms_code or lang.code, "--outdir", str(out_dir.resolve()), "--uroman", str(uroman_dir)]
    subprocess.run(cmd, check=True, cwd=fairseq_dir)
    rows = []
    for line in (out_dir / "manifest.json").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        rows.append({"start": e["audio_start_sec"], "end": e["audio_start_sec"] + e["duration"],
                     "text": e["text"], "clip": Path(e["audio_filepath"]).name})
    return rows

"""Speech recognition with any Hugging Face model: pseudo-labels for clips without text,
and a character error rate (CER) check of aligned clips.

MMS adapters (facebook/mms-1b-all) cover mos, dyu, gux and ful: set `target_lang`.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np


class ASR:
    """`batch_size` caps the clips per batch and `max_batch_seconds` the padded audio per batch
    (clips x longest clip), so batches of long clips stay small enough for an 8 GB GPU."""

    def __init__(self, model: str, target_lang: str | None = None, device: str | None = None, batch_size: int = 8,
                 max_batch_seconds: float = 60.0):
        import torch
        from transformers import pipeline

        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        kwargs = {"target_lang": target_lang, "ignore_mismatched_sizes": True} if target_lang else {}
        from .export import hf_token

        self.pipe = pipeline("automatic-speech-recognition", model=model, device=device, model_kwargs=kwargs,
                             token=hf_token())          # needed for gated models
        self.batch_size, self.max_batch_seconds = batch_size, max_batch_seconds

    def batches(self, lengths: list[int], sample_rate: int) -> list[list[int]]:
        """Clip indices grouped shortest first, each group within both caps (a too-long clip goes alone)."""
        limit = self.max_batch_seconds * sample_rate
        out: list[list[int]] = []
        for i in sorted(range(len(lengths)), key=lambda i: lengths[i]):
            if out and len(out[-1]) < self.batch_size and (len(out[-1]) + 1) * lengths[i] <= limit:
                out[-1].append(i)
            else:
                out.append([i])
        return out

    def __call__(self, clips: list[np.ndarray], sample_rate: int = 16_000) -> list[str]:
        texts: list[str] = [""] * len(clips)
        for idx in self.batches([len(c) for c in clips], sample_rate):
            out = self.pipe([{"raw": clips[j], "sampling_rate": sample_rate} for j in idx], batch_size=len(idx))
            for j, o in zip(idx, out):
                texts[j] = o["text"].strip()
        return texts


def score_text(text: str) -> str:
    """Text as it is scored: NFC, lowercase, `<...>` tags removed, and everything that is not a letter or a
    combining mark (punctuation, apostrophes, hyphens, digits) turned into a space. Tone marks and nasal
    tildes are kept. Apostrophes and hyphens become spaces because the Mooré ASR models write `t'a` and
    `yõk-a` as two words."""
    text = unicodedata.normalize("NFC", text.lower())
    text = re.sub(r"<[^>]*>", " ", text)
    text = "".join(c if unicodedata.category(c)[0] in "LM" else " " for c in text)
    return " ".join(text.split())


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate on `score_text` of both sides."""
    r, h = score_text(reference), score_text(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        cur = [i]
        for j, hc in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return prev[-1] / len(r)

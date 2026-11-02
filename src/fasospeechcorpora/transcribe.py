"""Speech recognition with any Hugging Face model: pseudo-labels for clips without text,
and a character error rate (CER) check of aligned clips.

MMS adapters (facebook/mms-1b-all) cover mos, dyu, gux and ful: set `target_lang`.
"""
from __future__ import annotations

import unicodedata

import numpy as np


class ASR:
    def __init__(self, model: str, target_lang: str | None = None, device: str | None = None, batch_size: int = 8):
        import torch
        from transformers import pipeline

        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        kwargs = {"target_lang": target_lang, "ignore_mismatched_sizes": True} if target_lang else {}
        from .export import hf_token

        self.pipe = pipeline("automatic-speech-recognition", model=model, device=device, model_kwargs=kwargs,
                             token=hf_token())          # needed for gated models
        self.batch_size = batch_size

    def __call__(self, clips: list[np.ndarray], sample_rate: int = 16_000) -> list[str]:
        inputs = [{"raw": c, "sampling_rate": sample_rate} for c in clips]
        return [o["text"].strip() for o in self.pipe(inputs, batch_size=self.batch_size)]


def _chars(text: str) -> str:
    text = unicodedata.normalize("NFC", text.lower())
    return " ".join("".join(c for c in text if c.isalpha() or c.isspace() or c == "'").split())


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate after lowercasing and removing punctuation."""
    r, h = _chars(reference), _chars(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        cur = [i]
        for j, hc in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return prev[-1] / len(r)

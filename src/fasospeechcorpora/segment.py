"""Split recordings that have no text into utterance-sized clips at pauses.

The silence threshold is computed per file (a percentile of frame energy), so loud and quiet
recordings are both handled.
"""
from __future__ import annotations

import numpy as np


def frame_db(wav: np.ndarray, sr: int, frame: float = 0.03) -> np.ndarray:
    n = int(frame * sr)
    frames = wav[: len(wav) // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms)


def split_on_silence(wav: np.ndarray, sr: int = 16_000, min_len: float = 2.0, max_len: float = 15.0,
                     min_silence: float = 0.3, percentile: float = 5, margin_db: float = 6.0,
                     frame: float = 0.03) -> list[tuple[float, float]]:
    """Return (start, end) times in seconds. Cuts at the middle of pauses."""
    db = frame_db(wav, sr, frame)
    if not len(db):
        return []
    # quiet = within `margin_db` of the noise floor, and always well below the speech level
    threshold = min(np.percentile(db, percentile) + margin_db, np.percentile(db, 95) - 20)
    quiet = db < threshold
    # middle of every pause that lasts at least `min_silence`
    cuts, run = [0.0], 0
    for i, q in enumerate(quiet):
        run = run + 1 if q else 0
        if run * frame >= min_silence and (i + 1 == len(quiet) or not quiet[i + 1]):
            cuts.append((i + 1 - run / 2) * frame)
    total = len(wav) / sr
    cuts.append(total)
    # merge short pieces greedily, force a cut when a piece grows past max_len
    spans, start = [], 0.0
    for c in cuts[1:]:
        if c - start >= min_len or c == total:
            while c - start > max_len:
                spans.append((start, start + max_len))
                start += max_len
            if c - start > 0.2:
                spans.append((start, c))
            start = c
    return spans

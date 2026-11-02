"""Cut each clip down to its speech: drop music and silence before the first word and after the last.

The clip is split into voice and music with Demucs. A frame counts as speech when the voice is
within `rel_db` of the clip's loudest voice frame, above `floor_db`, and louder than the music.
Short blips (under `min_run` seconds) are ignored, so a breath or a drum hit does not count.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Bounds:
    start: float                 # seconds, first speech frame
    end: float                   # seconds, end of the last speech frame
    lead_music: float            # seconds of music before `start`
    trail_music: float           # seconds of music after `end`
    music_under_voice_db: float  # median music level relative to the voice, during speech


def frame_db(y: np.ndarray, n: int) -> np.ndarray:
    k = len(y) // n
    return 20 * np.log10(np.sqrt((y[: k * n].reshape(k, n) ** 2).mean(axis=1)) + 1e-9)


def speech_bounds(voice: np.ndarray, music: np.ndarray, sr: int = 16_000, frame: float = 0.02,
                  rel_db: float = 30.0, floor_db: float = -50.0, music_db: float = -45.0,
                  min_run: float = 0.06) -> Bounds | None:
    n = int(frame * sr)
    vd, md = frame_db(voice, n), frame_db(music, n)
    if not len(vd):
        return None
    active = (vd > vd.max() - rel_db) & (vd > floor_db) & (vd > md)
    # keep only runs of speech long enough to be speech
    need, run, keep = max(1, round(min_run / frame)), 0, np.zeros_like(active)
    for i, a in enumerate(active):
        run = run + 1 if a else 0
        if run >= need:
            keep[i - run + 1: i + 1] = True
    idx = np.flatnonzero(keep)
    if not len(idx):
        return None
    first, last = idx[0], idx[-1] + 1
    is_music = md > music_db
    return Bounds(start=first * frame, end=last * frame,
                  lead_music=float(is_music[:first].sum() * frame), trail_music=float(is_music[last:].sum() * frame),
                  music_under_voice_db=float(np.median(md[keep] - vd[keep])))

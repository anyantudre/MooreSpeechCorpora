"""Non-speech metadata and the ASR views built from it.

After `trim`, every clip knows where its speech starts and ends inside the original (untrimmed) clip.
From that this module derives:

  nonspeech_spans  [{start, end, label}] in seconds of the untrimmed clip: what `trim` cut off
                   at each edge, labelled "music" or "silence"
  segment_type     "speech", "speech_with_edge_music" or "music_only"
  is_nonspeech     true when the text is empty or only tags

and three ASR views of a corpus:

  negatives()  music-only clips with empty text, cut from the edges trim removed (plus clips where
               no voice was found), capped at a share of the speech clips
  tagged()     the untrimmed clip with `<MUSIC>` at each edge that had music; tags never mark the
               music bed under speech

Tags come from a closed set and are stripped before scoring (see transcribe.score_text).
"""
from __future__ import annotations

import random
import re
from pathlib import Path

import numpy as np

from . import audio

TAGS = ("<MUSIC>", "<NOISE>", "<LAUGH>", "<OVERLAP>", "<INAUDIBLE>")
_TAG = re.compile(r"<[A-Z]+>")


def is_nonspeech(text: str | None) -> bool:
    return not _TAG.sub(" ", text or "").strip()


def locate(part: np.ndarray, whole: np.ndarray) -> int | None:
    """Sample offset of `part` inside `whole` (trim saves an exact slice, so the match is exact)."""
    if len(part) == 0 or len(part) > len(whole):
        return None
    probe = part[: min(len(part), 400)]
    first = np.flatnonzero(np.abs(whole[: len(whole) - len(part) + 1] - probe[0]) < 1e-6)
    for i in first:
        if np.allclose(whole[i: i + len(probe)], probe, atol=1e-6):
            return int(i)
    return None


def edge_label(music_seconds: float, span: float, min_share: float = 0.5) -> str:
    return "music" if span > 0 and music_seconds >= min_share * span else "silence"


def spans(r: dict, min_span: float = 0.05) -> list[dict]:
    """The edges trim cut off, in seconds of the untrimmed clip."""
    if r.get("trim_start") is None:
        return []
    out = []
    a, z, total = r["trim_start"], r["trim_end"], r["untrimmed_duration"]
    if a >= min_span:
        out.append({"start": 0.0, "end": round(a, 3), "label": edge_label(r.get("lead_music", 0.0), a)})
    if total - z >= min_span:
        out.append({"start": round(z, 3), "end": round(total, 3),
                    "label": edge_label(r.get("trail_music", 0.0), total - z)})
    return out


def segment_type(r: dict, min_music: float = 0.5) -> str:
    if r.get("no_voice") or is_nonspeech(r.get("text")):
        return "music_only"
    edges = r.get("nonspeech_spans") or []
    if any(s["label"] == "music" and s["end"] - s["start"] >= min_music for s in edges):
        return "speech_with_edge_music"
    return "speech"


def annotate(r: dict) -> dict:
    """Fill nonspeech_spans, segment_type and is_nonspeech on a trimmed row (in place)."""
    r["nonspeech_spans"] = spans(r)
    r["segment_type"] = segment_type(r)
    r["is_nonspeech"] = is_nonspeech(r.get("text")) or bool(r.get("no_voice"))
    return r


def negatives(rows: list[dict], speech: list[dict], root: Path, sr: int = 16_000, min_len: float = 1.0,
              max_share: float = 0.1, seed: int = 0) -> list[dict]:
    """Music-only clips with empty text, at most `max_share` of len(speech).

    Candidates: the music edges trim cut off (at least `min_len` seconds) and whole clips where trim
    found no voice. Clips are written under negatives/.
    """
    cands = []
    for r in rows:
        if r.get("no_voice") and r.get("duration", 0) >= min_len:
            cands.append((r, None))
        for s in r.get("nonspeech_spans") or []:
            if s["label"] == "music" and s["end"] - s["start"] >= min_len:
                cands.append((r, s))
    random.Random(seed).shuffle(cands)
    out = []
    for r, s in cands[: int(max_share * len(speech))]:
        src = r.get("untrimmed_audio_filepath") or r["audio_filepath"]
        wav = audio.load(root / src, sr)
        if s is not None:
            wav = wav[int(s["start"] * sr): int(s["end"] * sr)]
        side = "clip" if s is None else ("lead" if s["start"] == 0 else "trail")
        path = f"negatives/{r['id']}_{side}.wav"
        audio.save(root / path, wav, sr)
        d = round(len(wav) / sr, 3)
        out.append({"id": f"{r['id']}_{side}", "audio_filepath": path, "text": "", "duration": d,
                    "language": r.get("language"), "source": r.get("source"), "source_id": r.get("source_id"),
                    "chapter": r.get("chapter"), "book": r.get("book"), "category": r.get("category"),
                    "nonspeech_spans": [{"start": 0.0, "end": d, "label": "music"}],
                    "segment_type": "music_only", "is_nonspeech": True})
    return out


def tagged(rows: list[dict], min_music: float = 0.5) -> list[dict]:
    """The untrimmed clip, with `<MUSIC>` on each edge that held at least `min_music` s of music."""
    out = []
    for r in rows:
        if not r.get("untrimmed_audio_filepath") or r.get("trim_start") is None:
            continue
        edges = {("lead" if s["start"] == 0 else "trail"): s for s in r.get("nonspeech_spans") or []}
        music = {k for k, s in edges.items() if s["label"] == "music" and s["end"] - s["start"] >= min_music}
        text = " ".join(p for p in ("<MUSIC>" if "lead" in music else "", r["text"],
                                    "<MUSIC>" if "trail" in music else "") if p)
        out.append({**r, "audio_filepath": r["untrimmed_audio_filepath"], "duration": r["untrimmed_duration"],
                    "text": text, "start": None, "end": None})
    return out

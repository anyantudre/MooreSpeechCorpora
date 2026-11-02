"""Group clips by speaker and guess male/female voices, for datasets that need speaker labels.

Each clip gets a speaker embedding (WavLM x-vector, `microsoft/wavlm-base-plus-sv`; weights under
CC BY-SA 3.0, used here only to compute labels). Clips are grouped by cosine similarity, and each
group's median pitch suggests "male" or "female". A person should listen to a few clips per group and
confirm the labels: see the `speakers` step in pipeline.py.
"""
from __future__ import annotations

import numpy as np


class SpeakerEmbedder:
    def __init__(self, model: str = "microsoft/wavlm-base-plus-sv", device: str | None = None):
        import torch
        from transformers import AutoFeatureExtractor, WavLMForXVector

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.fe = AutoFeatureExtractor.from_pretrained(model)
        self.model = WavLMForXVector.from_pretrained(model).to(self.device).eval()

    def __call__(self, clips: list[np.ndarray], sr: int = 16_000, max_seconds: float = 8.0,
                 batch: int = 16) -> np.ndarray:
        out = []
        for i in range(0, len(clips), batch):
            part = [c[: int(max_seconds * sr)] for c in clips[i:i + batch]]
            x = self.fe(part, sampling_rate=sr, return_tensors="pt", padding=True).to(self.device)
            with self.torch.inference_mode():
                e = self.model(**x).embeddings
            out.append(self.torch.nn.functional.normalize(e, dim=-1).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 512), dtype=np.float32)


def cluster(emb: np.ndarray, threshold: float = 0.75) -> np.ndarray:
    """Greedy cosine clustering, then merge groups whose centres are closer than `threshold`.
    Labels are 0, 1, 2… from the largest group down."""
    centres, members = [], []
    for i, e in enumerate(emb):
        if centres:
            sims = np.stack(centres) @ e
            j = int(sims.argmax())
            if sims[j] >= threshold:
                members[j].append(i)
                c = emb[members[j]].mean(axis=0)
                centres[j] = c / np.linalg.norm(c)
                continue
        centres.append(e.copy())
        members.append([i])
    merged = True
    while merged and len(centres) > 1:
        merged = False
        sims = np.stack(centres) @ np.stack(centres).T
        np.fill_diagonal(sims, -1)
        a, b = np.unravel_index(sims.argmax(), sims.shape)
        if sims[a, b] >= threshold:
            members[a] += members.pop(b)
            centres.pop(b)
            c = emb[members[a]].mean(axis=0)
            centres[a] = c / np.linalg.norm(c)
            merged = True
    labels = np.zeros(len(emb), dtype=int)
    for rank, m in enumerate(sorted(members, key=len, reverse=True)):
        labels[m] = rank
    return labels


def median_f0(wav: np.ndarray, sr: int = 16_000, fmin: float = 70.0, fmax: float = 400.0) -> float | None:
    """Median pitch of the voiced frames (autocorrelation), in Hz."""
    n, hop = int(0.04 * sr), int(0.02 * sr)
    frames = [wav[i:i + n] for i in range(0, len(wav) - n, hop)]
    if not frames:
        return None
    rms = np.array([np.sqrt((f ** 2).mean()) for f in frames])
    lo, hi = int(sr / fmax), int(sr / fmin)
    f0 = []
    for f, r in zip(frames, rms):
        if r < rms.max() * 0.1:                          # skip quiet frames (20 dB under the loudest)
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, mode="full")[n - 1:]
        if ac[0] <= 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.5:                        # clearly periodic
            f0.append(sr / lag)
    return float(np.median(f0)) if f0 else None

"""Group clips by speaker and guess male/female voices, for datasets that need speaker labels.

Each clip gets a speaker embedding: ECAPA-TDNN by default (`speechbrain/spkrec-ecapa-voxceleb`,
Apache-2.0), or a WavLM x-vector (`microsoft/wavlm-base-plus-sv`, CC BY-SA 3.0). Clips are grouped
by chapter first, since one chapter or recording is normally read by one person: each chapter's
mean embedding is clustered with average linkage, and each group's median pitch suggests "male" or
"female". A person should listen to a few clips per group and confirm the labels: see the
`speakers` step in pipeline.py.
"""
from __future__ import annotations

import numpy as np

ECAPA = "speechbrain/spkrec-ecapa-voxceleb"


class EcapaEmbedder:
    def __init__(self, model: str = ECAPA, device: str | None = None, savedir: str | None = None):
        import torch
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = EncoderClassifier.from_hparams(source=model, savedir=savedir, run_opts={"device": self.device},
                                                    local_strategy=LocalStrategy.COPY)

    def __call__(self, clips: list[np.ndarray], sr: int = 16_000, max_seconds: float = 8.0,
                 batch: int = 8) -> np.ndarray:
        torch = self.torch
        clips = [c[: int(max_seconds * sr)] for c in clips]
        out = np.zeros((len(clips), 192), dtype=np.float32)
        order = sorted(range(len(clips)), key=lambda i: len(clips[i]))
        for k in range(0, len(order), batch):
            idx = order[k:k + batch]
            n = max(len(clips[i]) for i in idx)
            x, lens = torch.zeros(len(idx), n), torch.zeros(len(idx))
            for j, i in enumerate(idx):
                x[j, :len(clips[i])] = torch.from_numpy(np.asarray(clips[i], dtype=np.float32))
                lens[j] = len(clips[i]) / n
            with torch.inference_mode():
                e = self.model.encode_batch(x.to(self.device), lens.to(self.device)).squeeze(1)
            out[idx] = torch.nn.functional.normalize(e, dim=-1).cpu().numpy()
        return out


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


def chapter_units(rows: list[dict], min_clips: int = 3) -> list[str]:
    """A unit per chapter or recording: run, source, book and chapter (or the source recording).
    Units with fewer than `min_clips` clips are grouped by their book when they have one."""
    def key(r, coarse=False):
        parts = [r.get("run"), r.get("source"), r.get("book")]
        if not coarse:
            parts.append(r.get("chapter") or r.get("source_id") or r.get("id"))
        return "|".join(str(p) for p in parts)

    fine = [key(r) for r in rows]
    size = {k: fine.count(k) for k in set(fine)}
    return [key(r, coarse=True) if size[k] < min_clips and r.get("book") else k for r, k in zip(rows, fine)]


def cluster(emb: np.ndarray, units: list[str] | None = None, threshold: float = 0.55) -> np.ndarray:
    """Cluster clips by speaker. Each unit (a chapter; one unit per clip when `units` is None) is
    represented by its mean embedding; units are merged with average linkage while their cosine
    similarity is at least `threshold`. Labels are 0, 1, 2… from the largest group down."""
    from scipy.cluster.hierarchy import fcluster, linkage

    units = units if units is not None else [str(i) for i in range(len(emb))]
    keys = list(dict.fromkeys(units))
    index = {k: i for i, k in enumerate(keys)}
    cent = np.zeros((len(keys), emb.shape[1]))
    for e, u in zip(emb, units):
        cent[index[u]] += e
    cent /= np.linalg.norm(cent, axis=1, keepdims=True)
    if len(keys) == 1:
        unit_label = np.ones(1, dtype=int)
    else:
        unit_label = fcluster(linkage(cent, method="average", metric="cosine"), t=1 - threshold, criterion="distance")
    clip_label = np.array([unit_label[index[u]] for u in units])
    ranks = {g: r for r, (g, _) in enumerate(sorted(((g, (clip_label == g).sum()) for g in set(clip_label)),
                                                    key=lambda x: -x[1]))}
    return np.array([ranks[g] for g in clip_label], dtype=int)


def cluster_sample(emb: np.ndarray, threshold: float = 0.55, sample: int = 5000, min_group: int = 10,
                   merge: float = 0.7, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Clip-by-clip grouping for many clips: cluster a random sample, keep the groups with at least
    `min_group` clips (the voices; tiny groups are mostly short clips with noisy embeddings), merge the
    groups whose mean embeddings have a cosine of at least `merge` (short clips of one reader split
    into several groups whose means are 0.75-0.95 apart; two readers are under 0.6), then give every
    clip the voice whose mean embedding is closest. Returns (labels, cosine to that voice);
    labels are 0, 1, 2… from the largest group down."""
    e = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    idx = np.random.default_rng(seed).permutation(len(e))[:sample]
    g = cluster(e[idx], None, threshold)
    counts = np.bincount(g)
    keep = [k for k in range(len(counts)) if counts[k] >= min_group] or [0]
    cent = np.stack([e[idx][g == k].mean(axis=0) for k in keep])
    cent /= np.linalg.norm(cent, axis=1, keepdims=True)
    if len(keep) > 1:
        voice = cluster(cent, None, merge)                    # which voice each kept group belongs to
        member = {k: v for k, v in zip(keep, voice)}
        g = np.array([member.get(k, -1) for k in g])
        cent = np.stack([e[idx][g == v].mean(axis=0) for v in sorted(set(voice))])
        cent /= np.linalg.norm(cent, axis=1, keepdims=True)
        keep = sorted(set(voice))
    sims = e @ cent.T
    best = sims.argmax(axis=1)
    order = np.argsort(-np.bincount(best, minlength=len(keep)), kind="stable")
    rank = np.empty(len(keep), dtype=int)
    rank[order] = np.arange(len(keep))
    return rank[best], sims.max(axis=1)


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

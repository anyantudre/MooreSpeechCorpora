"""Remove background music from recordings by keeping only the voice, with Demucs (htdemucs).

Install with `pip install "fasospeechcorpora[enhance]"`. Runs on CPU or GPU; on CPU expect about
real time. The Demucs code and models are MIT licensed.
"""
from __future__ import annotations

import numpy as np
import soxr


class VoiceExtractor:
    def __init__(self, model: str = "htdemucs", device: str | None = None):
        import torch
        from demucs.api import Separator

        self.torch = torch
        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.separator = Separator(model=model, device=device)

    def __call__(self, wav: np.ndarray, sample_rate: int = 16_000) -> np.ndarray:
        """Mono float32 in, mono float32 voice out, at the same sample rate."""
        x = self.torch.from_numpy(wav).float().unsqueeze(0)          # (channels=1, samples)
        _, stems = self.separator.separate_tensor(x, sample_rate)
        voice = stems["vocals"].mean(dim=0).cpu().numpy()
        voice = soxr.resample(voice, self.separator.samplerate, sample_rate)
        return voice[: len(wav)].astype(np.float32)

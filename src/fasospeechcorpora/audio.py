"""Audio input/output: decode anything, resample to mono 16 kHz, write clips.

soundfile (libsndfile) reads wav, flac, ogg and mp3 on every platform. Other formats
(m4a, webm, mp4) go through ffmpeg: the one bundled by `imageio-ffmpeg` if installed,
otherwise the system ffmpeg.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr


def ffmpeg_binary() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        exe = shutil.which("ffmpeg")
        if not exe:
            raise RuntimeError("This file needs ffmpeg: `pip install imageio-ffmpeg` or install ffmpeg.")
        return exe


def load(path: str | Path, sample_rate: int = 16_000) -> np.ndarray:
    """Return mono float32 audio at `sample_rate`."""
    path = Path(path)
    try:
        audio, sr = sf.read(path, dtype="float32", always_2d=True)
        audio = audio.mean(axis=1)
    except (sf.LibsndfileError, RuntimeError):
        cmd = [ffmpeg_binary(), "-nostdin", "-loglevel", "error", "-i", str(path),
               "-f", "f32le", "-ac", "1", "-ar", str(sample_rate), "-"]
        raw = subprocess.run(cmd, check=True, capture_output=True).stdout
        return np.frombuffer(raw, dtype=np.float32).copy()
    if sr != sample_rate:
        audio = soxr.resample(audio, sr, sample_rate)
    return audio.astype(np.float32)


def save(path: str | Path, audio: np.ndarray, sample_rate: int = 16_000) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio, sample_rate)


def duration(path: str | Path) -> float:
    info = sf.info(path)
    return info.frames / info.samplerate

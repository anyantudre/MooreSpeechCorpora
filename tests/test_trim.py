import numpy as np
import soundfile as sf

from fasospeechcorpora import manifest
from fasospeechcorpora.config import load_recipe
from fasospeechcorpora.pipeline import Pipeline
from fasospeechcorpora.trim import speech_bounds

SR = 16_000


def tone(seconds, amp=0.3):
    t = np.arange(int(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def zeros(seconds):
    return np.zeros(int(seconds * SR), dtype=np.float32)


def noise(seconds, amp=0.05):
    return (amp * np.random.default_rng(0).standard_normal(int(seconds * SR))).astype(np.float32)


def test_bounds_skip_music_intro_and_trailing_silence():
    voice = np.concatenate([zeros(1.5), tone(2), zeros(0.8)])
    music = np.concatenate([noise(1.5), zeros(2), zeros(0.8)])
    b = speech_bounds(voice, music, SR)
    assert abs(b.start - 1.5) < 0.05 and abs(b.end - 3.5) < 0.05
    assert abs(b.lead_music - 1.5) < 0.05 and b.trail_music == 0
    assert b.music_under_voice_db < -60


def test_bounds_ignore_short_blips():
    voice = np.concatenate([tone(0.03), zeros(1), tone(2), zeros(1)])
    b = speech_bounds(voice, zeros(len(voice) / SR), SR)
    assert abs(b.start - 1.03) < 0.05


def test_no_voice():
    assert speech_bounds(zeros(2), noise(2), SR) is None


def test_trim_step_cuts_clips_and_keeps_the_voice(tmp_path, monkeypatch):
    import fasospeechcorpora.enhance as enhance

    class FakeSplit:                          # stands in for Demucs: music = the first second
        def __init__(self, *a, **k):
            pass

        def split(self, wav, sample_rate):
            music = np.zeros_like(wav)
            music[:SR] = wav[:SR]
            voice = wav.copy()
            voice[:SR] = 0
            return voice, music

    monkeypatch.setattr(enhance, "VoiceExtractor", FakeSplit)
    rec = tmp_path / "recordings"
    rec.mkdir()
    sf.write(rec / "a.wav", np.concatenate([noise(1, 0.2), tone(2), zeros(1)]), SR)
    (rec / "a.txt").write_text("0.0\t4.0\tWẽnnaam yeelame.\n", encoding="utf-8")
    recipe = tmp_path / "r.yaml"
    recipe.write_text(f"language: mos\nsource:\n  type: local\n  path: {rec.as_posix()}\n", encoding="utf-8")
    pipe = Pipeline(load_recipe(recipe, tmp_path / "out"))
    pipe.run(["fetch", "prepare", "align", "trim", "filter"])
    pipe.run(["trim"])                        # second run does nothing
    row = manifest.read(tmp_path / "out" / "final.jsonl")[0]
    assert row["audio_filepath"] == "trimmed/a_0000.wav" and row["voice_filepath"] == "trimmed_voice/a_0000.wav"
    assert abs(row["duration"] - 2.4) < 0.05 and abs(row["start"] - 0.8) < 0.05
    assert row["lead_music"] >= 0.9
    assert sf.info(tmp_path / "out" / row["audio_filepath"]).duration == row["duration"]

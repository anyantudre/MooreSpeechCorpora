import numpy as np
import soundfile as sf

from voxfaso import manifest
from voxfaso.config import load_recipe
from voxfaso.pipeline import Pipeline
from voxfaso.segment import split_on_silence
from voxfaso.transcribe import cer

SR = 16_000


def tone(seconds, freq=220.0, sr=SR):
    t = np.arange(int(seconds * sr)) / sr
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silence(seconds, sr=SR):
    return np.zeros(int(seconds * sr), dtype=np.float32)


def test_split_on_silence_cuts_in_pauses():
    wav = np.concatenate([tone(3), silence(0.6), tone(3), silence(0.6), tone(3)])
    spans = split_on_silence(wav, SR, min_len=2, max_len=15)
    assert len(spans) == 3
    assert abs(spans[0][1] - 3.3) < 0.1 and abs(spans[1][1] - 6.9) < 0.1


def test_split_on_silence_forces_max_len():
    spans = split_on_silence(tone(40), SR, max_len=15)
    assert all(e - s <= 15 for s, e in spans)


def test_cer():
    assert cer("Wẽnnaam yeelame.", "wẽnnaam yeelame") == 0
    assert 0 < cer("abcd", "abed") <= 0.25


def test_local_source_prepare_and_filter(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir()
    sf.write(rec / "a.wav", np.concatenate([tone(3, sr=44_100), silence(0.6, sr=44_100), tone(3, sr=44_100)]), 44_100)
    recipe = tmp_path / "r.yaml"
    recipe.write_text(f"language: mos\nsource:\n  type: local\n  path: {rec.as_posix()}\n", encoding="utf-8")
    pipe = Pipeline(load_recipe(recipe, tmp_path / "out"))
    pipe.run(["fetch", "prepare", "segment", "filter"])
    prepared = manifest.read(tmp_path / "out" / "prepared.jsonl")
    assert sf.info(tmp_path / "out" / prepared[0]["audio_filepath"]).samplerate == SR
    assert len(manifest.read(tmp_path / "out" / "segmented.jsonl")) == 2
    # clips without text are dropped by the filter until they are transcribed
    assert manifest.read(tmp_path / "out" / "final.jsonl") == []


def test_filter_rules(tmp_path):
    recipe = tmp_path / "r.yaml"
    recipe.write_text("language: mos\nsource: {type: local, path: .}\nfilter: {min_score: 0.5}\n", encoding="utf-8")
    pipe = Pipeline(load_recipe(recipe, tmp_path))
    rows = [
        {"id": "ok", "text": "Wẽnnaam yeelame.", "duration": 2.0, "language": "mos", "score": 0.9},
        {"id": "short", "text": "Ee.", "duration": 0.2, "language": "mos"},
        {"id": "fra", "text": "Clémence.", "duration": 2.0, "language": "fra"},
        {"id": "low", "text": "Wẽnnaam.", "duration": 2.0, "language": "mos", "score": 0.1},
    ]
    manifest.write(tmp_path / "aligned.jsonl", rows)
    pipe.filter()
    assert [r["id"] for r in manifest.read(tmp_path / "final.jsonl")] == ["ok"]

import numpy as np
import pytest
import soundfile as sf

from fasospeechcorpora import manifest
from fasospeechcorpora.config import load_recipe
from fasospeechcorpora.pipeline import Pipeline
from fasospeechcorpora.speakers import cluster, median_f0

SR = 16_000


def voiced(f0, seconds=1.5):
    """A buzzy periodic sound with harmonics, like a sustained vowel."""
    t = np.arange(int(seconds * SR)) / SR
    return sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 6)).astype(np.float32) * 0.2


def test_median_f0_separates_low_and_high_voices():
    assert abs(median_f0(voiced(120)) - 120) < 6
    assert abs(median_f0(voiced(220)) - 220) < 10
    assert median_f0(np.zeros(SR, dtype=np.float32)) is None


def test_cluster_groups_similar_embeddings_largest_first():
    rng = np.random.default_rng(0)
    a, b = rng.standard_normal(512), rng.standard_normal(512)
    emb = [a + 0.1 * rng.standard_normal(512) for _ in range(5)] + [b + 0.1 * rng.standard_normal(512) for _ in range(3)]
    emb = np.stack([e / np.linalg.norm(e) for e in emb])
    labels = cluster(emb, 0.8)
    assert list(labels) == [0, 0, 0, 0, 0, 1, 1, 1]


def make_run(tmp_path, steps, recipe_extra=""):
    rec = tmp_path / "recordings"
    rec.mkdir()
    sf.write(rec / "low.wav", voiced(120, 2.0), SR)
    sf.write(rec / "high.wav", voiced(220, 2.0), SR)
    (rec / "low.txt").write_text("0.0\t2.0\tWẽnnaam yeelame.\n", encoding="utf-8")
    (rec / "high.txt").write_text("0.0\t2.0\tLa a yɩɩ woto.\n", encoding="utf-8")
    recipe = tmp_path / "r.yaml"
    recipe.write_text(f"language: mos\nsource:\n  type: local\n  path: {rec.as_posix()}\n{recipe_extra}", encoding="utf-8")
    pipe = Pipeline(load_recipe(recipe, tmp_path / "out"))
    pipe.run(steps)
    return pipe


def test_speakers_step_labels_and_reads_corrections(tmp_path, monkeypatch):
    import fasospeechcorpora.speakers as speakers

    class FakeEmbedder:                      # one direction per pitch, standing in for WavLM
        def __init__(self, *a, **k):
            pass

        def __call__(self, clips, sr):
            return np.stack([np.eye(512)[0] if median_f0(c) < 165 else np.eye(512)[1] for c in clips])

    monkeypatch.setattr(speakers, "SpeakerEmbedder", FakeEmbedder)
    pipe = make_run(tmp_path, ["fetch", "prepare", "align", "filter", "speakers"])
    rows = {r["text"]: r for r in manifest.read(tmp_path / "out" / "final.jsonl")}
    assert rows["Wẽnnaam yeelame."]["voice"] == "male" and rows["La a yɩɩ woto."]["voice"] == "female"
    assert len({r["speaker_id"] for r in rows.values()}) == 2
    assert (tmp_path / "out" / "speakers" / "summary.json").exists()
    g = rows["La a yɩɩ woto."]["speaker_group"]
    (tmp_path / "out" / "speakers" / "labels.yaml").write_text(f"{g}: {{speaker_id: 7, voice: female}}\n", encoding="utf-8")
    pipe.run(["speakers"])
    rows = {r["text"]: r for r in manifest.read(tmp_path / "out" / "final.jsonl")}
    assert rows["La a yɩɩ woto."]["speaker_id"] == 7


def test_verify_scores_every_clip_and_filter_uses_it(tmp_path, monkeypatch):
    import fasospeechcorpora.transcribe as transcribe

    class FakeASR:
        def __init__(self, *a, **k):
            pass

        def __call__(self, clips, sr):
            return ["wẽnnaam yeelame" for _ in clips]     # right for one clip, wrong for the other

    monkeypatch.setattr(transcribe, "ASR", FakeASR)
    make_run(tmp_path, ["fetch", "prepare", "align", "verify", "filter"], "filter:\n  max_cer: 0.3\n")
    aligned = manifest.read(tmp_path / "out" / "aligned.jsonl")
    assert all("cer" in r and "cer_mms-1b-all" in r for r in aligned)
    assert [r["text"] for r in manifest.read(tmp_path / "out" / "final.jsonl")] == ["Wẽnnaam yeelame."]


def test_export_corpora_v1_layout(tmp_path):
    pytest.importorskip("datasets")
    from datasets import load_from_disk

    from fasospeechcorpora.export import export

    pipe = make_run(tmp_path, ["fetch", "prepare", "align", "filter"])
    rows = manifest.read(tmp_path / "out" / "final.jsonl")
    for r in rows:
        r.update(voice="male", speaker_id=1)
    export(rows, pipe.root, {"formats": ["hf"], "layout": "corpora_v1"}, "mos")
    ds = load_from_disk(str(tmp_path / "out" / "hf"))
    assert ds.column_names == ["audio", "text", "duration", "voice", "speaker_id", "denoised_audio",
                               "source", "chapter", "alignment_score", "cer"]

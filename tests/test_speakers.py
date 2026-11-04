import numpy as np
import pytest
import soundfile as sf

from fasospeechcorpora import manifest
from fasospeechcorpora.config import load_recipe
from fasospeechcorpora.pipeline import Pipeline
from fasospeechcorpora.speakers import chapter_units, cluster, median_f0

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
    pytest.importorskip("scipy")
    rng = np.random.default_rng(0)
    a, b = rng.standard_normal(192), rng.standard_normal(192)
    emb = [a + 0.1 * rng.standard_normal(192) for _ in range(5)] + [b + 0.1 * rng.standard_normal(192) for _ in range(3)]
    emb = np.stack([e / np.linalg.norm(e) for e in emb])
    assert list(cluster(emb, threshold=0.8)) == [0, 0, 0, 0, 0, 1, 1, 1]


def test_cluster_by_chapter_keeps_a_noisy_clip_with_its_chapter():
    pytest.importorskip("scipy")
    rng = np.random.default_rng(1)
    a, b = rng.standard_normal(192), rng.standard_normal(192)
    emb = [a + 0.1 * rng.standard_normal(192) for _ in range(4)] + [b] + [b + 0.1 * rng.standard_normal(192) for _ in range(3)]
    emb = np.stack([e / np.linalg.norm(e) for e in emb])
    # clip 4 sounds like speaker b but belongs to chapter A, read by speaker a
    units = ["A"] * 5 + ["B"] * 3
    assert list(cluster(emb, units, threshold=0.55)) == [0, 0, 0, 0, 0, 1, 1, 1]


def test_cluster_sample_gives_every_clip_the_nearest_voice():
    pytest.importorskip("scipy")
    from fasospeechcorpora.speakers import cluster_sample

    rng = np.random.default_rng(2)
    a, b = rng.standard_normal(192), rng.standard_normal(192)
    emb = np.stack([a + 0.2 * rng.standard_normal(192) for _ in range(120)] +
                   [b + 0.2 * rng.standard_normal(192) for _ in range(60)] +
                   [a + 0.9 * rng.standard_normal(192) for _ in range(3)])       # noisy short clips of voice a
    labels, sim = cluster_sample(emb, threshold=0.55, sample=50, min_group=5)
    assert list(labels[:120]) == [0] * 120 and list(labels[120:180]) == [1] * 60
    assert list(labels[180:]) == [0, 0, 0] and sim[180:].max() < sim[:120].min()


def test_cluster_sample_merges_groups_of_one_voice():
    pytest.importorskip("scipy")
    from fasospeechcorpora.speakers import cluster_sample

    rng = np.random.default_rng(3)
    a, b = rng.standard_normal(192), rng.standard_normal(192)
    emb = np.stack([a + 1.0 * rng.standard_normal(192) for _ in range(150)] +    # short clips: noisy
                   [b + 0.3 * rng.standard_normal(192) for _ in range(40)])
    split, _ = cluster_sample(emb, threshold=0.55, sample=190, min_group=5, merge=1.0)
    assert len(set(split[:150])) > 1                      # without merging: reader a is split up
    labels, _ = cluster_sample(emb, threshold=0.55, sample=190, min_group=5, merge=0.7)
    assert set(labels[:150]) == {0} and set(labels[150:]) == {1}


def test_chapter_units_fall_back_to_the_book_for_small_pages():
    rows = [{"run": "p", "source": "s", "book": "p1", "chapter": f"c{i // 2}"} for i in range(4)]
    rows += [{"run": "t", "source": "s", "chapter": "c0"} for _ in range(3)] + [{"run": "t", "source_id": "x"}]
    units = chapter_units(rows, min_clips=3)
    assert units[:4] == ["p|s|p1"] * 4
    assert units[4:7] == ["t|s|None|c0"] * 3 and units[7] == "t|None|None|x"


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

    pytest.importorskip("scipy")

    class FakeEmbedder:                      # one direction per pitch, standing in for ECAPA
        def __init__(self, *a, **k):
            pass

        def __call__(self, clips, sr):
            return np.stack([np.eye(192)[0] if median_f0(c) < 165 else np.eye(192)[1] for c in clips])

    monkeypatch.setattr(speakers, "EcapaEmbedder", FakeEmbedder)
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


def test_speakers_clip_runs_split_a_chapter_with_two_voices(tmp_path, monkeypatch):
    import fasospeechcorpora.speakers as speakers

    pytest.importorskip("scipy")

    class FakeEmbedder:
        def __init__(self, *a, **k):
            pass

        def __call__(self, clips, sr):
            return np.stack([np.eye(192)[0] if median_f0(c) < 165 else np.eye(192)[1] for c in clips])

    monkeypatch.setattr(speakers, "EcapaEmbedder", FakeEmbedder)
    rows = []
    for k, (run, chapter, f0) in enumerate([("tales", "c1", 120), ("tales", "c1", 220), ("tales", "c1", 120),
                                            ("bible", "GEN_1", 120), ("bible", "GEN_1", 220), ("bible", "GEN_1", 220)]):
        sf.write(tmp_path / f"{k}.wav", voiced(f0), SR)
        rows.append({"id": str(k), "audio_filepath": f"{k}.wav", "text": "x", "duration": 1.5, "run": run,
                     "source": run, "chapter": chapter})
    manifest.write(tmp_path / "final.jsonl", rows)
    recipe = tmp_path / "r.yaml"
    recipe.write_text("language: mos\nsource: {type: local, path: .}\n"
                      "speakers: {clip_runs: [bible], min_unit_clips: 1}\n", encoding="utf-8")
    Pipeline(load_recipe(recipe, tmp_path)).speakers()
    got = [r["speaker_group"] for r in manifest.read(tmp_path / "final.jsonl")]
    assert got[:3] == [0, 0, 0]                      # the tales chapter is one unit: one reader
    assert got[3] != got[4] == got[5] and min(got[3:]) == 1


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


def test_verify_model_limited_to_some_languages(tmp_path, monkeypatch):
    import fasospeechcorpora.transcribe as transcribe

    class FakeASR:
        def __init__(self, *a, **k):
            pass

        def __call__(self, clips, sr):
            return ["x" for _ in clips]

    monkeypatch.setattr(transcribe, "ASR", FakeASR)
    pipe = make_run(tmp_path, ["fetch", "prepare", "align"])
    rows = manifest.read(pipe.path("aligned.jsonl"))
    rows[0]["language"] = "fra"
    manifest.write(pipe.path("aligned.jsonl"), rows)
    pipe.r.verify = {"models": [{"model": "facebook/mms-1b-all", "target_lang": "fra", "name": "mms-fra",
                                 "languages": ["fra"]}]}
    pipe.verify()
    got = manifest.read(pipe.path("aligned.jsonl"))
    assert "cer_mms-fra" in got[0] and "hyp_mms-fra" in got[0]
    assert all("cer_mms-fra" not in r for r in got[1:])


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

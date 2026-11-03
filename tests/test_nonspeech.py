import numpy as np
import pytest
import soundfile as sf

from fasospeechcorpora import manifest, nonspeech
from fasospeechcorpora.combine import combine
from fasospeechcorpora.config import load_recipe
from fasospeechcorpora.pipeline import Pipeline

SR = 16_000


def trimmed_row(**kw):
    r = {"id": "c0", "text": "Wẽnnaam yeelame.", "duration": 2.0, "language": "mos", "trimmed": True,
         "audio_filepath": "trimmed/c0.wav", "untrimmed_audio_filepath": "clips/c0.wav",
         "trim_start": 1.0, "trim_end": 3.0, "untrimmed_duration": 4.0, "lead_music": 0.9, "trail_music": 0.0}
    return {**r, **kw}


def test_locate_finds_the_exact_slice():
    whole = np.random.default_rng(0).uniform(-0.5, 0.5, 2 * SR).astype(np.float32)
    assert nonspeech.locate(whole[8000:24000], whole) == 8000
    assert nonspeech.locate(np.ones(10, dtype=np.float32), whole) is None


def test_annotate_labels_music_and_silence_edges():
    r = nonspeech.annotate(trimmed_row())
    assert r["nonspeech_spans"] == [{"start": 0.0, "end": 1.0, "label": "music"},
                                    {"start": 3.0, "end": 4.0, "label": "silence"}]
    assert r["segment_type"] == "speech_with_edge_music" and r["is_nonspeech"] is False
    assert nonspeech.annotate(trimmed_row(lead_music=0.1))["segment_type"] == "speech"
    assert nonspeech.annotate(trimmed_row(text="<MUSIC>"))["is_nonspeech"] is True


def test_tagged_marks_only_music_edges():
    [r] = nonspeech.tagged([nonspeech.annotate(trimmed_row())])
    assert r["text"] == "<MUSIC> Wẽnnaam yeelame."
    assert r["audio_filepath"] == "clips/c0.wav" and r["duration"] == 4.0


def test_negatives_are_cut_and_capped(tmp_path):
    (tmp_path / "clips").mkdir()
    sf.write(tmp_path / "clips" / "c0.wav", np.zeros(4 * SR, dtype=np.float32), SR)
    rows = [nonspeech.annotate(trimmed_row(lead_music=1.5, trim_start=1.5))]
    assert nonspeech.negatives(rows, speech=[{}] * 9, root=tmp_path) == []        # 10% of 9 rounds down to 0
    [neg] = nonspeech.negatives(rows, speech=[{}] * 10, root=tmp_path)
    assert neg["text"] == "" and neg["is_nonspeech"] and neg["segment_type"] == "music_only"
    assert neg["duration"] == pytest.approx(1.5) and (tmp_path / neg["audio_filepath"]).exists()


def test_trim_offsets_are_backfilled_from_the_audio(tmp_path):
    recipe = tmp_path / "r.yaml"
    recipe.write_text("language: mos\nsource: {type: local, path: .}\n", encoding="utf-8")
    pipe = Pipeline(load_recipe(recipe, tmp_path))
    whole = np.random.default_rng(1).uniform(-0.5, 0.5, 2 * SR).astype(np.float32)
    (tmp_path / "clips").mkdir()
    (tmp_path / "trimmed").mkdir()
    sf.write(tmp_path / "clips" / "c0.wav", whole, SR)
    sf.write(tmp_path / "trimmed" / "c0.wav", whole[8000:24000], SR)
    rows = [trimmed_row(trim_start=None, trim_end=None, untrimmed_duration=None)]
    pipe._backfill_trim(rows)
    assert (rows[0]["trim_start"], rows[0]["trim_end"], rows[0]["untrimmed_duration"]) == (0.5, 1.5, 2.0)


def test_filter_writes_the_asr_views(tmp_path):
    recipe = tmp_path / "r.yaml"
    recipe.write_text("""language: mos
source: {type: local, path: .}
filter:
  min_score: null
  max_music_under_voice_db: -30
  variants:
    asr: {max_music_under_voice_db: null}
    fra: {languages: [fra]}
  negatives: {of: asr, max_share: 0.5}
  tagged: {of: asr}
""", encoding="utf-8")
    (tmp_path / "clips").mkdir()
    for i in range(3):
        sf.write(tmp_path / "clips" / f"c{i}.wav", np.zeros(4 * SR, dtype=np.float32), SR)
    rows = [nonspeech.annotate(trimmed_row(id="clean", untrimmed_audio_filepath="clips/c0.wav", lead_music=1.0,
                                           music_under_voice_db=-40)),
            nonspeech.annotate(trimmed_row(id="bed", untrimmed_audio_filepath="clips/c1.wav", music_under_voice_db=-20)),
            nonspeech.annotate(trimmed_row(id="fr", untrimmed_audio_filepath="clips/c2.wav", language="fra",
                                           text="Le lièvre et la hyène."))]
    manifest.write(tmp_path / "aligned.jsonl", rows)
    Pipeline(load_recipe(recipe, tmp_path)).filter()
    ids = lambda name: [r["id"] for r in manifest.read(tmp_path / name)]   # noqa: E731
    assert ids("final.jsonl") == ["clean"]
    assert ids("final_asr.jsonl") == ["clean", "bed"]
    assert ids("final_fra.jsonl") == ["fr"]
    assert ids("final_asr_negatives.jsonl") == ["clean_lead"]
    assert [r["text"] for r in manifest.read(tmp_path / "final_asr_tagged.jsonl")] == \
        ["<MUSIC> Wẽnnaam yeelame.", "<MUSIC> Wẽnnaam yeelame."]


def test_combine_merges_views(tmp_path):
    run = tmp_path / "tales"
    (run / "trimmed").mkdir(parents=True)
    sf.write(run / "trimmed" / "c0.wav", np.zeros(SR, dtype=np.float32), SR)
    row = {"id": "c0", "audio_filepath": "trimmed/c0.wav", "text": "Wẽnnaam.", "duration": 1.0}
    manifest.write(run / "final.jsonl", [row])
    manifest.write(run / "final_asr.jsonl", [row])
    combine([run], tmp_path / "v3")
    [r] = manifest.read(tmp_path / "v3" / "final_asr.jsonl")
    assert r["id"] == "tales_c0" and (tmp_path / "v3" / r["audio_filepath"]).exists()


def test_views_take_the_speaker_of_their_chapter(tmp_path):
    recipe = tmp_path / "r.yaml"
    recipe.write_text("language: mos\nsource: {type: local, path: .}\n", encoding="utf-8")
    pipe = Pipeline(load_recipe(recipe, tmp_path))
    final = [{"id": f"c{i}", "run": "t", "source": "s", "chapter": "ch1", "speaker_group": 0, "speaker_id": 1,
              "voice": "female"} for i in range(3)]
    manifest.write(tmp_path / "final_asr.jsonl", [
        {"id": "c0", "run": "t", "source": "s", "chapter": "ch1"},
        {"id": "extra", "run": "t", "source": "s", "chapter": "ch1"},
        {"id": "c0_lead", "run": "t", "source": "s", "chapter": "ch1", "is_nonspeech": True}])
    from fasospeechcorpora import speakers as sp
    pipe._label_views(final, sp.chapter_units(final))
    got = [(r["id"], r["speaker_id"], r["voice"]) for r in manifest.read(tmp_path / "final_asr.jsonl")]
    assert got == [("c0", 1, "female"), ("extra", 1, "female"), ("c0_lead", None, None)]


def test_export_writes_one_config_per_view(tmp_path):
    pytest.importorskip("datasets")
    from fasospeechcorpora.export import export
    (tmp_path / "clips").mkdir()
    sf.write(tmp_path / "clips" / "c0.wav", np.zeros(SR, dtype=np.float32), SR)
    row = nonspeech.annotate(trimmed_row(audio_filepath="clips/c0.wav", voice_filepath="clips/c0.wav",
                                         speaker_id=1, voice="female"))
    manifest.write(tmp_path / "final_asr.jsonl", [row])
    export([row], tmp_path, {"formats": ["hf"], "configs": ["tts", "asr"]}, "mos")
    from datasets import load_from_disk
    tts, asr = load_from_disk(str(tmp_path / "hf" / "tts")), load_from_disk(str(tmp_path / "hf" / "asr"))
    assert "denoised_audio" in tts.column_names and "denoised_audio" not in asr.column_names
    meta = asr.select_columns(["nonspeech_spans", "segment_type"])[0]          # no audio decoding needed
    assert asr.column_names[:3] == ["audio", "text", "duration"] and meta["nonspeech_spans"][0]["label"] == "music"
    assert meta["segment_type"] == "speech_with_edge_music"


def test_metadata_fills_fields_and_looks_up_values(tmp_path):
    recipe = tmp_path / "r.yaml"
    recipe.write_text("""language: mos
source: {type: local, path: .}
metadata:
  category: proverbe
  book: {from: book, map: {p1: "Proverbes en mooré vol. 1"}}
  note: "V1 contes {hf_split}"
""", encoding="utf-8")
    pipe = Pipeline(load_recipe(recipe, tmp_path))
    r = {"book": "p1", "hf_split": "vol3"}
    pipe._stamp(r)
    assert r == {"book": "Proverbes en mooré vol. 1", "hf_split": "vol3", "category": "proverbe", "note": "V1 contes vol3"}
    r = {"book": "p9"}
    pipe._stamp(r)
    assert r["book"] == "p9" and r["note"] == "V1 contes "


def test_export_config_can_take_part_of_a_view(tmp_path):
    pytest.importorskip("datasets")
    from datasets import load_from_disk

    from fasospeechcorpora.export import export
    (tmp_path / "clips").mkdir()
    sf.write(tmp_path / "clips" / "c0.wav", np.zeros(SR, dtype=np.float32), SR)
    rows = [nonspeech.annotate(trimmed_row(id=f"c{i}", audio_filepath="clips/c0.wav", voice_filepath="clips/c0.wav",
                                           category=cat)) for i, cat in enumerate(["conte", "proverbe", "conte"])]
    export(rows, tmp_path, {"formats": ["hf"], "configs": [{"name": "contes", "view": "tts", "where": {"category": "conte"}}]}, "mos")
    ds = load_from_disk(str(tmp_path / "hf" / "contes"))
    assert ds.num_rows == 2 and ds.column_names[:6] == ["audio", "text", "duration", "voice", "speaker_id", "denoised_audio"]


def test_export_configs_share_one_schema_even_with_empty_columns(tmp_path):
    pytest.importorskip("datasets")
    from datasets import load_from_disk

    from fasospeechcorpora.export import export
    (tmp_path / "clips").mkdir()
    sf.write(tmp_path / "clips" / "c0.wav", np.zeros(SR, dtype=np.float32), SR)
    base = dict(audio_filepath="clips/c0.wav", voice_filepath="clips/c0.wav", speaker_id=1, voice="female")
    rows = [nonspeech.annotate(trimmed_row(id="a", category="conte", score=0.9, **base)),
            nonspeech.annotate(trimmed_row(id="b", category="devinette", nonspeech_spans=[], **base))]   # no score
    export(rows, tmp_path, {"formats": ["hf"], "configs": [
        {"name": "contes", "view": "tts", "where": {"category": "conte"}},
        {"name": "devinettes", "view": "tts", "where": {"category": "devinette"}}]}, "mos")
    a, b = (load_from_disk(str(tmp_path / "hf" / n)).features for n in ("contes", "devinettes"))
    assert a == b and str(b["alignment_score"]) == "Value('float64')"

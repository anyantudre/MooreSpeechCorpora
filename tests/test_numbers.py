from fasospeechcorpora import manifest
from fasospeechcorpora.config import load_recipe
from fasospeechcorpora.numbers import MooreNumbers, write_numbers
from fasospeechcorpora.pipeline import Pipeline


def test_moore_numbers():
    n = MooreNumbers()
    assert [n(x) for x in (1, 6, 10, 12, 45, 100, 205, 1000)] == [
        "yembo", "yoobe", "piiga", "piig la a yi", "pis-naase la a nu", "koabga", "kobs-yiibu la nu", "tusri"]
    assert n(0) == ""


def test_write_numbers_only_touches_standalone_numbers():
    assert write_numbers("Tɩ ges seb-va-neng 45 soaba.", "mos") == "Tɩ ges seb-va-neng pis-naase la a nu soaba."
    assert write_numbers("(Hebre sak 12 gom-dulg 14)", "mos") == "(Hebre sak piig la a yi gom-dulg piig la a naase)"
    for t in ("sẽ pak 24h/24 ?", "(Yɩɩn-sõamyã 86:11)", "15fcfa", "3,5", "1-2", "0"):
        assert write_numbers(t, "mos") == t
    assert write_numbers("yʋʋm 10", "dyu") == "yʋʋm 10"         # no writer for this language yet


def test_filter_writes_numbers(tmp_path):
    recipe = tmp_path / "r.yaml"
    recipe.write_text("language: mos\nsource: {type: local, path: .}\n"
                      "filter: {numbers_to_words: true, no_digits: true, min_score: null}\n", encoding="utf-8")
    rows = [{"id": "a", "text": "Rɩt 6 pʋɩɩbo.", "duration": 2.0, "language": "mos", "qc_flags": ["noisy"]},
            {"id": "b", "text": "Sẽ pak 24h/24.", "duration": 2.0, "language": "mos"}]
    manifest.write(tmp_path / "aligned.jsonl", rows)
    Pipeline(load_recipe(recipe, tmp_path)).filter()
    out = manifest.read(tmp_path / "final.jsonl")
    assert [r["id"] for r in out] == ["a"]                  # b keeps its digits, so no_digits drops it
    assert out[0]["text"] == "Rɩt yoobe pʋɩɩbo." and out[0]["raw_text"] == "Rɩt 6 pʋɩɩbo."
    assert out[0]["qc_flags"] == ["noisy", "numbers_written_out"]

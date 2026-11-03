from fasospeechcorpora import codeswitch as cs
from fasospeechcorpora.transcribe import score_text

FRENCH = {"gouvernement": 5.0, "la": 7.0, "merci": 5.0, "beaucoup": 5.5, "école": 5.0, "paris": 5.0}
LEXICON = {"la", "nasaar", "dãmb", "sẽn", "bond", "yaa", "sõma", "a", "kẽng", "yiib"}


def labeller(**kw):
    return cs.Labeller("mos", LEXICON, zipf=lambda w, lang: FRENCH.get(w, 0.0), **kw)


def test_french_insertion_inside_a_moore_sentence():
    text = "Nasaar dãmb sẽn bond gouvernement la"
    labels = labeller()(text)
    assert labels == ["mos", "mos", "mos", "mos", "fra", "mos"]       # "la" is Mooré here: it is in the lexicon
    m = cs.metrics(text, labels, "mos")
    assert (m["cmi"], m["n_switch_points"], m["cs_type"], m["matrix_lang"]) == (16.67, 2, "intra", "mos")
    assert cs.tag_text(text, labels) == "Nasaar dãmb sẽn bond <fr>gouvernement</fr> la"
    assert score_text(cs.tag_text(text, labels)) == score_text(text)          # the scorer ignores the tags


def test_loans_markup_and_proper_nouns():
    assert labeller(loans={"gouvernement"})("bond gouvernement") == ["mos", "mos"]
    assert labeller()("Le lièvre 2", line_lang="fra") == ["fra", "fra", "none"]
    assert labeller()("a kẽng Paris") == ["mos", "mos", "mos"]               # a name follows the word before it
    assert labeller()("a kẽng l'école") == ["mos", "mos", "fra"]             # elided article is ignored


def test_inter_sentential_switch():
    text = "Yaa sõma. Merci beaucoup."
    m = cs.metrics(text, labeller()(text), "mos")
    assert m["cs_type"] == "inter" and m["n_switch_points"] == 1 and m["cmi"] == 50.0
    assert cs.metrics("Yaa sõma.", labeller()("Yaa sõma."), "mos")["cs_type"] == "none"


def test_span_cer_ignores_errors_on_french_words():
    ref, labels = "nasaar dãmb gouvernement", ["mos", "mos", "fra"]
    assert cs.span_cer(ref, "nasaar dãmb kuvɛrnma", labels, "mos") == 0.0
    assert cs.span_cer(ref, "nasar dãmb kuvɛrnma", labels, "mos") == round(1 / 11, 4)
    assert cs.span_cer(ref, "nasaar dãmb", labels, "fra") == 1.0
    assert cs.span_cer("gouvernement", "x", ["fra"], "mos") is None


def test_lexicon_needs_repeated_words():
    assert cs.build_lexicon(["yaa sõma", "yaa sõma", "yaa kẽng"], min_count=2) == {"yaa", "sõma"}


def test_detect_cs_step_scores_switched_clips_on_moore_words(tmp_path, monkeypatch):
    from fasospeechcorpora import manifest
    from fasospeechcorpora.config import load_recipe
    from fasospeechcorpora.pipeline import Pipeline

    real = cs.Labeller
    monkeypatch.setattr(cs, "Labeller", lambda *a, **k: real(*a, zipf=lambda w, lang: FRENCH.get(w, 0.0), **k))
    recipe = tmp_path / "r.yaml"
    recipe.write_text("language: mos\nsource: {type: local, path: .}\ndetect_cs: {glotlid: false, lexicon_min_count: 2}\n"
                      "filter: {min_score: null, max_cer: 0.25}\n", encoding="utf-8")
    rows = [{"id": "mix", "text": "Nasaar dãmb gouvernement", "duration": 2.0, "language": "mos", "cer": 0.5,
             "hyp_m": "nasaar dãmb kuvɛrnma"},
            {"id": "plain", "text": "Yaa sõma la", "duration": 2.0, "language": "mos", "cer": 0.0, "hyp_m": "yaa sõma la"},
            {"id": "plain2", "text": "La beaucoup yaa", "duration": 2.0, "language": "mos", "cer": 0.0},
            {"id": "fr", "text": "Merci beaucoup", "duration": 2.0, "language": "fra"}]
    manifest.write(tmp_path / "aligned.jsonl", rows)
    pipe = Pipeline(load_recipe(recipe, tmp_path))
    pipe.detect_cs()
    out = {r["id"]: r for r in manifest.read(tmp_path / "aligned.jsonl")}
    assert out["mix"]["cs_type"] == "intra" and out["mix"]["cer_matrix"] == 0.0
    assert out["mix"]["text_tagged"] == "Nasaar dãmb <fr>gouvernement</fr>"
    assert out["plain"]["cs_type"] == "none" and "cer_matrix" not in out["plain"]      # "la" is in 2 Mooré lines
    assert out["plain2"]["token_lang"] == ["mos", "fra", "mos"]
    assert out["fr"]["token_lang"] == ["fra", "fra"] and out["fr"]["lang_source"] == "markup"
    assert (tmp_path / "codeswitch" / "candidates.tsv").read_text(encoding="utf-8") == \
        "token\tcount\ngouvernement\t1\nbeaucoup\t1\n"
    pipe.filter()                       # the code-switched clip passes on its Mooré words despite cer 0.5
    assert [r["id"] for r in manifest.read(tmp_path / "final.jsonl")] == ["mix", "plain", "plain2"]

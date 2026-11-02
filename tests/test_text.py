from voxfaso.config import Language, load_language
from voxfaso.text import foreign_ratio, split_sentences


def test_split_keeps_closing_quotes():
    lang = Language(code="mos", name="Mooré")
    text = "Wẽnnaam yeelame: «Bɩ vẽenem zĩndi.» La vẽenem zĩndame. Yaa pipi daarã!"
    assert split_sentences(text, lang) == [
        "Wẽnnaam yeelame: «Bɩ vẽenem zĩndi.»", "La vẽenem zĩndame.", "Yaa pipi daarã!"]


def test_drop_numbers():
    lang = Language(code="x", name="x", drop_numbers=True)
    assert split_sentences("Gen 1.2 here. Plain text.", lang) == ["Plain text."]


def test_foreign_ratio_accepts_tone_marks():
    mos = load_language("mos")
    assert foreign_ratio("Wẽnnaam yeelame", mos) == 0
    assert foreign_ratio("Clémence rime avec puissance", mos) > 0


def test_bundled_languages():
    for code in ["mos", "dyu", "gux", "ffm", "fuh"]:
        assert load_language(code).code == code


def test_split_after_single_guillemet():
    lang = Language(code="mos", name="Mooré")
    text = "Wẽnnaam pʋda sa-gãongã yʋʋr tɩ ‹saasẽ.› Zaabr ne yibeoog zĩndame."
    assert split_sentences(text, lang) == ["Wẽnnaam pʋda sa-gãongã yʋʋr tɩ ‹saasẽ.›", "Zaabr ne yibeoog zĩndame."]

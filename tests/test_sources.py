from fasospeechcorpora.config import load_language
from fasospeechcorpora.sources.bible_com import next_chapter_url, parse_chapter
from fasospeechcorpora.sources.local import read_text_file
from fasospeechcorpora.sources.ipsapps import page_lines, reading_lines

# Shape of a bible.com chapter page (class prefixes are hashed and change between deploys)
CHAPTER = """
<html><body><h1>Sɩngre 1</h1>
<div class="x1_chapter" data-usfm="GEN.1">
  <div class="x1_label">1</div>
  <div class="x1_s"><span class="x1_heading">Dũniyã naanego</span></div>
  <div class="x1_p">
    <span class="x1_verse" data-usfm="GEN.1.1"><span class="x1_label">1</span>
      <span class="x1_content">Sɩngr wẽndẽ, Wẽnnaam naana yĩngr la tẽnga. </span></span>
    <span class="x1_verse" data-usfm="GEN.1.2"><span class="x1_label">2</span><span class="x1_content">Tẽngã</span>
      <span class="x1_note"><span class="x1_label">#</span><span class="x1_body"><span class="x1_content">a footnote</span></span></span>
      <span class="x1_content"> rag n ka tar yalẽ ye.</span></span>
  </div>
</div>
<a aria-label="Next Chapter" href="/bible/3058/GEN.2.MPBU">next</a>
</body></html>
"""


def test_parse_chapter_skips_labels_and_notes():
    title, paragraphs = parse_chapter(CHAPTER, "GEN.1")
    assert title == "Sɩngre 1"
    assert paragraphs == ["Dũniyã naanego",
                          "Sɩngr wẽndẽ, Wẽnnaam naana yĩngr la tẽnga. Tẽngã rag n ka tar yalẽ ye."]


def test_parse_chapter_without_headings():
    _, paragraphs = parse_chapter(CHAPTER, "GEN.1", include_headings=False)
    assert paragraphs[0].startswith("Sɩngr")


def test_next_chapter():
    assert next_chapter_url(CHAPTER) == "https://www.bible.com/bible/3058/GEN.2.MPBU"


PROVERB_PAGE = """
<div class="m"><div id="T2a" class="txs"><span class="bd">42 </span><span class="bd">K</span><span class="bd">a reng roog la gõeem ye.</span></div></div>
<div class="m"><div id="T2b" class="txs"><span class="bdit">(S</span><span class="bdit">e coucher avant les autres ne fait pas dormir avant eux).</span></div></div>
<div class="m"><div id="T2c" class="txs"><span class="bdit">K</span><span class="bd">a reng roog la gõeem ye.</span></div></div>
<div class="m"><div id="T1b" class="txs"><span class="it">La perdrix dit que tant qu</span><span class="it">’</span><span class="it">il y a la vie.</span></div></div>
"""


def test_ipsapps_lines_join_drop_caps_and_detect_translation():
    assert page_lines(PROVERB_PAGE) == [
        ("Ka reng roog la gõeem ye.", False),
        ("Se coucher avant les autres ne fait pas dormir avant eux.", True),
        ("Ka reng roog la gõeem ye.", False),
        ("La perdrix dit que tant qu’il y a la vie.", True),
    ]


def test_bilingual_page_keeps_one_line_per_reading():
    mos = load_language("mos")
    page = [("Zĩrẽ zoeta yʋʋm tusri,", False), ("tɩ sɩd wa yõk-a raar a ye.", False),
            ("En une journée de course,", True), ("la vérité rattrape le mensonge.", True),
            ("Zĩrẽ zoeta yʋʋm tusri,", False), ("tɩ sɩd wa yõk-a raar a ye.", False)]
    lines, langs = reading_lines(page, mos, "fra")
    assert langs == ["mos", "fra", "mos"]
    assert lines[0] == "Zĩrẽ zoeta yʋʋm tusri, tɩ sɩd wa yõk-a raar a ye."


def test_monolingual_page_is_split_into_sentences():
    lines, langs = reading_lines([("A ra yaa. B ra be.", False)], load_language("mos"), "fra")
    assert lines == ["A ra yaa.", "B ra be."] and langs == ["mos", "mos"]


def test_local_transcript_is_split_into_sentences(tmp_path):
    f = tmp_path / "tale.txt"
    f.write_text("Nin-kẽem a yembr kibare.\nNin-kẽem a yembr n wa n yik a zak pʋgẽ. La, a bi-bilf yikame.\n",
                 encoding="utf-8")
    assert read_text_file(f, load_language("mos")) == {"lines": [
        "Nin-kẽem a yembr kibare.", "Nin-kẽem a yembr n wa n yik a zak pʋgẽ.", "La, a bi-bilf yikame."]}


def test_local_transcript_can_skip_a_title_line(tmp_path):
    f = tmp_path / "GEN_1.txt"
    f.write_text("Sɩngre 1\nWẽnnaam naana saasa.\n", encoding="utf-8")
    assert read_text_file(f, load_language("mos"), skip_lines=1) == {"lines": ["Wẽnnaam naana saasa."]}


def test_local_audacity_labels_become_segments(tmp_path):
    f = tmp_path / "tale.txt"
    f.write_text("0.000000\t5.350000\tNin-kẽem a yembr kibare.\n5.36, 10.15, \"La, a bi-bilf yikame.\"\n",
                 encoding="utf-8")
    assert read_text_file(f, load_language("mos")) == {"segments": [
        {"start": 0.0, "end": 5.35, "text": "Nin-kẽem a yembr kibare."},
        {"start": 5.36, "end": 10.15, "text": "La, a bi-bilf yikame."}]}


def test_hf_dataset_subset_limits_the_glob_to_one_config():
    from fnmatch import fnmatch

    from fasospeechcorpora.sources.hf_dataset import HFDataset

    files = ["datasets/u/r/data/train-0.parquet", "datasets/u/r/devinettes/train-0.parquet"]
    pick = lambda pat: [f for f in files if fnmatch(f, pat)]          # noqa: E731
    assert pick(HFDataset.pattern("u/r", "train")) == files
    assert pick(HFDataset.pattern("u/r", "train", "devinettes")) == ["datasets/u/r/devinettes/train-0.parquet"]


def test_drop_repeated_lines_keeps_each_passage_once():
    from fasospeechcorpora.text import drop_repeated_lines

    # moore-speech-contes vol5: paragraphs first, then the same paragraphs in pieces
    lines = ["Daar a yembre, yõensã tigma.", "B sɩd yeele : « D sã n pa bao ».", "Daar a yembre,", "yõensã tigma.",
             "B sɩd yeele :", "« D sã n pa bao ».", "D na n daa lombr.", "Rẽ, a sã n na.", "D na n daa lombr.",
             "Rẽ,", "a sã n na."]
    assert drop_repeated_lines(lines) == ["Daar a yembre,", "yõensã tigma.", "B sɩd yeele :", "« D sã n pa bao ».",
                                          "D na n daa lombr.", "Rẽ,", "a sã n na."]
    assert drop_repeated_lines(["Yaa sõma.", "Wẽnnaam yeelame."]) == ["Yaa sõma.", "Wẽnnaam yeelame."]


def test_hf_dataset_rejoins_a_chapter(tmp_path):
    import numpy as np
    import soundfile as sf

    from fasospeechcorpora.config import load_language
    from fasospeechcorpora.sources.hf_dataset import HFDataset

    recs = []
    for i, text in enumerate(["Yaa sõma la.", "Yaa sõma", "la."]):
        sf.write(tmp_path / f"c{i}.wav", np.full(16_000, i / 10, dtype=np.float32), 16_000)
        recs.append({"id": f"c{i}", "audio_filepath": f"c{i}.wav", "source": "hf:u/r/vol5",
                     "meta": {"hf_split": "vol5", "chapter": "01-B021"}, "segments": [{"start": 0, "end": 1, "text": text}]})
    src = HFDataset(load_language("mos"), repo="u/r", rejoin="chapter", dedupe_lines=True)
    [rec] = src._rejoin(recs, tmp_path)
    assert rec["id"] == "vol5_01_B021" and rec["pieces"] == 3 and rec["lines"] == ["Yaa sõma", "la."]
    wav, sr = sf.read(tmp_path / rec["audio_filepath"])
    assert len(wav) == 3 * 16_000 and abs(wav[-1] - 0.2) < 1e-3

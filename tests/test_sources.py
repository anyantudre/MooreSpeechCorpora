from fasospeechcorpora.config import load_language
from fasospeechcorpora.sources.bible_com import next_chapter_url, parse_chapter
from fasospeechcorpora.sources.ipsapps import page_lines

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

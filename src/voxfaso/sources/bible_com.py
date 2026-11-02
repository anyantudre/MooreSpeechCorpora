"""Audio Bibles from bible.com (YouVersion), any version that has audio.

Parsing relies on stable markers only: `data-usfm` verse ids, class-name suffixes
(`_content`, `_heading`, `_note`) and the "Next Chapter" aria-label, so site redesigns
that rename hashed CSS classes do not break it.

Check the terms of use before running: YouVersion content is for personal use, and
publishing a derived dataset needs the rights holder's permission.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from parsel import Selector

from ..text import normalize, split_sentences
from .base import Source, register

BASE = "https://www.bible.com"
CONTENT = ("//span[(contains(@class, '_content') or contains(@class, '_heading'))"
           " and not(ancestor::span[contains(@class, '_note')])]")


def parse_chapter(html: str, chapter_usfm: str, include_headings: bool = True) -> tuple[str, list[str]]:
    """Return (title, paragraphs) for one chapter page."""
    sel = Selector(text=html)
    title = normalize(sel.css("h1::text").get(default=""))
    paragraphs = []
    for block in sel.xpath(f'//div[@data-usfm="{chapter_usfm}"]/div'):
        cls = block.attrib.get("class", "")
        if cls.endswith("_label"):                       # big chapter number
            continue
        spans = block.xpath("." + CONTENT)
        if not include_headings:
            spans = [s for s in spans if "_heading" not in s.attrib.get("class", "")]
        text = normalize(" ".join(t for s in spans for t in s.xpath(".//text()").getall()))
        if text:
            paragraphs.append(text)
    return title, paragraphs


def next_chapter_url(html: str) -> str | None:
    href = Selector(text=html).css('a[aria-label="Next Chapter"]::attr(href)').get()
    return urljoin(BASE, href) if href else None


@register("bible_com")
class BibleCom(Source):
    """Params: version (int, e.g. 3058), abbreviation (e.g. "MPBU"), start (e.g. "GEN.1"),
    stop (optional, last chapter to fetch, e.g. "GEN.50"), include_headings (default true),
    include_title (default false: narrators read the chapter number differently from the page)."""

    def fetch(self, raw_dir: Path) -> list[dict]:
        p = self.params
        version, abbr = p["version"], p["abbreviation"]
        url = f"{BASE}/bible/{version}/{p.get('start', 'GEN.1')}.{abbr}"
        stop = p.get("stop")
        records = []
        while url and (self.limit is None or len(records) < self.limit):
            usfm = re.search(rf"/bible/{version}/([A-Z0-9]+\.\d+)\.", url).group(1)
            item_id = usfm.replace(".", "_")
            audio_path = raw_dir / f"{item_id}.mp3"
            html = self.get(url).text
            title, paragraphs = parse_chapter(html, usfm, p.get("include_headings", True))
            lines = ([title] if title and p.get("include_title", False) else [])
            for para in paragraphs:
                lines += split_sentences(para, self.lang)
            audio_page = self.get(url.replace("/bible/", "/audio-bible/")).text
            audio_url = Selector(text=audio_page).css("audio::attr(src)").get()
            if audio_url and lines:
                self.download(audio_url, audio_path)
                records.append({"id": item_id, "audio_filepath": audio_path.name, "lines": lines,
                                "source": f"bible.com/{version}", "chapter": usfm})
            if stop and usfm == stop:
                break
            url = next_chapter_url(html)
        return records

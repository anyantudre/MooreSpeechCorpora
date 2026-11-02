"""SIL "ipsapps" audio books (e.g. media.ipsapps.org/mos/ora/...): tales, proverbs, riddles.

Each `div.txs` on a page is one spoken line. Spans with class `bd` are in the book's language,
spans with class `bdit` or `it` (italics) are the translation; a line belongs to whichever has more text.
(The first letter of a line is often a separate drop-cap span, so lines are joined without spaces.)

Two layouts, picked with `mode`:
  chapters    one audio file per page (tales)
  timestamps  one audio file for the whole book; each page gives `startTime`/`stopTime` (proverbs)
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from parsel import Selector

from .. import audio
from ..text import normalize, split_sentences
from .base import Source, register


def page_lines(html: str, line_css: str = "div.txs", translation_classes: tuple = ("bdit", "it")) -> list[tuple[str, bool]]:
    """Return (text, is_translation) for every line on the page."""
    out = []
    for div in Selector(text=html).css(line_css):
        text = normalize("".join(div.css("::text").getall()))
        if not text:
            continue
        trans = sum(len(t) for t in div.css(", ".join(f".{c} ::text" for c in translation_classes)).getall())
        is_translation = trans > len(text.replace(" ", "")) / 2
        text = re.sub(r"^\d+\s*", "", text)                    # proverb number
        if is_translation:
            text = normalize(text.replace("(", "").replace(")", ""))
        if text:
            out.append((text, is_translation))
    return out


def reading_lines(page: list[tuple[str, bool]], lang, tlang: str) -> tuple[list[str], list[str]]:
    """Turn page lines into the lines to align, with their language.

    Monolingual pages (tales) are split into sentences. Bilingual pages (proverbs) keep one line per
    reading: consecutive lines in the same language are joined, so a proverb printed on two lines
    stays one clip and pairs with its whole translation."""
    lines, langs = [], []
    if not any(is_tr for _, is_tr in page):
        for text, _ in page:
            for sentence in split_sentences(text, lang):
                lines.append(sentence)
                langs.append(lang.code)
        return lines, langs
    for text, is_tr in page:
        code = tlang if is_tr else lang.code
        if langs and langs[-1] == code:
            lines[-1] = f"{lines[-1]} {text}"
        else:
            lines.append(text)
            langs.append(code)
    return lines, langs


@register("ipsapps")
class IpsApps(Source):
    """Params: start (first page URL), mode ("chapters" | "timestamps"),
    translation_language (default "fra"), line_selector (default "div.txs")."""

    def fetch(self, raw_dir: Path) -> list[dict]:
        p = self.params
        mode = p.get("mode", "chapters")
        tlang = p.get("translation_language", "fra")
        url = p["start"]
        records = []
        book_audio, book_wav = None, None
        while url and (self.limit is None or len(records) < self.limit):
            html = self.get(url).text
            sel = Selector(text=html)
            item_id = url.rstrip("/").split("/")[-1].removesuffix(".html")
            audio_url = sel.css("audio source::attr(src), audio::attr(src)").get()
            lines, langs = reading_lines(page_lines(html, p.get("line_selector", "div.txs")), self.lang, tlang)
            if len(lines) >= 2 and lines[0] == lines[1]:           # page title repeated as first line
                lines, langs = lines[1:], langs[1:]
            record = {"id": item_id, "lines": lines, "source": url.split("/ora/")[0]}
            if tlang in langs:
                record["line_languages"] = langs
                record["translation"] = " ".join(t for t, l in zip(lines, langs) if l == tlang)
            if mode == "chapters" and audio_url and lines:
                path = self.download(urljoin(url, audio_url), raw_dir / f"{item_id}.mp3")
                records.append({**record, "audio_filepath": path.name})
            elif mode == "timestamps" and audio_url and lines:
                start = re.search(r"var startTime\s*=\s*([\d.]+)", html)
                stop = re.search(r"var stopTime\s*=\s*([\d.]+)", html)
                if start and stop:
                    if book_audio is None:
                        book_audio = self.download(urljoin(url, audio_url), raw_dir / "book.mp3")
                    clip = raw_dir / f"{item_id}.wav"
                    if not clip.exists():
                        if book_wav is None:
                            book_wav = audio.load(book_audio)          # decode the book once
                        a, b = (int(float(m.group(1)) * 16_000) for m in (start, stop))
                        audio.save(clip, book_wav[a:b])
                    records.append({**record, "audio_filepath": clip.name})
            nxt = sel.css('a[title="Next Chapter"]::attr(href)').get()
            url = urljoin(url, nxt) if nxt and nxt.strip() else None
        return records

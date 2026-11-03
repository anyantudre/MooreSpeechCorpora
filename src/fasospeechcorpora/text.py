"""Text cleanup and sentence splitting, driven by the language config (no ICU needed)."""
from __future__ import annotations

import re
import unicodedata

from .config import Language


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str, lang: Language) -> list[str]:
    """Split after sentence-ending punctuation followed by a space (and optional closing quotes)."""
    text = normalize(text)
    if not text:
        return []
    ends = re.escape(lang.sentence_end)
    closers = "\"'»”’›)"
    # split on the space after an end mark, or after an end mark plus one closing quote
    parts = re.split(rf"(?:(?<=[{ends}])|(?<=[{ends}][{closers}]))\s+", text)
    sentences = [p.strip() for p in parts if p.strip()]
    if lang.drop_numbers:
        sentences = [s for s in sentences if not re.search(r"\d", s)]
    return sentences


def foreign_ratio(text: str, lang: Language) -> float:
    """Share of letters in `text` that are not in the language's alphabet (0 when no alphabet is set)."""
    if not lang.letters:
        return 0.0
    allowed = set(lang.letters.lower())
    letters = [c for c in unicodedata.normalize("NFC", text.lower()) if c.isalpha()]
    if not letters:
        return 0.0
    # compare base letters too, so tone marks and nasal tildes on allowed vowels are accepted
    def ok(c: str) -> bool:
        base = unicodedata.normalize("NFD", c)[0]
        return c in allowed or base in allowed
    return sum(not ok(c) for c in letters) / len(letters)


def clean_text(text: str) -> str:
    """Tidy a transcript for training without changing its words.

    Drops a leading item number ("7 Põor naaf…"), the space before punctuation ("kibare ."),
    dialogue dashes after a colon (":- Ad-y"), unifies apostrophes (’ ‘ ` -> ') and spaces,
    and keeps one copy of a sentence printed twice in a row.
    """
    t = normalize(text)
    t = re.sub(r"^\d+[.)]?\s+", "", t)
    t = re.sub(r"[’‘`]", "'", t)
    t = re.sub(r":\s*-\s*", ": ", t)
    t = re.sub(r"\s+([.,!?;:»])", r"\1", t)
    t = re.sub(r"«\s+", "«", t)
    t = normalize(t)
    sentences = re.split(r"(?<=[.!?»])\s+", t)
    half = len(sentences) // 2
    if half and len(sentences) % 2 == 0:                          # "X. X." printed twice
        a, b = " ".join(sentences[:half]), " ".join(sentences[half:])
        if re.sub(r"\W", "", a) == re.sub(r"\W", "", b):
            return b                                              # the second copy has the cleaner spacing
    return t


def drop_repeated_lines(lines: list[str], window: int = 40, max_parts: int = 8) -> list[str]:
    """Keep each passage once when a text gives it twice, whole and then in pieces.

    A line equal to a run of 2+ other lines nearby (a paragraph that also appears split) is dropped,
    and of two equal lines the later copy is kept, as in texts listing paragraphs before their pieces.
    Lines are compared lowercased, without punctuation.
    """
    def norm(t: str) -> str:
        t = unicodedata.normalize("NFC", t.lower())
        return " ".join("".join(c if unicodedata.category(c)[0] in "LM" else " " for c in t).split())

    keys = [norm(t) for t in lines]
    drop = {i for i, k in enumerate(keys) if not k}
    for i, k in enumerate(keys):
        if i in drop:
            continue
        for j in range(max(0, i - window), min(len(keys), i + window)):
            acc = []
            for m in range(j, min(len(keys), j + max_parts)):
                if m == i:
                    break
                acc.append(keys[m])
                joined = " ".join(acc)
                if len(acc) >= 2 and joined == k:
                    drop.add(i)
                if len(joined) >= len(k):
                    break
            if i in drop:
                break
    last: dict[str, int] = {}
    for i, k in enumerate(keys):
        if i not in drop:
            if k in last:
                drop.add(last[k])
            last[k] = i
    return [t for i, t in enumerate(lines) if i not in drop]

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

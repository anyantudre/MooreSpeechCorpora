"""Write numbers in words, so transcripts keep no digits.

Mooré numbers follow the MooreConverter by Salif Sawadogo (https://github.com/sawallesalfo), for plain
numbers (not prices). Only whole numbers standing alone are written out: digits glued to letters or
other numbers ("24h/24", "86:11", "15fcfa", "3,5") are left as they are, since reading them needs a
person, and the filter's `no_digits` rule still catches them.
"""
from __future__ import annotations

import re

# a whole number, not part of a word, a time, a ratio, a decimal or a range
_NUMBER = re.compile(r"(?<![\w/:.,\-])\d+(?![\w/%]|[.,:\-]\d)")


class MooreNumbers:
    """Cardinal numbers in Mooré (Salif Sawadogo's MooreConverter, plain numbers only)."""

    units = ["", "yembo", "yiibu", "tãabo", "naase", "nu", "yoobe", "yopoe", "nii", "wae"]
    tens = ["", "piiga", "pisi", "pis-tã", "pis-naase", "pis-nu", "pis-yoobe", "pis-yopoe", "pis-nii", "pis-wae"]
    short = {"yembo": "ye", "yiibu": "yi", "tãabo": "tã"}      # unit forms after "la a"

    def __call__(self, n: int) -> str:
        if n == 0:
            return ""                                         # no agreed word: keep the digit
        if n < 10:
            return self.units[n]
        if n == 10:
            return self.tens[1]
        if n < 20:
            u = self.units[n - 10]
            return "piig la a " + self.short.get(u, u)
        if n < 100:
            t, u = self.tens[n // 10], self.units[n % 10]
            return t + " la a " + self.short.get(u, u) if u else t
        if n < 1000:
            h, rest = divmod(n, 100)
            out = "koabga" if h == 1 else "kobs-" + {"yembo": "ye", "tãabo": "tã"}.get(self.units[h], self.units[h])
            return out + " la " + self(rest) if rest else out
        if n < 1_000_000:
            k, rest = divmod(n, 1000)
            out = "tusri" if k == 1 else ("tus " if n >= 10_000 else "tusa ") + self(k)
            return out + " la " + self(rest) if rest else out
        m, rest = divmod(n, 1_000_000)
        out = self(m) + " milyɔɔng"
        return out + " " + self(rest) if rest else out


WRITERS = {"mos": MooreNumbers()}


def write_numbers(text: str, lang: str) -> str:
    """Replace each standalone whole number in `text` with its words in `lang`. Languages without a
    number writer, and numbers it has no word for, keep their digits."""
    writer = WRITERS.get(lang)
    if writer is None or not text:
        return text
    return _NUMBER.sub(lambda m: writer(int(m.group())) or m.group(), text)

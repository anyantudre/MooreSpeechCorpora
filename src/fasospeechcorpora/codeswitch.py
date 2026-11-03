"""Token-level language labels for code-switched speech (e.g. Mooré with French words).

The per-token list is the source of truth; everything else is derived from it:

  token_lang       one label per whitespace token: the matrix language (e.g. mos), an embedded
                   language (e.g. fra), or "none" (tags, numbers, punctuation)
  text_tagged      the text with <fr>...</fr> around runs of French tokens
  cmi              code-mixing index of Das & Gambäck (0-100)
  n_switch_points  language changes between neighbouring tokens
  cs_type          none / inter (each sentence is one language) / intra (a switch inside a sentence)
  matrix_lang      the language with the most tokens
  cer_matrix       CER counted on the matrix-language words only, from the stored ASR transcripts

Rules, in order (closed lists, so labels can be recomputed when a list changes):
  1. a line whose `language` is an embedded language (e.g. a French proverb reading) is all embedded;
  2. a token in the loan list takes the matrix language;
  3. a token is embedded when every part of it (2+ letters) is a common word of that language
     (wordfreq Zipf >= min_zipf) and is not in the matrix-language lexicon built from the corpus;
  4. a capitalised token inside a sentence (a proper noun) takes the label of the word before it.

Text LID decides; audio LID (MMS-LID) is only a cross-check that flags disagreements for review.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .transcribe import score_text

TAG_FOR = {"fra": "fr", "eng": "en", "dyu": "dyu"}
LOAN_LEXICON_VERSION = "0"


def parts(token: str) -> list[str]:
    p = score_text(token).split()
    return [x for x in p if len(x) >= 2] or p


def build_lexicon(texts, min_count: int = 3) -> set[str]:
    c = Counter(x for t in texts for tok in t.split() for x in score_text(tok).split())
    return {w for w, n in c.items() if n >= min_count}


class Labeller:
    """Defaults tuned on the Mooré proverbs (Mooré lines and their French readings, labelled by the
    books): words of 4+ letters, Zipf >= 3, and more common in French than in English. That called
    0.02% of Mooré tokens French and caught 88% of French content words; shorter words and English
    look-alikes (bugs, more, make) were most of the errors."""

    def __init__(self, matrix: str, lexicon: set[str], embedded: tuple[str, ...] = ("fra",),
                 loans: set[str] | None = None, min_zipf: float = 3.0, min_len: int = 4,
                 not_english: bool = True, zipf=None):
        self.matrix, self.lexicon, self.embedded = matrix, lexicon, embedded
        self.loans = {score_text(w) for w in (loans or set())}
        self.min_zipf, self.min_len = min_zipf, min_len
        if zipf is None:
            from functools import lru_cache

            from wordfreq import zipf_frequency
            iso1 = {"fra": "fr", "eng": "en"}

            @lru_cache(maxsize=None)
            def zipf(w, lang):
                z = zipf_frequency(w, iso1.get(lang, lang))
                return 0.0 if not_english and lang != "eng" and zipf_frequency(w, "en") >= z else z
        self.zipf = zipf

    def token(self, tok: str) -> str:
        p = parts(tok)
        if not p or not any(c.isalpha() for c in tok):
            return "none"
        if " ".join(p) in self.loans or all(x in self.loans for x in p):
            return self.matrix
        for lang in self.embedded:
            if all(len(x) >= self.min_len and x not in self.lexicon and self.zipf(x, lang) >= self.min_zipf
                   for x in p):
                return lang
        return self.matrix

    def __call__(self, text: str, line_lang: str | None = None) -> list[str]:
        toks = text.split()
        if line_lang in self.embedded:
            return ["none" if not any(c.isalpha() for c in t) else line_lang for t in toks]
        labels = [self.token(t) for t in toks]
        for i, t in enumerate(toks):                     # proper nouns follow the word before them
            if i and t[:1].isupper() and not re.search(r"[.!?]$", toks[i - 1]) and labels[i] != "none":
                prev = next((labels[j] for j in range(i - 1, -1, -1) if labels[j] != "none"), None)
                if prev:
                    labels[i] = prev
        return labels


def metrics(text: str, labels: list[str], matrix_default: str) -> dict:
    langs = [x for x in labels if x != "none"]
    n, u = len(labels), labels.count("none")
    counts = Counter(langs)
    cmi = 0.0 if n == u or len(counts) < 2 else round(100 * (1 - max(counts.values()) / (n - u)), 2)
    switches = sum(1 for a, b in zip(langs, langs[1:]) if a != b)
    matrix = max(counts, key=lambda k: (counts[k], k == matrix_default)) if counts else matrix_default
    if len(counts) < 2:
        kind = "none"
    else:
        sentences, cur = [], []
        for t, lab in zip(text.split(), labels):
            if lab != "none":
                cur.append(lab)
            if re.search(r"[.!?]$", t):
                sentences.append(cur)
                cur = []
        sentences.append(cur)
        kind = "inter" if all(len(set(s)) <= 1 for s in sentences) else "intra"
    return {"token_lang": labels, "cmi": cmi, "n_switch_points": switches, "cs_type": kind,
            "matrix_lang": matrix, "n_langs": len(counts), "loan_lexicon_version": LOAN_LEXICON_VERSION}


def tag_text(text: str, labels: list[str], embedded: tuple[str, ...] = ("fra",)) -> str:
    """Wrap each run of embedded-language tokens in <fr>...</fr>. A "none" token (a number,
    a dash) between two tokens of the same embedded language stays inside the run."""
    toks = text.split()
    lab = list(labels)
    for i in range(1, len(lab) - 1):
        if lab[i] == "none" and lab[i - 1] == lab[i + 1] and lab[i - 1] in embedded:
            lab[i] = lab[i - 1]
    out, i = [], 0
    while i < len(toks):
        if lab[i] in embedded:
            j = i
            while j < len(toks) and lab[j] == lab[i]:
                j += 1
            t = TAG_FOR.get(lab[i], lab[i])
            out.append(f"<{t}>" + " ".join(toks[i:j]) + f"</{t}>")
            i = j
        else:
            out.append(toks[i])
            i += 1
    return " ".join(out)


def span_cer(ref: str, hyp: str, labels: list[str], keep: str) -> float | None:
    """CER over the reference words labelled `keep`. Errors are found with a character edit
    alignment; an insertion is charged to the reference character before it."""
    toks = ref.split()
    chars, mask = [], []
    for tok, lab in zip(toks, labels):
        norm = score_text(tok)
        if not norm:
            continue
        if chars:
            chars.append(" ")
            mask.append(lab == keep and mask[-1])
        chars.extend(norm)
        mask.extend([lab == keep] * len(norm))
    r, h = chars, list(score_text(hyp))
    total = sum(mask)
    if not total:
        return None
    n, m = len(r), len(h)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    errors, i, j = 0, n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (r[i - 1] != h[j - 1]):
            errors += (r[i - 1] != h[j - 1]) and mask[i - 1]
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            errors += mask[i - 1]
            i -= 1
        else:
            errors += mask[i - 1] if i else mask[0]
            j -= 1
    return round(errors / total, 4)


def read_loans(path: str | Path | None) -> set[str]:
    if not path or not Path(path).exists():
        return set()
    return {l.split("#")[0].strip() for l in Path(path).read_text(encoding="utf-8").splitlines()
            if l.split("#")[0].strip()}

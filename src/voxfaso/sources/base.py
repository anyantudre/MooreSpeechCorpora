from __future__ import annotations

import time
from pathlib import Path

import requests

from ..config import Language

SOURCES: dict[str, type["Source"]] = {}
USER_AGENT = "voxfaso (+https://github.com/anyantudre/MooreSpeechCorpora)"


def register(name: str):
    def wrap(cls):
        SOURCES[name] = cls
        cls.type = name
        return cls
    return wrap


def get_source(lang: Language, params: dict) -> "Source":
    params = dict(params)
    kind = params.pop("type")
    if kind not in SOURCES:
        raise ValueError(f"Unknown source type '{kind}'. Available: {', '.join(sorted(SOURCES))}")
    return SOURCES[kind](lang, **params)


class Source:
    """Fetch audio (and text when it exists) into `raw_dir`.

    `fetch` returns one record per audio file:
      {"id", "audio_filepath", "lines": [...sentences...] or None, "source", ...extra}
    Paths are relative to `raw_dir`. Sources must skip files that already exist (resumable).
    """

    type = "base"

    def __init__(self, lang: Language, limit: int | None = None, delay: float = 1.0, **params):
        self.lang = lang
        self.limit = limit          # max number of items (chapters, pages, videos); handy for tests
        self.delay = delay          # seconds between requests, to be polite to servers
        self.params = params
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def fetch(self, raw_dir: Path) -> list[dict]:
        raise NotImplementedError

    def get(self, url: str) -> requests.Response:
        time.sleep(self.delay)
        r = self.session.get(url, timeout=60)
        r.raise_for_status()
        if "charset" not in r.headers.get("content-type", "").lower():
            r.encoding = "utf-8"            # requests would fall back to Latin-1 and garble the text
        return r

    def download(self, url: str, dest: Path) -> Path:
        if dest.exists() and dest.stat().st_size > 0:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with self.session.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        tmp.replace(dest)
        time.sleep(self.delay)
        return dest

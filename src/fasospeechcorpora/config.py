"""Language and recipe configuration, loaded from YAML."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

LANGUAGES_DIR = Path(__file__).parent / "languages"


@dataclass
class Language:
    code: str                          # ISO 639-3, e.g. "mos"
    name: str
    letters: str = ""                  # alphabet of the language, used by the text filter
    sentence_end: str = ".!?"
    drop_numbers: bool = False         # drop sentences that contain digits
    uroman_code: str | None = None     # language hint for uroman (defaults to `code`)
    mms_code: str | None = None        # code for the legacy fairseq MMS aligner (defaults to `code`)
    asr_model: str | None = None       # optional Hugging Face ASR model for pseudo-labelling


@dataclass
class Recipe:
    name: str
    language: Language
    source: dict[str, Any]
    output_dir: Path
    steps: list[str] = field(default_factory=lambda: ["fetch", "prepare", "align", "filter", "export"])
    sample_rate: int = 16_000
    enhance: dict[str, Any] = field(default_factory=dict)
    trim: dict[str, Any] = field(default_factory=dict)
    align: dict[str, Any] = field(default_factory=dict)
    segment: dict[str, Any] = field(default_factory=dict)
    transcribe: dict[str, Any] = field(default_factory=dict)
    filter: dict[str, Any] = field(default_factory=dict)
    export: dict[str, Any] = field(default_factory=dict)


def load_language(code_or_path: str | Path) -> Language:
    """Load a language by ISO code (bundled file) or from a YAML path."""
    path = Path(code_or_path)
    if not path.suffix:
        path = LANGUAGES_DIR / f"{code_or_path}.yaml"
    if not path.exists():
        known = ", ".join(sorted(p.stem for p in LANGUAGES_DIR.glob("*.yaml")))
        raise FileNotFoundError(f"Unknown language '{code_or_path}'. Bundled languages: {known}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Language(**data)


def load_recipe(path: str | Path, output_dir: str | Path | None = None) -> Recipe:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    language = data.pop("language")
    lang = load_language(language if isinstance(language, str) else Path(path.parent, language["file"]))
    out = Path(output_dir or data.pop("output_dir", Path("data") / path.stem))
    data.pop("output_dir", None)
    return Recipe(name=data.pop("name", path.stem), language=lang, output_dir=out, **data)


def available_languages() -> list[Language]:
    return [load_language(p) for p in sorted(LANGUAGES_DIR.glob("*.yaml"))]

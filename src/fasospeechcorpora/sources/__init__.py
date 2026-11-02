"""Data sources. Each source downloads audio (+ text when known) into `raw/` and returns records.

Add a source: subclass `Source`, decorate it with `@register("my_type")`, import it below.
"""
from .base import SOURCES, Source, get_source, register  # noqa: F401
from . import bible_com, ipsapps, local, youtube  # noqa: F401  (registers the built-in sources)

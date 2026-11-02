"""Command line: `fasospeech run recipe.yaml`, `fasospeech check recipe.yaml`, `fasospeech languages`."""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import available_languages, load_recipe
from .pipeline import STEPS, Pipeline


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="fasospeech", description="Build speech datasets for any language.")
    sub = ap.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a recipe")
    run.add_argument("recipe")
    run.add_argument("--steps", help=f"comma-separated subset of: {','.join(STEPS)}")
    run.add_argument("--limit", type=int, help="only fetch this many items (chapters, pages, videos)")
    run.add_argument("--output", help="output folder (default: data/<recipe name>)")

    check = sub.add_parser("check", help="compare a sample of clips with an ASR model (CER)")
    check.add_argument("recipe")
    check.add_argument("--output")
    check.add_argument("--sample", type=int, default=50)
    check.add_argument("--model", help="ASR model (default: facebook/mms-1b-all)")
    check.add_argument("--target-lang", help="MMS adapter code (default: the language's mms_code)")

    sub.add_parser("languages", help="list bundled languages")

    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):        # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.command == "languages":
        for lang in available_languages():
            print(f"{lang.code}  {lang.name}")
        return
    recipe = load_recipe(args.recipe, args.output)
    if args.command == "run":
        steps = args.steps.split(",") if args.steps else None
        Pipeline(recipe, limit=args.limit).run(steps)
    else:
        print(json.dumps(Pipeline(recipe).check(args.sample, args.model, args.target_lang), indent=2))


if __name__ == "__main__":
    main()

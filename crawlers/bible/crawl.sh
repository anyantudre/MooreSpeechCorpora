#!/usr/bin/env bash

python crawlers/bible/crawl.py \
  --name MooreBible \
  --output_folder datasets \
  --url https://www.bible.com/bible/3058/GEN.1.MPBU \
  --language Moore \
  --code MPBU

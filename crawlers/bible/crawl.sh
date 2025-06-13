#!/usr/bin/env bash

echo "⌛️ Starting scraping..."

python crawlers/bible/crawl.py \
  --output_folder datasets \
  --url https://www.bible.com/bible/3058/GEN.1.MPBU \
  --language moore \
  --code MPBU

echo "✅ Scraping completed!"
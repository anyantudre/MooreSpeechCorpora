#!/usr/bin/env bash

echo "⌛️ Starting scraping..."

python crawlers/bible/crawl.py \
  --output_folder datasets/moore/bible/raw \
  --url https://www.bible.com/bible/3058/GEN.1.MPBU \
  --code MPBU

echo "✅ Scraping completed!"
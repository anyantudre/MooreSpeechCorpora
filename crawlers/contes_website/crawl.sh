#!/bin/bash

echo "⌛️ Starting scraping..."

python crawlers/contes_website/crawl.py \
    --output_folder "datasets/moore/contes_moore/vol5" \
    --url "https://media.ipsapps.org/mos/ora/prv-v10/01-B001-001.html" \
    --code "mos"

echo "✅ Scraping completed!"
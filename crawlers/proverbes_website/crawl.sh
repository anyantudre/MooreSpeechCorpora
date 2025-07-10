#!/bin/bash

# Script for scraping & preprocessing at the same time proverbes Mooré.
# PLEASE DO NOT USE IT FOR NOW, NEED SOME TWEAKS TO MAKE IT WORK
# PREFER THE PIPELINE SCRIPT IN THE MAIN DIR!!!


echo "⌛️ Starting scraping..."

python crawlers/proverbes_website/crawl.py \
    --name "proverbes_moore" \
    --output_folder "datasets/moore/proverbes_moore/vol2" \
    --url "https://media.ipsapps.org/mos/ora/p2/01-001-001.html" \
    --code "mos"

echo "🎵 Preprocessing..."

bash preprocessing/proverbes_preprocess.sh \
    --input_folder "datasets/moore/proverbes_moore/vol2/raw" \
    --output_folder "datasets/moore/proverbes_moore/vol2/preprocessed"


bash preprocessing/resample.sh \
  --input_folder "datasets/moore/proverbes_moore/vol2/preprocessed" \
  --output_folder "datasets/moore/proverbes_moore/vol2/resampled"


bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/moore/proverbes_moore/vol2/resampled \
  --text_folder datasets/moore/proverbes_moore/vol2/resampled \
  --output_folder datasets/moore/proverbes_moore/vol2/aligned \
  --lang mos \
  --uroman_path uroman_tools/bin

python datasets/prepare_proverbes_dataset.py \
  --input_folder datasets/moore/proverbes_moore/vol2/aligned \
  --repo_id anyantudre/moore-speech-proverbes \
  --split "vol2"

echo "✅ Scraping et préprocessing terminés!"
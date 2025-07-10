#!/bin/bash

# Pipeline pour les proverbes Mooré (version 2)
# Usage: bash pipelines_proverbes_2.sh --repo_id anyantudre/moore-speech-proverbes-2 --volume vol9 --split vol9 --start_url "https://media.ipsapps.org/mos/ora/prv-v09/01-B001-001.html"


# bash crawlers/contes_website/crawl.sh

# bash preprocessing/resample.sh --input_folder datasets/moore/proverbes_moore/vol9/raw --output_folder datasets/moore/proverbes_moore/vol9/resampled

# bash forced_alignement/align_and_segment.sh \
#   --audio_folder datasets/moore/proverbes_moore/vol9/resampled \
#   --text_folder datasets/moore/proverbes_moore/vol9/resampled \
#   --output_folder datasets/moore/proverbes_moore/vol9/aligned \
#   --lang mos \
#   --uroman_path uroman_tools/bin

# python datasets/prepare_hf_dataset.py   --input_folder datasets/moore/proverbes_moore/vol9/aligned   --repo_id anyantudre/moore-speech-proverbes-2   --split "vol9"

set -e

# Configuration par défaut
VOLUME="vol9"
START_URL="https://media.ipsapps.org/mos/ora/prv-v09/01-B001-001.html"
REPO_ID="anyantudre/moore-speech-proverbes-2"
SPLIT="vol9"
HF_TOKEN=""

# arguments pzarse
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --volume) VOLUME="$2"; shift ;;
    --start_url) START_URL="$2"; shift ;;
    --repo_id) REPO_ID="$2"; shift ;;
    --split) SPLIT="$2"; shift ;;
    --hf_token) HF_TOKEN="$2"; shift ;;
    *) echo "❌ Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# verif
if [[ -z "$REPO_ID" ]]; then
  echo "Error: --repo_id is required"
  echo "Usage: bash pipelines_proverbes_2.sh --repo_id your-username/moore-proverbes-2 [--volume vol9] [--split vol9] [--start_url URL] [--hf_token TOKEN]"
  exit 1
fi

BASE_DIR="datasets/moore/proverbes_moore/$VOLUME"
RAW_DIR="$BASE_DIR/raw"
RESAMPLED_DIR="$BASE_DIR/resampled"
ALIGNED_DIR="$BASE_DIR/aligned"

echo "🚀 Starting proverbes pipeline 2..."
echo ""


echo "📥 Step 1/4: Scraping..."
python crawlers/contes_website/crawl.py \
    --output_folder "$BASE_DIR" \
    --url "$START_URL" \
    --language "moore" \
    --code "mos"

echo "🎵 Step 2/4: Resampling..."
bash preprocessing/resample.sh \
  --input_folder "$RAW_DIR" \
  --output_folder "$RESAMPLED_DIR"

echo "🎯 Step 3/4: Forced alignment..."
bash forced_alignement/align_and_segment.sh \
  --audio_folder "$RESAMPLED_DIR" \
  --text_folder "$RESAMPLED_DIR" \
  --output_folder "$ALIGNED_DIR" \
  --lang mos \
  --uroman_path uroman_tools/bin

echo "☁️  Step 4/4: Pushing to HuggingFace..."
HF_ARGS="--input_folder $ALIGNED_DIR --repo_id $REPO_ID --split $SPLIT"
if [[ -n "$HF_TOKEN" ]]; then
  HF_ARGS="$HF_ARGS --hf_token $HF_TOKEN"
fi

python datasets/prepare_hf_dataset.py $HF_ARGS

echo ""
echo "✅ Pipeline terminé avec succès!"
echo "📊 Dataset disponible: https://huggingface.co/datasets/$REPO_ID"
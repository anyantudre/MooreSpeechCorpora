#!/bin/bash

# Pipeline complet pour les proverbes Mooré
# Usage: bash pipeline_proverbes.sh   --repo_id anyantudre/moore-speech-proverbes   --volume vol8   --split vol8   --start_url "https://media.ipsapps.org/mos/ora/p8/01-001-001.html"

set -e

VOLUME="vol2"
START_URL="https://media.ipsapps.org/mos/ora/p2/01-001-001.html"
REPO_ID="anyantudre/moore-speech-proverbes"
SPLIT="vol2"
HF_TOKEN=""

# arguments parse
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --volume) VOLUME="$2"; shift ;;
    --start_url) START_URL="$2"; shift ;;
    --repo_id) REPO_ID="$2"; shift ;;
    --split) SPLIT="$2"; shift ;;
    --hf_token) HF_TOKEN="$2"; shift ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

if [[ -z "$REPO_ID" ]]; then
  echo "Error: --repo_id is required"
  echo "Usage: bash pipeline_proverbes.sh --repo_id your-username/moore-proverbes [--volume vol2] [--split vol2] [--start_url URL] [--hf_token TOKEN]"
  exit 1
fi

BASE_DIR="datasets/moore/proverbes_moore/$VOLUME"
RAW_DIR="$BASE_DIR/raw"
PREPROCESSED_DIR="$BASE_DIR/preprocessed" 
RESAMPLED_DIR="$BASE_DIR/resampled"
ALIGNED_DIR="$BASE_DIR/aligned"

echo "🚀 Starting pipeline..."

echo "📥 Step 1/5: Scraping proverbes..."
python crawlers/proverbes_website/crawl.py \
    --name "proverbes_moore" \
    --output_folder "$BASE_DIR" \
    --url "$START_URL" \
    --language "moore" \
    --code "mos"

echo "📂 Step 2/5: Preprocessing segments..."
bash preprocessing/proverbes_preprocess.sh \
    --input_folder "$RAW_DIR" \
    --output_folder "$PREPROCESSED_DIR"

echo "🎵 Step 3/5: Resampling to WAV..."
bash preprocessing/resample.sh \
  --input_folder "$PREPROCESSED_DIR" \
  --output_folder "$RESAMPLED_DIR"

echo "🎯 Step 4/5: Forced alignment..."
bash forced_alignement/align_and_segment.sh \
  --audio_folder "$RESAMPLED_DIR" \
  --text_folder "$RESAMPLED_DIR" \
  --output_folder "$ALIGNED_DIR" \
  --lang mos \
  --uroman_path uroman_tools/bin

echo "☁️  Step 5/5: Pushing to HuggingFace..."
HF_ARGS="--input_folder $ALIGNED_DIR --repo_id $REPO_ID --split $SPLIT"
if [[ -n "$HF_TOKEN" ]]; then
  HF_ARGS="$HF_ARGS --hf_token $HF_TOKEN"
fi

python datasets/prepare_proverbes_dataset.py $HF_ARGS

echo ""
echo "✅ Pipeline terminé avec succès!"
echo "📊 Dataset disponible: https://huggingface.co/datasets/$REPO_ID"
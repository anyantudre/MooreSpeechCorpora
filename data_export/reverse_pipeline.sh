#!/bin/bash

# Reverse Pipeline Script for Moore Speech Corpora
# Usage: bash data_export/reverse_pipeline.sh --dataset_id your-username/your-dataset --output_base datasets/corrected

set -e

# Default values
DATASET_ID=""
OUTPUT_BASE="datasets/corrected"
SPLIT="train"
HF_TOKEN=""
ORGANIZE_BY_SPEAKER=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --dataset_id) DATASET_ID="$2"; shift ;;
    --output_base) OUTPUT_BASE="$2"; shift ;;
    --split) SPLIT="$2"; shift ;;
    --hf_token) HF_TOKEN="$2"; shift ;;
    --organize_by_speaker) ORGANIZE_BY_SPEAKER=true ;;
    *) echo "❌ Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# Check required parameters
if [[ -z "$DATASET_ID" ]]; then
  echo "❌ Error: --dataset_id is required"
  echo "Usage: bash data_export/reverse_pipeline.sh --dataset_id your-username/your-dataset [--output_base datasets/corrected] [--split train] [--hf_token TOKEN] [--organize_by_speaker]"
  exit 1
fi

# Set up folder structure
RAW_DIR="$OUTPUT_BASE/raw"
RESAMPLED_DIR="$OUTPUT_BASE/resampled"
ALIGNED_DIR="$OUTPUT_BASE/aligned"

echo "🚀 Starting reverse pipeline for dataset: $DATASET_ID"
echo "📂 Output base directory: $OUTPUT_BASE"
echo ""

# Step 1: Convert HF dataset to raw format
echo "📥 Step 1/4: Converting HF dataset to raw format..."
REVERSE_ARGS="--dataset_id $DATASET_ID --output_folder $RAW_DIR --split $SPLIT"
if [[ -n "$HF_TOKEN" ]]; then
  REVERSE_ARGS="$REVERSE_ARGS --hf_token $HF_TOKEN"
fi
if [[ "$ORGANIZE_BY_SPEAKER" == true ]]; then
  REVERSE_ARGS="$REVERSE_ARGS --organize_by_speaker"
fi

python data_export/reverse_hf_to_raw.py $REVERSE_ARGS

echo ""
echo "⏸️  MANUAL STEP: Please manually correct the text files in $RAW_DIR"
echo "   - Edit .txt files to fix transcription errors"
echo "   - Check metadata comments for original information"
echo "   - Press ENTER when ready to continue with resampling..."
read -p ""

# Step 2: Resample audio files
echo "🎵 Step 2/4: Resampling audio files..."
bash preprocessing/resample.sh \
  --input_folder "$RAW_DIR" \
  --output_folder "$RESAMPLED_DIR"

# Step 3: Forced alignment
echo "🎯 Step 3/4: Running forced alignment..."
bash forced_alignement/align_and_segment.sh \
  --audio_folder "$RESAMPLED_DIR" \
  --text_folder "$RESAMPLED_DIR" \
  --output_folder "$ALIGNED_DIR" \
  --lang mos \
  --uroman_path uroman_tools/bin

# Step 4: Export to HF dataset
echo "☁️  Step 4/4: Creating new HF dataset..."
NEW_DATASET_ID="${DATASET_ID}-corrected"
echo "📊 Suggested dataset ID: $NEW_DATASET_ID"
read -p "Enter HF dataset ID for corrected dataset (or press ENTER to use suggested): " USER_DATASET_ID

if [[ -n "$USER_DATASET_ID" ]]; then
  NEW_DATASET_ID="$USER_DATASET_ID"
fi

HF_EXPORT_ARGS="--input_folder $ALIGNED_DIR --repo_id $NEW_DATASET_ID --split $SPLIT"
if [[ -n "$HF_TOKEN" ]]; then
  HF_EXPORT_ARGS="$HF_EXPORT_ARGS --hf_token $HF_TOKEN"
fi

python data_export/prepare_hf_dataset.py $HF_EXPORT_ARGS

echo ""
echo "✅ Reverse pipeline completed successfully!"
echo "📊 Original dataset: $DATASET_ID"
echo "📊 Corrected dataset: $NEW_DATASET_ID"
echo "📁 Local files: $OUTPUT_BASE"
echo ""
echo "🎉 Your corrected dataset is now available at: https://huggingface.co/datasets/$NEW_DATASET_ID" 
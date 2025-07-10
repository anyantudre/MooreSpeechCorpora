#!/usr/bin/env bash

set -e

UROMAN_PATH="uroman_tools/bin"

#parse named args
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --audio_folder) AUDIO_FOLDER="$2"; shift ;;
    --text_folder) TEXT_FOLDER="$2"; shift ;;
    --output_folder) OUTPUT_FOLDER="$2"; shift ;;
    --lang) LANG="$2"; shift ;;
    --uroman_path) UROMAN_PATH="$2"; shift ;;
    *) echo "❌ Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# check required
if [[ -z "$AUDIO_FOLDER" || -z "$TEXT_FOLDER" || -z "$OUTPUT_FOLDER" || -z "$LANG" ]]; then
  echo "Usage: $0 --audio_folder <path> --text_folder <path> --output_folder <path> --lang <code> [--uroman_path <path>]"
  exit 1
fi

mkdir -p "$OUTPUT_FOLDER"

for wavpath in "$AUDIO_FOLDER"/*.wav; do
  filename="$(basename "$wavpath")"
  stem="${filename%.*}"
  outdir="$OUTPUT_FOLDER/$stem"

  # Skip if already processed
  if [[ -d "$outdir" && -f "$outdir/manifest.json" ]]; then
    echo "⏭️  Skipping $stem (already processed)"
    continue
  fi

  rm -rf "$outdir"

  python forced_alignement/data_prep/align_and_segment.py \
    --audio_filepath "$wavpath" \
    --text_filepath "$TEXT_FOLDER/${stem}.txt" \
    --lang "$LANG" \
    --outdir "$outdir" \
    --uroman_path "$UROMAN_PATH" \
    --use_star

  echo "✅ Finished aligning $stem → $outdir"
done
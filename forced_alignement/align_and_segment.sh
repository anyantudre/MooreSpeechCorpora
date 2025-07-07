#!/usr/bin/env bash

set -e

UROMAN_PATH="../uroman/bin"

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

cd fairseq

for wavpath in "../$AUDIO_FOLDER"/*.wav; do
  filename="$(basename "$wavpath")"
  stem="${filename%.*}"
  outdir="../$OUTPUT_FOLDER/$stem"

  rm -rf "$outdir"

  python -m examples.mms.data_prep.align_and_segment \
    --audio_filepath "$wavpath" \
    --text_filepath "../$TEXT_FOLDER/${stem}.txt" \
    --lang "$LANG" \
    --outdir "$outdir" \
    --uroman "$UROMAN_PATH"

  echo "✅ Finished aligning $stem → $outdir"
done

cd ..
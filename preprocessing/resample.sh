#!/usr/bin/env bash

set -e

# default values
INPUT_FOLDER=""
OUTPUT_FOLDER=""

# parse named args
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --input_folder) INPUT_FOLDER="$2"; shift ;;
    --output_folder) OUTPUT_FOLDER="$2"; shift ;;
    *) echo "❌ Unknown parameter passed: $1"; exit 1 ;;
  esac
  shift
done

# check required args
if [[ -z "$INPUT_FOLDER" || -z "$OUTPUT_FOLDER" ]]; then
  echo "Usage: $0 --input_folder <path> --output_folder <path>"
  exit 1
fi

mkdir -p "$OUTPUT_FOLDER"

for f in "$INPUT_FOLDER"/*.{mp3,wav}; do
  [[ -f "$f" ]] || continue  # Skip if no files match
  filename="$(basename "$f")"
  stem="${filename%.*}"
  ffmpeg -y -nostdin -i "$f" -ac 1 -ar 16000 "$OUTPUT_FOLDER/${stem}.wav"
  cp "$INPUT_FOLDER/${stem}.txt" "$OUTPUT_FOLDER/" 2>/dev/null || true
done

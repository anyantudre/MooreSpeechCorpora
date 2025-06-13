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
  echo "Convert proverbes MP3 segments to WAV for forced alignment"
  exit 1
fi

mkdir -p "$OUTPUT_FOLDER"

echo "📁 Copying proverbes segments..."

for f in "$INPUT_FOLDER"/*.mp3; do
  # Skip main audio file
  if [[ "$(basename "$f")" == "proverbes_moore.mp3" ]]; then
    continue
  fi
  
  filename="$(basename "$f")"
  stem="${filename%.*}"
  
  echo "  Copying $filename..."
  cp "$f" "$OUTPUT_FOLDER/"
  
  # Copy corresponding text file
  if [[ -f "$INPUT_FOLDER/${stem}.txt" ]]; then
    cp "$INPUT_FOLDER/${stem}.txt" "$OUTPUT_FOLDER/"
  fi
done

echo "✅ Copie terminée! Fichiers prêts."
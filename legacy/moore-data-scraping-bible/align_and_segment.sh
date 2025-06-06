#!/usr/bin/env bash
# align_and_segment.sh

INPUT_FOLDER="MooreBible/raw/Mooré_resampled"
INPUT_FOLDER_TEXT="MooreBible/raw/Mooré"
OUTPUT_FOLDER="MooreBible/aligned/Mooré"
mkdir -p "$OUTPUT_FOLDER"

cd fairseq

for wavpath in "../$INPUT_FOLDER"/*.wav; do
  filename="$(basename "$wavpath")"
  stem="${filename%.*}"
  outdir="../$OUTPUT_FOLDER/$stem"

  # remove any previous output, but do NOT recreate it here:
  rm -rf "$outdir"

  python -m examples.mms.data_prep.align_and_segment \
    --audio_filepath "$wavpath" \
    --text_filepath    "../$INPUT_FOLDER_TEXT/${stem}.txt" \
    --lang mos \
    --outdir "$outdir" \
    --uroman ../uroman/bin

  echo "Finished aligning $stem → $outdir"
done

cd ..   # back to project root
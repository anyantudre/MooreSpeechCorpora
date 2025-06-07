# Forced Alignment
Scripts to perform forced alignment and segmentation of audio-text pairs using Fairseq MMS tools.

### Requirements
- Fairseq installed with MMS examples.
- Uroman tool for romanization (see README at repo root for setup).

### Usage
```bash
bash align_and_segment.sh [audio_folder] [text_folder] [output_folder] [lang_code] [uroman_path]
```
Example:
```bash
bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/raw/Moore_resampled \
  --text_folder datasets/raw/Moore_resampled \
  --output_folder datasets/aligned/Moore \
  --lang mos \
  --uroman_path ../uroman/bin
```
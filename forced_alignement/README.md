# Forced Alignment
Scripts to perform forced alignment and segmentation of audio-text pairs using Fairseq MMS tools.

### Requirements
- Fairseq installed with MMS examples.
- Uroman tool for romanization (see README at repo root for setup).

### Usage
```bash
bash align_and_segment.sh [audio_folder] [text_folder] [output_folder] [lang_code] [uroman_path]
```
- Example Bible:
```bash
bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/moore/bible/resampled \
  --text_folder datasets/moore/bible/resampled \
  --output_folder datasets/moore/bible/aligned \
  --lang mos \
  --uroman_path ../uroman/bin
```

- Example Proverbes:
```bash
bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/moore/proverbes_moore/vol9/resampled \
  --text_folder datasets/moore/proverbes_moore/vol9/resampled \
  --output_folder datasets/moore/proverbes_moore/vol9/aligned \
  --lang mos \
  --uroman_path ../uroman/bin
  ```
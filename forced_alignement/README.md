# Forced Alignment
Scripts to perform forced alignment and segmentation of audio-text pairs using MMS tools.

## Requirements
- `torchaudio` with MMS model support
- `sox` for audio processing
- `perl` for uroman text romanization (tools included)

## Components
- `data_prep/`: MMS alignment tools (adapted from fairseq)
- `align_and_segment.sh`: Main alignment script

## Usage
```bash
bash forced_alignement/align_and_segment.sh \
  --audio_folder <audio_folder> \
  --text_folder <text_folder> \
  --output_folder <output_folder> \
  --lang <language_code> \
  --uroman_path <uroman_path>
```

- Example Bible:
```bash
bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/moore/bible/resampled \
  --text_folder datasets/moore/bible/resampled \
  --output_folder datasets/moore/bible/aligned \
  --lang mos \
  --uroman_path uroman/bin
```

- Example Proverbes:
```bash
bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/moore/proverbes_moore/vol9/resampled \
  --text_folder datasets/moore/proverbes_moore/vol9/resampled \
  --output_folder datasets/moore/proverbes_moore/vol9/aligned \
  --lang mos \
  --uroman_path uroman/bin
  ```
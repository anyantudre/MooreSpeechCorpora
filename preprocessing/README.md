# Preprocessing
Utilities to prepare raw audio and text data before alignment or dataset preparation.

### Scripts
- `resample.sh`: batch resample audio files to 16kHz, mono channel.
- `text_normalization.py`: normalize and clean text data, e.g., remove unwanted characters, lowercase, etc.

### Usage
Example to resample all `.mp3` to `.wav` in a folder:
```bash
bash preprocessing/resample.sh \ 
  --input_folder datasets/raw/Moore \
  --output_folder datasets/raw/Moore_resampled
```

Contes:
```bash
bash preprocessing/resample.sh --input_folder datasets/contes_moore/vol3/raw/moore --output_folder datasets/contes_moore/vol3/raw/moore_resampled
```

Proverbes:
```bash
bash preprocessing/resample.sh \
  --input_folder datasets/proverbes_moore/preprocessed/moore \
  --output_folder datasets/proverbes_moore/raw/moore_resampled
```
# Data Folder
Scripts to convert aligned audio-text data into Hugging Face Dataset format ready for ASR/TTS tasks.


### Structure
- `prepare_hf_dataset.py`: generates and pushes a HF dataset from aligned folder structures.
- `prepare_proverbes_dataset.py`: specialized script for proverbes with Moore-French paired structure.
- `reverse_hf_to_raw.py`: **reverse pipeline** - converts HF dataset back to raw format for manual correction.
- `reverse_pipeline.sh`: **complete reverse workflow** - automated script for the full correction pipeline.
- `raw/`: raw downloaded audio and text files.
- `aligned/`: forced-aligned audio-text segments ready for dataset creation.


### Usage

**For general datasets:**
```bash
python data_export/prepare_hf_dataset.py \
  --input_folder datasets/moore/bible/aligned \
  --repo_id anyantudre/moore-speech-bible \
  --hf_token YOUR_HF_TOKEN
```

**For proverbes (paired Moore-French):**
```bash
python data_export/prepare_proverbes_dataset.py \
  --input_folder datasets/proverbes_moore/aligned/moore \
  --repo_id your-username/moore-proverbes-audio \
  --hf_token YOUR_HF_TOKEN
```

Or omit --hf_token if you've already run:
```bash
huggingface-cli login
```

**For reverse pipeline (HF dataset → raw format):**
```bash
python data_export/reverse_hf_to_raw.py \
  --dataset_id your-username/your-dataset \
  --output_folder datasets/corrected/raw \
  --split train \
  --organize_by_speaker
```

This converts a HF dataset with columns `(audio, text, duration, voice, speaker_id)` back to raw format with `.wav` and `.txt` files for manual correction and re-alignment. After manual corrections, you can run the standard pipeline:

1. **Resample**: `bash preprocessing/resample.sh --input_folder datasets/corrected/raw --output_folder datasets/corrected/resampled`
2. **Align**: `bash forced_alignement/align_and_segment.sh --audio_folder datasets/corrected/resampled --text_folder datasets/corrected/resampled --output_folder datasets/corrected/aligned --lang mos`
3. **Export**: `python data_export/prepare_hf_dataset.py --input_folder datasets/corrected/aligned --repo_id your-corrected-dataset`

**Or use the complete automated workflow:**
```bash
bash data_export/reverse_pipeline.sh \
  --dataset_id your-username/your-dataset \
  --output_base datasets/corrected
```
This script handles the entire reverse pipeline with manual correction prompts.

**Note:** It is recommended to add this folder to `.gitignore` to avoid pushing large data files (Not this one anymore but `datasets` folder).
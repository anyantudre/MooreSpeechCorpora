# Data Folder
Scripts to convert aligned audio-text data into Hugging Face Dataset format ready for ASR/TTS tasks.

It is a placeholder, intended for storing raw and processed data files.


### Structure
- `prepare_hf_dataset.py`: generates and pushes a HF dataset from aligned folder structures.
- `prepare_proverbes_dataset.py`: specialized script for proverbes with Moore-French paired structure.
- `raw/`: raw downloaded audio and text files.
- `aligned/`: forced-aligned audio-text segments ready for dataset creation.


### Usage

**For general datasets:**
```bash
python prepare_hf_dataset.py \
  --input_folder MooreBible/aligned/Moore \
  --repo_id your-username/moore-bible-audio \
  --hf_token YOUR_HF_TOKEN
```

**For proverbes (paired Moore-French):**
```bash
python prepare_proverbes_dataset.py \
  --input_folder datasets/proverbes_moore/aligned/moore \
  --repo_id your-username/moore-proverbes-audio \
  --hf_token YOUR_HF_TOKEN
```

Or omit --hf_token if you've already run:
```bash
huggingface-cli login
```

**Note:** It is recommended to add this folder to `.gitignore` to avoid pushing large data files.
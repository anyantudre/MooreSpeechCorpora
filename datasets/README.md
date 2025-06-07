# Data Folder
Scripts to convert aligned audio-text data into Hugging Face Dataset format ready for ASR/TTS tasks.

It is a placeholder, intended for storing raw and processed data files.


### Structure
- `prepare_hf_dataset.py`: generates and pushes a HF dataset from aligned folder structures.
- `raw/`: raw downloaded audio and text files.
- `aligned/`: forced-aligned audio-text segments ready for dataset creation.


### Usage
```bash
python push_dataset.py \
  --input_folder MooreBible/aligned/Moore \
  --repo_id your-username/moore-bible-audio \
  --hf_token YOUR_HF_TOKEN
```
Or omit --hf_token if you've already run:
```bash
huggingface-cli login
```

**Note:** It is recommended to add this folder to `.gitignore` to avoid pushing large data files.
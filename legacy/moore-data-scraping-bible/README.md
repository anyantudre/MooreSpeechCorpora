# Mooré ASR Dataset Collection & Hugging Face Preparation

This README explains how to reproduce the Mooré (mos) ASR data pipeline—from environment setup through Bible scraping, resampling, forced alignment, dataset creation, and finally pushing to Hugging Face. 

> Check: [bible.com](https://www.bible.com/bible/3058/GEN.1.MPBU)

## 1. Environment Setup on Lightning AI Studio
Lightning AI Studio provides a Jupyter‐style notebook with GPU (or CPU) access on Ubuntu. Install all required dependencies, then make sure these scripts and folders are in your working directory.

```bash
# 1. Update package list and install system‐level dependencies:
sudo apt-get update -y
sudo apt-get install -y libsox-fmt-all sox ffmpeg libicu-dev pkg-config git

# 2. Remove existing torch/torchaudio/torchvision, then install PyTorch nightly (CUDA 11.8):
pip uninstall -y torch torchaudio torchvision
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu118

# 3. Install Python libraries for scraping, processing, alignment, and modeling:
pip install scrapy ICU-Tokenizer sox librosa datasets transformers accelerate evaluate jiwer bitsandbytes
pip install git+https://github.com/huggingface/peft.git@main
pip install fairseq

# 4. Clone required repos for scraper and Uroman:
git clone https://github.com/cawoylel/nlp4all.git      # Contains BibleScraper and evaluation scripts
git clone https://github.com/isi-nlp/uroman.git        # Uroman romanizer (data/ and bin/)
````


## 2. Scraping Mooré Bible Audio + Text (`bible_crawler.py`)
Use `bible_crawler.py` to download Mooré Bible `.mp3` and transcripts.

1. **Verify the Mooré Bible URL** on bible.com—for example:
   ```
   https://www.bible.com/bible/3058/GEN.1.MPBU
   ```

   where `MPBU` is the Mooré code.

2. **Run the crawler** in a notebook cell:
   ```bash
   python bible_crawler.py
   ```

3. **Inspect the output folder** `MooreBible/raw/Mooré/`, which should now contain:
   ```
   GEN.1.MPBU.txt    # Transcript of Genesis 1
   GEN.1.MPBU.mp3    # Audio of Genesis 1
   GEN.2.MPBU.txt
   GEN.2.MPBU.mp3
   ...
   ```


## 3. Resampling Audio to 16 kHz Mono (`resample.sh`)

Convert every `.mp3` under `MooreBible/raw/Mooré/` to a 16 kHz mono `.wav` in `MooreBible/raw/Mooré_resampled/`.

**Notebook Cell (Shell)**

```bash
# Ensure output folder exists:
mkdir -p MooreBible/raw/Mooré_resampled

# Run resampling:
bash resample.sh
```

After running, `MooreBible/raw/Mooré_resampled/` holds all `.wav` files at 16 kHz mono.


## 4. Neural Forced Alignment (`align_and_segment.sh`)

Segment each long `.wav` and align to text using the MMS forced aligner via Fairseq.

1. **Ensure Uroman is in place**:
```bash
moore-data-scraping-bible/
├── fairseq/
└── uroman/
    ├── bin/
    │   └── uroman.pl        ← (the Perl script; move it from uroman to lib and move data also to the main dir)
    ├── data/
    │   ├── Scripts.txt
    │   ├── UnicodeData.txt
    │   ├── UnicodeDataOverwrite.txt
    │   └── romanization-table.txt
    └── (other folders)

```

2. **Run forced alignment**:

   ```bash
   bash align_and_segment.sh
   ```

* **`--lang mos`** will be used since MMS supports Mooré.
* Each `manifest.json` now appears under `MooreBible/aligned/Mooré/<chapter>/`, containing:

  ```json
  {"audio_start_sec":0.0,"audio_filepath":"../MooreBible/aligned/Mooré/GEN.1_MPBU/segment0.flac","duration":3.80,"text":"1 Kibayã 10","normalized_text":"kibayã"}
  ...
  ```
* Segmented audio files live in `.../<chapter>/audio/`.


## 5. Preparing & Pushing a Hugging Face Dataset (`prepare_hf_dataset.py`)

Create a `DatasetDict` with columns: `audio`, `transcription`, `duration`, and `chapter`, then push to Hugging Face.

1. **Run the script** in a notebook cell (after logging in with `huggingface-cli login`):

   ```bash
   python prepare_hf_dataset.py
   ```

* This automatically decodes all `\uXXXX` escapes into actual Mooré characters.
* The resulting dataset on HF will have four columns per row:
  * `audio`: URL to download the `.wav` (HF handles streaming)
  * `transcription`: the aligned text with correct diacritics
  * `duration`: duration in seconds
  * `chapter`: the chapter code (e.g. `1CH_10_MPBU`)

2. **Verify on Hugging Face**:
   Visit `https://huggingface.co/anyantudre/moore-asr-dataset` to confirm that each row displays proper Mooré text and that columns are intact.


## Reproducibility Tips

1. **Environment**
   * Use Python 3.10 or pip < 24.1 to avoid Fairseq dataclass issues on Python 3.12, or install the patched Fairseq fork.
   * Ensure `uroman/bin/uroman.pl` and `uroman/data/…` are present before running alignment.

2. **Scraping**
   * Confirm the correct Mooré version code (e.g. `MPBU`) on bible.com before running `bible_crawler.py`.

3. **Resampling**
   * Run `resample.sh`, verifying that `MooreBible/raw/Mooré_resampled/` contains 16 kHz `.wav` files.

4. **Alignment**
   * Use `align_and_segment.sh` with `--lang mos` if MMS supports Mooré; otherwise use `--lang hau`.
   * Check each `manifest.json` to ensure segments, timestamps, and normalized text appear correctly.

5. **Dataset**
   * `prepare_hf_dataset.py` builds and splits the dataset, pushing it to HF with all four columns: `audio`, `transcription`, `duration`, `chapter`.

6. **Push to HF**
   * After `push_to_hub`, verify Unicode diacritics and metadata on the HF webpage.
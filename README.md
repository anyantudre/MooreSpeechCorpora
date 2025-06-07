# Moore Speech Corpora Toolkit
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Modular tools to collect, preprocess, align, and prepare Mooré speech/text data for **Text-to-Speech (TTS)** and **Automatic Speech Recognition (ASR)**.

This toolkit reproduces the full Moore Speech Corpora data pipeline.

---

## Table of Contents

1. [Features](#features)  
2. [Installation](#installation)  
3. [Quick Start](#quick-start)  
4. [Usage](#usage)
6. [Contributing](#contributing)  
7. [License](#license)

---

## Features

- Scrape aligned Mooré audio and text from online sources (Bible, YouTube, etc.)
- Segment and align long audio using MMS forced alignment tools (Fairseq)
- Audio preprocessing: resampling, mono conversion
- Text normalization and optional romanization (via Uroman)
- Export datasets ready for the Hugging Face ecosystem
- Modular, CLI-friendly scripts

The toolkit is structured as follows:
```text
moore-toolkit/
├─ crawlers/             # Bible, YouTube, etc.
├─ preprocessing/        # Resample, normalize text
├─ forced_alignment/     # MMS scripts & wrappers
├─ datasets/             # HF dataset prep & push
├─ utils/                # Shared helpers
├─ environment.yml
└─ README.md
```

---

## Installation & Setup
```bash
git clone https://github.com/anyantudre/moore-toolkit.git
cd moore-toolkit
conda env create -f environment.yml
conda activate moore-toolkit
```

> It's recommended to use **Python 3.10.11**

---

## Quick Start

- **Data Crawling:** crawls data.  
```bash
# crawling Moore Bible example
sh ./crawlers/bible/crawl.sh
```
See [crawlers/README.md](crawlers/README.md) for full instructions.

- **Preprocessing:** preprocessing.
```bash
bash preprocessing/resample.sh --input_folder datasets/raw/Moore --output_folder datasets/raw/Moore_resampled
```

- **Forced Alignment:** outputs segmented audio and `manifest.json` files for each chapter.  
```bash
# run forced alignment
bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/raw/Moore_resampled \
  --text_folder datasets/raw/Moore_resampled \
  --output_folder datasets/aligned/Moore \
  --lang mos \
  --uroman_path ../uroman/bin
```
See [forced_alignment/README.md](forced_alignment/README.md) for full instructions.

- **Dataset Preparation:** uploads dataset with columns: audio, transcription, duration, chapter.
```bash
python datasets/prepare_hf_dataset.py --input_folder MooreBible/aligned/Moore --repo_id anyantudre/moore-asr-dataset --hf_token hf_xxxx
```
See [datasets/README.md](datasets/README.md) for full instructions.

---

## Contributing
Contributions are more than welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

---

## Acknowledgments
* [Facebook AI Research Fairseq](https://github.com/facebookresearch/fairseq/) for multilingual alignment tools.
* [bible.com](https://www.bible.com/) for Mooré audio/text
* [Uroman](https://github.com/isi-nlp/uroman) for romanization
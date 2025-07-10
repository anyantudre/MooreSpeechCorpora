# Moore Speech Corpora Toolkit
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A complete toolkit for building Mooré speech datasets. Collect, preprocess, align, and export high-quality audio/text pairs for **Text-to-Speech (TTS)** and **Automatic Speech Recognition (ASR)**.

This toolkit reproduces the full [Moore Speech Corpora](https://huggingface.co/datasets/anyantudre/MooreSpeechCorpora) data collection pipeline.

---

## Table of Contents
1. [Features](#features)  
2. [Installation & Setup](#installation--setup)  
3. [Quick Start](#quick-start)  
4. [Contributing](#contributing)  
5. [Contacts & Citation](#contacts--citation)
6. [Acknowledgments](#acknowledgments)

---

## Features
We offer modular, CLI-friendly scripts for tasks like:
- Scrape Mooré audios and texts from online sources (Bible, YouTube, etc.)
- Segment and align long audios w/ texts
- Audio preprocessing: resampling, mono conversion
- Moore text normalization
- Audios denoising and enhancement
- Export datasets to different formats (Hugging Face, LJSpeech etc...)

The toolkit is structured as follows:
```text
moore-toolkit/
├─ crawlers/             # Bible, YouTube, etc.
├─ preprocessing/        # Resample, normalize text
├─ forced_alignement/    # MMS scripts & data_prep tools
├─ uroman_tools/         # Romanization tools (extracted)
├─ data_export/          # HF dataset prep & push
├─ environment.yml
└─ README.md
```

---

## Installation & Setup

```bash
git clone https://github.com/anyantudre/MooreSpeechCorpora.git
cd MooreSpeechCorpora
conda env create -f environment.yml
conda activate mooredata
```

> It's highly recommended to use **Python 3.10.11**!!!

---

## Quick Start

* **Data Crawling:** crawls data from sources like Bible and YouTube.
```bash
# crawling Moore Bible example
sh ./crawlers/bible/crawl.sh
```

See [crawlers/README.md](crawlers/README.md) for full instructions and more details.

* **Preprocessing:** preprocessing.

```bash
# example resampling Moore data
bash preprocessing/resample.sh --input_folder datasets/moore/bible/raw --output_folder datasets/moore/bible/resampled
```

See [preprocessing/README.md](preprocessing/README.md) for full instructions and more details.

* **Forced Alignment:** outputs segmented audio and `manifest.json` files for each chapter.

```bash
# run forced alignment
bash forced_alignement/align_and_segment.sh \
  --audio_folder datasets/moore/bible/resampled \
  --text_folder datasets/moore/bible/resampled \
  --output_folder datasets/moore/bible/aligned \
  --lang mos \
  --uroman_path uroman_tools/bin
```

See [forced_alignement/README.md](forced_alignement/README.md) for full instructions and more details.

* **Dataset Preparation/Export:** uploads dataset with columns: audio, transcription, duration, chapter to Hugging Face Hub.

```bash
python data_export/prepare_hf_dataset.py --input_folder datasets/moore/bible/aligned --repo_id anyantudre/moore-speech-bible --hf_token hf_xxxx
```

See [datasets/README.md](datasets/README.md) for full instructions and more details.

* **Denoising & Enhancement (optional):** applies Resemble Enhance to improve audio quality, optionally skipping enhancement or keeping original audio.

```bash
python denoising/denoise_and_push.py \
  --dataset_id anyantudre/moore-speech-bible \
  --output_repo_id anyantudre/moore-speech-bible-denoised \
  --hf_token hf_xxxx \
  --enhance_audio \
  --keep_original_audio
```

> The resulting dataset will include `denoised_audio` and optionally `enhanced_audio` fields, depending on the flags.

See [denoising/README.md](denoising/README.md) for full instructions and parameters.

---

## Contributing
Contributions are more than welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

---

## Contacts & Citation

**Curator:**
- [Wendyellé A. Alban NYANTUDRE](https://github.com/anyantudre) (@anyantudre)
- [Aristide BANDAOGO](https://github.com/Bandoss-Ariss) (@Bandoss-Ariss)

**Example Citation:**
```bibtex
@misc{anyantudre2025moorespeechcorpora,
  title        = {Moore Speech Corpora: Toolkit to collect, preprocess, align, and prepare Mooré speech/text data for TTS and ASR.},
  author       = {Nyantudre, Wendyellé Abubakrh Alban and Bandaogo, Aristide},
  year         = {2025},
  howpublished = {Available at \url{https://github.com/anyantudre/MooreSpeechCorpora}},
  note         = {GO AI Corporation}
}
```

**License Compliance:**
This work builds on several open-source components. When using this toolkit or derived datasets, please:
- Credit this work using proper citation
- Comply with all original component licenses (see Acknowledgments)
- Include appropriate attribution in publications and derived works

---

## Acknowledgments
* [cawoylel](https://github.com/cawoylel/): this repo is largely inspired by their excellent work on the Fula language!
* [Facebook AI Research Fairseq](https://github.com/facebookresearch/fairseq/) for the original MMS alignment tools (adapted in `forced_alignement/data_prep/`).
* [bible.com](https://www.bible.com/) for Mooré audio/text
* [Uroman](https://github.com/isi-nlp/uroman) for romanization (tools included in `uroman_tools/`)
* [Resemble Enhance](https://github.com/resemble-ai/resemble-enhance) for speech enhancement
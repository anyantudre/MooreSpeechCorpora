# Contributing to the Mooré Language Toolkit (No finished yet)

🎉 Thank you for considering contributing to this open-source effort to support speech and language technology for the Mooré language!

This toolkit helps collect, align, and prepare Mooré text and audio data for training TTS, ASR, and other models. Whether you’re a developer, researcher, linguist, or simply enthusiastic about language tech — you are welcome!

---

## 🛠 What You Can Contribute

* 🐞 **Bug Fixes**: Found something broken? Open an issue or submit a fix.
* 🌍 **New Crawlers**: Add scripts for scraping new websites with Mooré text/audio.
* 🧼 **Data Cleaning**: Help improve preprocessing and alignment.
* 🔤 **Language Resources**: Contribute dictionaries, lexicons, or metadata.
* 📚 **Documentation**: Improve READMEs or add usage examples.

---

## 🧑‍💻 Getting Started

1. **Fork** the repository.
2. **Clone** your fork:
   ```bash
   git clone https://github.com/anyantudre/moore-lang-toolkit.git
   cd moore-lang-toolkit
   ```
3. Create a new branch:
   ```bash
   git checkout -b your-feature-name
   ```
4. Make your changes, test them, and commit:
   ```bash
   git commit -m "Add: brief description of your change"
   ```
5. **Push** and open a **pull request** from your fork.

---

## ✅ Code Guidelines
* Keep code **simple, modular**, and **well-commented**.
* Use **descriptive names** for files and functions.
* Prefer **Python** and **Bash** for core toolkit functionality.
* Scripts should use **CLI arguments** instead of hardcoded paths.

---

## 📂 Directory Structure
Here's what each folder is for:

* `crawlers/`: Website/Youtube scraping tools.
* `forced_alignment/`: Audio-text alignment tools.
* `data/`: Datasets and resources (usually ignored in `.gitignore`).
* `utils/`: Small reusable utilities.
* `scripts/`: Useful helper scripts for setup or processing.

---

## 📬 Opening an Issue
If you're not ready to code, you can still help by:

* Reporting bugs.
* Requesting features.
* Suggesting websites with Mooré content.

Use [Issues](https://github.com/<your-org-or-username>/moore-lang-toolkit/issues) for discussions or questions.

---

## 🧪 Tests (Optional for now)
We don't yet have formal test coverage, but we appreciate PRs that include small test scripts or examples in `examples/` or `tests/`.

---

## 🙌 Thanks for Your Contribution!
You're helping preserve and promote the Mooré language through technology. 💛

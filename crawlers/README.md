# Crawlers
This folder contains web scrapers to collect Mooré language audio and text data from online sources.

### Included scrapers
- **bible/bible_crawler.py**: scrapes aligned text and audio from the Bible website for Mooré.
- **contes_website/contes_scraper.py**: scrapes aligned text and audio from the mooreburkina.com website.
- **youtube/youtube_downloader.py**: downloads Mooré language videos and extracts audio.


### Usage
Run scripts:
- For Mooré Bible data, simply run (assuming you're in main folder):
```bash
python crawlers/bible/crawl.py \
  --name MooreBible \
  --output_folder datasets \
  --url https://www.bible.com/bible/3058/GEN.1.MPBU \
  --language Moore \
  --code MPBU
```
or if you prefer bash scripts, open [crawl.sh](./bible/crawl.sh), modify params then execute:
```bash
sh crawlers/bible/crawl.sh
```

**Inspect the output folder** `datasets/raw/Moore/`, which should now contain:
```
   GEN.1.MPBU.txt    # Transcript of Genesis 1
   GEN.1.MPBU.mp3    # Audio of Genesis 1
   GEN.2.MPBU.txt
   GEN.2.MPBU.mp3
   ...
```

### TO DO
- [✅] [WẼNNAAM SEBRE 2014](https://www.bible.com/bible/3058/GEN.1.MPBU)
- [ ] [Contes vol 2 avec audio](https://mooreburkina.com/fr/contes-et-proverbes-en-moor%C3%A9/contes-en-moor%C3%A9): Collection de 18 contes en moore (avec audio) écrit par SIBALLO Jacques
- [ ] [YouTube](#)
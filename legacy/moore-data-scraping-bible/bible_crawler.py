from scrapy.crawler import CrawlerProcess
from icu_tokenizer import SentSplitter
from nlp4all.asr.src.scraper import BibleScraper

SPLITTER = SentSplitter()

process = CrawlerProcess()
process.crawl(
    BibleScraper,
    name="MooreBible",
    output_folder="MooreBible", 
    start_urls=["https://www.bible.com/bible/3058/GEN.1.MPBU"],
    language="Mooré", 
    code="MPBU",  # Mooré code in the URL: MPBU
    splitter=SPLITTER
)
process.start()
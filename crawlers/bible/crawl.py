import argparse
from scrapy.crawler import CrawlerProcess
from bible_scraper import BibleScraper


def main():
    parser = argparse.ArgumentParser(description="Run Bible scraper")
    parser.add_argument("--output_folder", type=str, required=True, help="Where to save audio/text")
    parser.add_argument("--url", type=str, required=True, help="Start URL (e.g., GEN.1.MPBU)")
    parser.add_argument("--language", type=str, required=True, help="Language name")
    parser.add_argument("--code", type=str, required=True, help="3–4 letter language code in the URL")
    args = parser.parse_args()

    process = CrawlerProcess()
    process.crawl(
        BibleScraper,
        output_folder=args.output_folder,
        start_urls=[args.url],
        language=args.language,
        code=args.code,
    )
    process.start()


if __name__ == "__main__":
    main()

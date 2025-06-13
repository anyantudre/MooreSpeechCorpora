import argparse
from scrapy.crawler import CrawlerProcess
from icu_tokenizer import SentSplitter
from proverbes_scraper import ProverbesScraper


def main():
    parser = argparse.ArgumentParser(description="Lancer le scraper de proverbes Mooré")
    parser.add_argument("--name", type=str, required=True, help="Nom du dataset")
    parser.add_argument("--output_folder", type=str, required=True, help="Dossier de sauvegarde")
    parser.add_argument("--url", type=str, required=True, help="URL de départ")
    parser.add_argument("--code", type=str, required=True, help="Code langue")
    args = parser.parse_args()

    process = CrawlerProcess()
    process.crawl(
        ProverbesScraper,
        name=args.name,
        output_folder=args.output_folder,
        start_urls=[args.url],
        code=args.code,
        splitter=SentSplitter()
    )
    process.start()


if __name__ == "__main__":
    main()

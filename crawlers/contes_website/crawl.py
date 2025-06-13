import argparse
from scrapy.crawler import CrawlerProcess
from icu_tokenizer import SentSplitter
from contes_scraper import ConteScraper


def main():
    parser = argparse.ArgumentParser(description="Lancer le scraper de contes Mooré")
    parser.add_argument("--output_folder", type=str, required=True, help="Dossier de sauvegarde audio/texte")
    parser.add_argument("--url", type=str, required=True, help="URL de départ")
    parser.add_argument("--code", type=str, required=True, help="Code langue 3-4 lettres")
    args = parser.parse_args()

    process = CrawlerProcess()
    process.crawl(
        ConteScraper,
        output_folder=args.output_folder,
        start_urls=[args.url],
        code=args.code,
        splitter=SentSplitter()
    )
    process.start()


if __name__ == "__main__":
    main()

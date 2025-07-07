"""
Contes Crawler from https://mooreburkina.com/fr/sitemap
Author: @anyantudre
"""


from pathlib import Path
from typing import List
import requests

from icu_tokenizer import SentSplitter
from scrapy import Spider, Request


class ConteScraper(Spider):
    allowed_domains = ["media.ipsapps.org"]
    splitter = SentSplitter()

    def __init__(
        self,
        output_folder: str,
        start_urls: List[str],
        code: str,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.output_folder = Path(output_folder) / "raw"
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.start_urls = start_urls.split(",") if isinstance(start_urls, str) else start_urls
        self.code = code

    def parse(self, response):
        #ID du fichier depuis l'URL (ex: "01-B001-001" depuis "01-B001-001.html")
        filename = response.url.split("/")[-1].replace(".html", "")
        
        txt_path = self.output_folder / f"{filename}.txt"
        mp3_path = self.output_folder / f"{filename}.mp3"

        # download audio
        audio_src = response.css("audio source::attr(src)").get()
        if audio_src:
            try:
                audio_response = requests.get(audio_src)
                if audio_response.status_code == 200:
                    mp3_path.write_bytes(audio_response.content)
                    self.logger.info(f"Audio sauvegardé dans {mp3_path}")
            except Exception as e:
                self.logger.error(f"Erreur lors du téléchargement audio: {e}")

        # extract title
        title = response.css("title::text").get()
        if title:
            title = title.strip()

        # extract text
        #text_elements = response.css("div.txs, div.m")
        text_elements = response.css("div.txs")
        tokens = []
        for element in text_elements:
            # get all text from element, excluding tags
            text_content = element.css("::text").getall()
            clean_text = " ".join([t.strip() for t in text_content if t.strip()])
            
            if clean_text:
                sentences = self.splitter.split(clean_text.strip())
                tokens.extend([s for s in sentences if s.strip()])

        with open(txt_path, "w", encoding="utf-8") as f:
            #if title:
            #    f.write(f"{title}\n")
            # eviter la répétition des 2 premières lignes
            if len(tokens) >= 2 and tokens[0] == tokens[1]:
                tokens = tokens[:1] + tokens[2:]
            for token in tokens:
                f.write(f"{token}\n")
        
        self.logger.info(f"Texte sauvegardé dans {txt_path}")

        # next page
        next_page = response.css('a[title="Next Chapter"]::attr(href)').get()
        if next_page:
            # build full url
            next_url = response.urljoin(next_page)
            yield Request(url=next_url, callback=self.parse)

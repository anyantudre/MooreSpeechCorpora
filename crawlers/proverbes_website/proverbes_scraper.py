"""
proverbes Crawler for https://mooreburkina.com/fr/sitemap
Author: @anyantudre
"""

from pathlib import Path
from typing import List
import requests
import re

from icu_tokenizer import SentSplitter
from scrapy import Spider


class ProverbesScraper(Spider):
    name = "proverbes"
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
        self.audio_downloaded = False
        self.main_audio_path = None

    def download_audio(self, audio_src):
        """Télécharge l'audio principal une seule fois"""
        if self.audio_downloaded:
            return self.main_audio_path
            
        try:
            data = requests.get(audio_src)
            self.main_audio_path = self.output_folder / "proverbes_moore.mp3"
            with open(self.main_audio_path, 'wb') as out_mp3:
                out_mp3.write(data.content)
            self.audio_downloaded = True
            return self.main_audio_path
        except Exception as e:
            self.logger.error(f"Erreur téléchargement audio: {e}")
            return None

    def extract_timestamps(self, response):
        """Extrait startTime et stopTime depuis le JavaScript"""
        script_content = response.text
        
        # Extraction de startTime et stopTime
        start_match = re.search(r'var startTime = ([\d.]+);', script_content)
        stop_match = re.search(r'var stopTime\s*=\s*([\d.]+);', script_content)
        
        if start_match and stop_match:
            return float(start_match.group(1)), float(stop_match.group(1))
        return None, None

    def extract_texts(self, response):
        """Extrait exactement 3 lignes : mooré, français, mooré répété"""
        moore_texts = []
        french_texts = []
        
        #textes mooré
        for span in response.css("span.bd"):
            text = span.css("::text").get()
            if text and text.strip():
                moore_texts.append(text.strip())
        
        #textes français
        for span in response.css("span.bdit"):
            text = span.css("::text").get()
            if text and text.strip():
                # Enlève les parenthèses
                clean_text = text.strip().replace("(", "").replace(")", "").strip()
                if clean_text:
                    french_texts.append(clean_text)

        result = []
        
        if moore_texts:
            full_moore = " ".join(moore_texts).strip()
            
            # enlève la numérotation au début
            clean_moore = re.sub(r'^\d+\s+', '', full_moore).strip()
            
            # gestion de la les répétitions
            words = clean_moore.split()
            half_len = len(words) // 2
            if half_len > 0 and " ".join(words[:half_len]) == " ".join(words[half_len:]):
                clean_moore = " ".join(words[:half_len]).strip()
            
            result.append(clean_moore)
        
        if french_texts:
            french_line = " ".join(french_texts).strip()
            result.append(french_line)
        
        # meme texte mooré répété
        if moore_texts:
            result.append(clean_moore)
        
        return result

    def create_audio_segment(self, start_time, stop_time, filename):
        """Crée un segment audio avec ffmpeg"""
        if not self.main_audio_path or not self.main_audio_path.exists():
            return False
            
        try:
            import subprocess
            output_path = self.output_folder / f"{filename}.mp3"
            
            cmd = [
                "ffmpeg", "-i", str(self.main_audio_path),
                "-ss", str(start_time),
                "-to", str(stop_time),
                "-c", "copy",
                str(output_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception as e:
            self.logger.error(f"Erreur création segment: {e}")
            return False

    def parse(self, response):
        filename = response.url.split("/")[-1].replace(".html", "")
        
        # télécharge l'audio principal
        audio_element = response.css("audio source::attr(src)").get()
        if audio_element and not self.audio_downloaded:
            self.download_audio(audio_element)
        
        # extraction timestamps
        start_time, stop_time = self.extract_timestamps(response)
        if start_time is not None and stop_time is not None:
            self.create_audio_segment(start_time, stop_time, filename)
        
        # extraction textes
        texts = self.extract_texts(response)
        
        txt_path = self.output_folder / f"{filename}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for text in texts:
                f.write(f"{text}\n")
        
        self.logger.info(f"✅ Page traitée: {filename} ({len(texts)} lignes)")

        #navig vers la page suivante
        next_url = response.css('a[title="Next Chapter"]::attr(href)').get()
        if next_url and not next_url.strip() == "":
            yield response.follow(next_url, self.parse)

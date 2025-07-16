import os
import sys
import subprocess
from urllib.parse import urlparse, parse_qs
from pytubefix import Playlist, YouTube

helpers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'helpers'))
sys.path.append(helpers_path)

from utils import sanitize_filename


class YoutubeDownloader:
    """
    Classe pour télécharger des playlists et vidéos YouTube avec automatisation du pipeline.
    """
    
    def __init__(self, output_dir="./data/youtube-mp3-downloads"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def download_playlist(self, playlist_url, custom_output_dir=None):
        output_dir = custom_output_dir or self.output_dir
        
        try:
            playlist_name = playlist_url.split('list=')[-1]
            folder_name = f"playlist_{playlist_name}"
            playlist_folder = os.path.join(output_dir, folder_name)
            
            if not os.path.exists(playlist_folder):
                os.makedirs(playlist_folder)
            
            playlist = Playlist(playlist_url)
            print(f"\n\n ================ Téléchargement de la playlist: {playlist.title}   =============== \n")
            
            for video in playlist.videos:
                try:
                    print(f"\n Traitement de la vidéo: {video.title}")
                    
                    sanitized_title = sanitize_filename(video.title)
                    file_path = os.path.join(playlist_folder, f"{sanitized_title}.mp3")
                    
                    if os.path.exists(file_path):
                        print(f"Fichier déjà existant: {file_path}. Téléchargement ignoré.")
                        continue
                    
                    audio_stream = video.streams.get_audio_only()
                    
                    audio_stream.download(output_path=playlist_folder, filename=f"{sanitized_title}.mp3")
                    print(f"Téléchargé: {file_path}")
                    
                except Exception as e:
                    print(f"Erreur lors du traitement de la vidéo '{video.title}': {e}")
            
            print("\n\n ================ Téléchargement de playlist terminé!   =============== \n")
            return playlist_folder
            
        except Exception as e:
            print(f"Erreur lors du téléchargement de la playlist: {e}")
            return None
    
    def download_video(self, video_url, custom_output_dir=None):

        output_dir = custom_output_dir or self.output_dir
        
        try:
            print(f"\n\n ================ Téléchargement audio depuis {video_url}...   =============== \n")
            
            yt = YouTube(video_url)
            video = yt.streams.filter(only_audio=True).first()
            
            original_title = yt.title
            sanitized_title = sanitize_filename(original_title)
            
            downloaded_file = os.path.join(output_dir, sanitized_title + ".mp4")
            
            if os.path.exists(downloaded_file):
                print(f"Fichier déjà existant: {downloaded_file}. Téléchargement ignoré.")
                return downloaded_file
            
            downloaded_file = video.download(output_path=output_dir, filename=sanitized_title + ".mp4")
            
            print(f"Fichier audio téléchargé: {downloaded_file}")
            return downloaded_file
            
        except Exception as e:
            print(f"Échec du téléchargement de {video_url}: {e}")
            return None
    
    def download_from_urls_list(self, urls_list):
        downloaded_paths = []
        for url in urls_list:
            if "playlist" in url:
                path = self.download_playlist(url)
                if path:
                    downloaded_paths.append(path)
            else:
                path = self.download_video(url)
                if path:
                    downloaded_paths.append(path)
        
        return downloaded_paths
    
    def download_from_file(self, urls_file_path):
        try:
            with open(urls_file_path, 'r') as file:
                urls = file.read().splitlines()
            urls = [url.strip() for url in urls if url.strip()]
            
            return self.download_from_urls_list(urls)
            
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier {urls_file_path}: {e}")
            return []
    
    def automate_download(self, urls_source, run_full_pipeline=False, **pipeline_kwargs):
        results = {
            'downloaded_paths': [],
            'pipeline_completed': False,
            'error': None
        }
        
        try:
            print("\n\n ================ PHASE 1: TÉLÉCHARGEMENT   =============== \n")
            
            if isinstance(urls_source, str):
                downloaded_paths = self.download_from_file(urls_source)
            elif isinstance(urls_source, list):
                downloaded_paths = self.download_from_urls_list(urls_source)
            else:
                raise ValueError("urls_source doit être un chemin de fichier ou une liste d'URLs")
            
            results['downloaded_paths'] = downloaded_paths
            
            if not downloaded_paths:
                results['error'] = "Aucun fichier téléchargé"
                return results
            
            if run_full_pipeline:
                print("\n\n ================ PHASE 2: PIPELINE COMPLET   =============== \n")
                
                raw_data_dir = pipeline_kwargs.get('raw_data_dir', './data/raw_wav_audios')
                chunked_data_dir = pipeline_kwargs.get('chunked_data_dir', './data/chunked_wav_audios')
                hf_repo = pipeline_kwargs.get('hf_repo')
                min_duration = pipeline_kwargs.get('min_duration', 4)
                max_duration = pipeline_kwargs.get('max_duration', 20)
                
                if not hf_repo:
                    results['error'] = "hf_repo requis pour le pipeline complet"
                    return results

                print("Conversion MP3 vers WAV...")
                cmd = f"python ./helpers/convert_to_wav.py -i \"{self.output_dir}\" -o \"{raw_data_dir}\""
                subprocess.run(cmd, shell=True)
                
                print("Création de chunks et filtrage...")
                cmd = f"python ./create_dataset/create-ljspeech.py -i \"{raw_data_dir}\" -o \"{chunked_data_dir}\" --min_duration {min_duration} --max_duration {max_duration}"
                subprocess.run(cmd, shell=True)
                
                print("Création et push vers Hugging Face...")
                cmd = f"python ./create_dataset/create_hf_dataset.py -i \"{chunked_data_dir}\" -o \"{chunked_data_dir}\" -r \"{hf_repo}\""
                subprocess.run(cmd, shell=True)
                
                results['pipeline_completed'] = True
                print("\n\n ================ PIPELINE TERMINÉ!   =============== \n")
            
            print("\n\n ================ TOUS LES TÉLÉCHARGEMENTS ET TRAITEMENTS TERMINÉS!   =============== \n")
            
        except Exception as e:
            results['error'] = str(e)
            print(f"Erreur dans automate_download: {e}")
        
        return results


if __name__ == "__main__":
    downloader = YoutubeDownloader()
    
    # Exemple 1: Télécharger une playlist
    # playlist_url = "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
    # downloader.download_playlist(playlist_url)
    
    # Exemple 2: Télécharger une vidéo
    # video_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
    # downloader.download_video(video_url)
    
    # Exemple 3: Automatiser depuis un fichier d'URLs
    # downloader.automate_download("./yt_download/urls.txt")
    
    # Exemple 4: Pipeline complet
    # downloader.automate_download(
    #     "./yt_download/urls.txt", 
    #     run_full_pipeline=True,
    #     hf_repo="username/repo-name"
    # )
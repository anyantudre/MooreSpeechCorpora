"""
Youtube Crawler for https://www.youtube.com/
Author: @anyantudre
"""

import os
import subprocess
from pytubefix import Playlist, YouTube

from preprocessing.utils import sanitize_filename



class YoutubeCrawler:
    """Class to crawl playlists and videos from YouTube."""
    
    def __init__(self, output_dir="datasets/moore/youtube/raw"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def download_playlist(
            self, 
            playlist_url, 
        ):
        output_dir = self.output_dir
        
        try:
            playlist_name = playlist_url.split('list=')[-1]
            folder_name = f"playlist_{playlist_name}"
            playlist_folder = os.path.join(output_dir, folder_name)
            
            if not os.path.exists(playlist_folder):
                os.makedirs(playlist_folder)
            
            playlist = Playlist(playlist_url)
            print(f"\n\n ================ Downloading playlist: {playlist.title}   =============== \n")
            
            for video in playlist.videos:
                try:
                    print(f"\n Processing video: {video.title}")
                    
                    sanitized_title = sanitize_filename(video.title)
                    file_path = os.path.join(playlist_folder, f"{sanitized_title}.mp3")
                    
                    if os.path.exists(file_path):
                        print(f"File already exists: {file_path}. Download ignored.")
                        continue
                    
                    audio_stream = video.streams.get_audio_only()
                    
                    audio_stream.download(output_path=playlist_folder, filename=f"{sanitized_title}.mp3")
                    print(f"Downloaded: {file_path}")
                    
                except Exception as e:
                    print(f"Error processing video '{video.title}': {e}")
            
            print("\n\n ================ Downloading playlist completed!   =============== \n")
            return playlist_folder
            
        except Exception as e:
            print(f"Error downloading playlist: {e}")
            return None
    
    def download_video(
            self, 
            video_url, 
        ):
        output_dir = self.output_dir
        
        try:
            print(f"\n\n ================ Downloading audio from {video_url}...   =============== \n")
            
            yt = YouTube(video_url)
            video = yt.streams.filter(only_audio=True).first()
            
            original_title = yt.title
            sanitized_title = sanitize_filename(original_title)
            
            downloaded_file = os.path.join(output_dir, sanitized_title + ".mp4")
            
            if os.path.exists(downloaded_file):
                print(f"File already exists: {downloaded_file}. Download ignored.")
                return downloaded_file
            
            downloaded_file = video.download(output_path=output_dir, filename=sanitized_title + ".mp4")
            
            print(f"Audio file downloaded: {downloaded_file}")
            return downloaded_file
            
        except Exception as e:
            print(f"Error downloading {video_url}: {e}")
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
            print(f"Error reading file {urls_file_path}: {e}")
            return []
    
    def automate_download(
            self, 
            urls_source, 
            run_full_pipeline=False, 
            **pipeline_kwargs
        ):
        results = {
            'downloaded_paths': [],
            'pipeline_completed': False,
            'error': None
        }
        
        try:
            print("\n\n ================ PHASE 1: DOWNLOADING   =============== \n")
            
            if isinstance(urls_source, str):
                downloaded_paths = self.download_from_file(urls_source)
            elif isinstance(urls_source, list):
                downloaded_paths = self.download_from_urls_list(urls_source)
            else:
                raise ValueError("urls_source must be a file path or a list of URLs")
            
            results['downloaded_paths'] = downloaded_paths
            
            if not downloaded_paths:
                results['error'] = "No file downloaded"
                return results
            
            if run_full_pipeline:
                print("\n\n ================ PHASE 2: PIPELINE COMPLETED   =============== \n")
                
                raw_data_dir = pipeline_kwargs.get('raw_data_dir', 'datasets/moore/youtube/raw')
                chunked_data_dir = pipeline_kwargs.get('chunked_data_dir', 'datasets/moore/youtube/chunk')
                hf_repo = pipeline_kwargs.get('hf_repo')
                min_duration = pipeline_kwargs.get('min_duration', 2)
                max_duration = pipeline_kwargs.get('max_duration', 12)
                
                if not hf_repo:
                    results['error'] = "hf_repo required for full pipeline"
                    return results

                print("Conversion MP3 vers WAV...")
                cmd = f"python preprocessing/convert_to_wav.py -i \"{self.output_dir}\" -o \"{raw_data_dir}\""
                subprocess.run(cmd, shell=True)
                
                print("Creating chunks and filtering...")
                cmd = f"python ./create_dataset/create-ljspeech.py -i \"{raw_data_dir}\" -o \"{chunked_data_dir}\" --min_duration {min_duration} --max_duration {max_duration}"
                subprocess.run(cmd, shell=True)
                
                print("Creating and pushing to Hugging Face...")
                cmd = f"python ./create_dataset/create_hf_dataset.py -i \"{chunked_data_dir}\" -o \"{chunked_data_dir}\" -r \"{hf_repo}\""
                subprocess.run(cmd, shell=True)
                
                results['pipeline_completed'] = True
                print("\n\n ================ PIPELINE COMPLETED!   =============== \n")
            
            print("\n\n ================ ALL DOWNLOADS AND PROCESSING COMPLETED!   =============== \n")
            
        except Exception as e:
            results['error'] = str(e)
            print(f"Error in automate_download: {e}")
        
        return results
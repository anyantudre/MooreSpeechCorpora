import os
from pydub import AudioSegment
import yt_dlp

# Directory for downloaded and converted audio files
# Directory where downloaded videos will be stored
output_dir = "./data/outputs"
audio_dir = os.path.join(output_dir, "./data/inputs")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)
if not os.path.exists(audio_dir):
    os.makedirs(audio_dir)

# List of YouTube video URLs to download
youtube_urls = [
    "https://www.youtube.com/watch?v=Rkit4YUvTDs",
    "https://www.youtube.com/live/zdvhFMoi5uE?si=t5Ha1ld3oSe0le6x",
    "https://youtu.be/PNJjXdbhX1o?si=RW4-ntbGyNrKbJ0E",
]

# Function to download and convert to WAV using yt-dlp
def download_and_convert_to_wav(url):
    try:
        print(f"Downloading video from {url}...")

        # Download audio using yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info_dict).replace('.webm', '.wav').replace('.m4a', '.wav')
        
        # Move the converted wav file to the audio_dir
        wav_file_final_path = os.path.join(audio_dir, os.path.basename(downloaded_file))
        os.rename(downloaded_file, wav_file_final_path)
        
        print(f"Converted and saved WAV file to {wav_file_final_path}")
        return wav_file_final_path
    except Exception as e:
        print(f"Failed to download or convert {url}: {e}")

# Download and convert all YouTube videos in the list
for url in youtube_urls:
    download_and_convert_to_wav(url)

print("All videos have been processed.")

from pytubefix import YouTube
import os
from pydub import AudioSegment

# Directory where downloaded videos will be stored
output_dir = "./youtube-downloads"
audio_dir = os.path.join(output_dir, "wav-audio")
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

# Function to download YouTube video and convert it to wav format
def download_and_convert_to_wav(url):
    try:
        # Download video
        print(f"Downloading video from {url}...")
        yt = YouTube(url)
        video = yt.streams.filter(only_audio=True).first()  # Only audio

        # Set download path and download
        downloaded_file = video.download(output_path=output_dir)

        # Convert to wav
        base, ext = os.path.splitext(downloaded_file)
        wav_file = f"{base}.wav"
        
        print(f"Converting {downloaded_file} to WAV...")
        audio = AudioSegment.from_file(downloaded_file)
        audio.export(wav_file, format="wav")

        # Move the converted wav file to the audio_dir
        wav_file_final_path = os.path.join(audio_dir, os.path.basename(wav_file))
        os.rename(wav_file, wav_file_final_path)
        
        # Remove original downloaded file (optional)
        os.remove(downloaded_file)
        
        print(f"Converted and saved WAV file to {wav_file_final_path}")
        return wav_file_final_path
    except Exception as e:
        print(f"Failed to download or convert {url}: {e}")

# Download and convert all YouTube videos in the list
for url in youtube_urls:
    download_and_convert_to_wav(url)

print("All videos have been processed.")

import argparse
from pytubefix import YouTube
import os
from helpers.utils import sanitize_filename


### function to download audio from a YouTube video
def download_audio(url, output_dir):
    """Download audio from a given YouTube video URL.

    Args:
        url (str): The URL of the YouTube video.
        output_dir (str): The directory where the downloaded audio will be stored.
    
    Returns:
        str: The path to the downloaded audio file, or None if failed.
    """
    try:
        ### download audio
        print(f"downloading audio from {url}...")
        yt = YouTube(url)
        video = yt.streams.filter(only_audio=True).first()  ### filter for audio only
        
        ### get a sanitized file name
        original_title = yt.title
        sanitized_title = sanitize_filename(original_title)
        
        ### set download path
        downloaded_file = os.path.join(output_dir, sanitized_title + ".mp4")
        
        ### check if the file already exists
        if os.path.exists(downloaded_file):
            print(f"file already exists: {downloaded_file}. Skipping download.")
            return None
        
        ### download audio
        downloaded_file = video.download(output_path=output_dir, filename=sanitized_title + ".mp4")
        
        print(f"downloaded audio file: {downloaded_file}")
        return downloaded_file
    except Exception as e:
        print(f"failed to download {url}: {e}")
        return None



### function to parse command line arguments
def parse_arguments():
    """Parse command line arguments for YouTube audio downloader.

    Returns:
        Namespace: Parsed arguments including YouTube URLs and output directory.
    """
    parser = argparse.ArgumentParser(description="Download audio from YouTube video URLs.")
    parser.add_argument("youtube_urls", nargs='+', help="List of YouTube video URLs to download")
    parser.add_argument("-o", "--output_dir", type=str, default="./youtube-mp3-downloads",
                        help="Directory to save the downloaded audio files (default: './youtube-mp3-downloads')")
    return parser.parse_args()


if __name__ == "__main__":
    ### parse command line arguments
    args = parse_arguments()

    ### create output directory if it doesn't exist
    output_dir = args.output_dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ### download audio files for each URL provided
    for url in args.youtube_urls:
        download_audio(url, output_dir)

    print("all audio files have been downloaded.")

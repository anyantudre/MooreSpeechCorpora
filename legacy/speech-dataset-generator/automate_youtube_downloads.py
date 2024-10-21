### basic usage: python automate_youtube_downloads.py -u "urls.txt" -o "./youtube-mp3-downloads"


import os
import subprocess
import argparse
import re
from urllib.parse import urlparse, parse_qs


### Function to download a YouTube playlist
def download_playlist(playlist_url, output_dir):
    """Download a YouTube playlist and save it to the specified directory."""
    # Extract the playlist name from the URL
    playlist_name = playlist_url.split('list=')[-1]
    folder_name = f"playlist_{playlist_name}"  # Placeholder for playlist name

    # Create the output folder for the playlist
    playlist_folder = os.path.join(output_dir, folder_name)
    os.makedirs(playlist_folder, exist_ok=True)

    # Run the download command
    cmd = f'python yt_download_playlist.py "{playlist_url}" -o "{playlist_folder}"'
    print(f"Downloading playlist: {playlist_url} to {playlist_folder}...")
    subprocess.run(cmd, shell=True)


### Function to download a single YouTube video
def download_video(video_url, output_dir):
    """Download a YouTube video and save it to the specified directory."""
    # Extract video name from the URL
    video_id = parse_qs(urlparse(video_url).query)['v'][0]
    video_name = f"video_{video_id}"  # Placeholder for video name

    # Run the download command
    cmd = f'python yt_download_urls.py "{video_url}" -o "{output_dir}"'
    print(f"Downloading video: {video_url} to {output_dir}...")
    subprocess.run(cmd, shell=True)


### Function to process URLs
def process_urls(urls, output_dir):
    """Process each URL and download playlists or videos accordingly."""
    for url in urls:
        if "playlist" in url:
            download_playlist(url, output_dir)
        else:
            download_video(url, output_dir)


### Function to read URLs from a file
def read_urls_from_file(file_path):
    """Read a list of URLs from a specified file."""
    with open(file_path, 'r') as file:
        urls = file.read().splitlines()
    return [url.strip() for url in urls if url.strip()]


### Function to parse CLI arguments
def parse_arguments():
    """Parse command line arguments for downloading YouTube content."""
    parser = argparse.ArgumentParser(description="Automate downloading YouTube playlists and videos.")
    parser.add_argument("-u", "--urls", type=str, nargs='?', help="Path to a file containing YouTube playlist or video URLs to download.")
    parser.add_argument("-o", "--output_dir", type=str, default="./youtube-mp3-downloads",
                        help="Directory to save downloaded audio files (default: './youtube-mp3-downloads')")
    return parser.parse_args()


if __name__ == "__main__":
    ### Parse the CLI arguments
    args = parse_arguments()

    ### Ensure the output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    ### Read URLs from the file if provided
    if args.urls:
        urls = read_urls_from_file(args.urls)
    else:
        print("No URLs provided. Please specify a file containing URLs.")
        exit(1)

    ### Process the provided URLs
    process_urls(urls, args.output_dir)

    print("All requested playlists and videos have been downloaded.")

import argparse
from pytubefix import Playlist
import os
import sys
from helpers.utils import sanitize_filename


### function to download audio from each video in the playlist as MP3
def download_playlist_mp3(playlist_url, output_dir):
    """Download audio from a YouTube playlist as MP3 files.

    Args:
        playlist_url (str): The URL of the YouTube playlist.
        output_dir (str): The directory where the downloaded MP3 files will be stored.
    """
    try:
        ### load the playlist
        playlist = Playlist(playlist_url)

        print(f"downloading playlist: {playlist.title}")

        ### ensure the output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        ### loop through each video in the playlist and download the audio as MP3
        for video in playlist.videos:
            try:
                print(f"processing video: {video.title}")

                ### sanitize video title for use in file name
                sanitized_title = sanitize_filename(video.title)

                ### set download path with sanitized file name
                file_path = os.path.join(output_dir, f"{sanitized_title}.mp3")

                ### check if the file already exists
                if os.path.exists(file_path):
                    print(f"file already exists: {file_path}. Skipping download.")
                    continue
                
                ### get the audio stream (audio-only in MP3 format)
                audio_stream = video.streams.get_audio_only()

                ### download and save as MP3
                audio_stream.download(output_path=output_dir, filename=f"{sanitized_title}.mp3")

                print(f"downloaded: {file_path}")
            except Exception as e:
                print(f"an error occurred while processing video '{video.title}': {e}")

        print("playlist download complete!")
    except Exception as e:
        print(f"an error occurred while downloading the playlist: {e}")


### function to handle CLI arguments
def parse_arguments():
    """Parse command line arguments for the YouTube playlist audio downloader.

    Returns:
        Namespace: Parsed arguments including playlist URL and output directory.
    """
    parser = argparse.ArgumentParser(description="Download audio from a YouTube playlist as MP3 files.")
    parser.add_argument("playlist_url", type=str, help="the URL of the YouTube playlist")
    parser.add_argument("-o", "--output_dir", type=str, default="./youtube-mp3-downloads",
                        help="directory to save the downloaded MP3 files (default: './youtube-mp3-downloads')")
    return parser.parse_args()


if __name__ == "__main__":
    ### ensure the console can handle the output encoding
    if sys.stdout.encoding != 'utf-8':
        print("Warning: Console output encoding is not UTF-8, which may cause issues with special characters.")

    ### parse the CLI arguments
    args = parse_arguments()
    
    ### run the download function with provided playlist URL and output directory
    download_playlist_mp3(args.playlist_url, args.output_dir)

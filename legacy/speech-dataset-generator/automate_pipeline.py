### basic usage: python automate_pipeline.py -r "ArissBandoss/moore-tts-new-yt-dataset"


import os
import subprocess
import argparse

### Function to convert all MP3s to WAV
def convert_mp3_to_wav(input_dir, output_dir):
    """Convert MP3s from subfolders to WAVs."""
    for root, dirs, files in os.walk(input_dir):
        for folder in dirs:
            folder_path = os.path.join(root, folder)
            print(f"\n\n ================   Converting audios in {folder_path} to WAV...   ================== \n")
            cmd = f"python convert_to_wav.py -i \"{folder_path}\" -o \"{output_dir}\""
            subprocess.run(cmd, shell=True)
    print("All MP3s have been converted to WAVs.")


### Function to create audio chunks and filter
def create_chunks_and_filter(input_dir, output_dir, min_duration=4, max_duration=20):
    """Create chunks from WAVs and filter them based on duration."""
    print(f"\n\n ================   Creating chunks and filtering audios from {input_dir} to {output_dir}...  ================   ")
    cmd = f"python create-ljspeech.py -i \"{input_dir}\" -o \"{output_dir}\" --min_duration {min_duration} --max_duration {max_duration}"
    subprocess.run(cmd, shell=True)
    print("Chunks have been created and filtered.")


### Function to create and push to Hugging Face
def create_and_push_to_hf(input_dir, output_dir, hf_repo):
    """Create Hugging Face dataset and push to the Hugging Face Hub."""
    print(f"Creating Hugging Face dataset from {input_dir} and pushing to {hf_repo}...")
    cmd = f"python create_hf_dataset.py -i \"{input_dir}\" -o \"{output_dir}\" -r \"{hf_repo}\""
    subprocess.run(cmd, shell=True)
    print("Dataset has been created and pushed to Hugging Face.")


### Function to parse CLI arguments
def parse_arguments():
    """Parse command line arguments for automating the pipeline."""
    parser = argparse.ArgumentParser(description="Automate the audio pipeline.")
    parser.add_argument("-i", "--input_dir", type=str, default="./youtube-mp3-downloads",
                        help="Directory containing subfolders with MP3 audio files (default: './youtube-mp3-downloads')")
    parser.add_argument("-raw", "--raw_data_dir", type=str, default="./data/raw_data",
                        help="Directory to save the converted WAV files (default: './data/raw_data')")
    parser.add_argument("-chunked", "--chunked_data_dir", type=str, default="./data/chunked_data",
                        help="Directory to save the chunked audio files (default: './data/chunked_data')")
    parser.add_argument("-r", "--hf_repo", type=str, required=True,
                        help="The Hugging Face repository to push the dataset (e.g., 'username/repo-name')")
    parser.add_argument("--min_duration", type=int, default=4,
                        help="Minimum duration of audio chunks in seconds (default: 4)")
    parser.add_argument("--max_duration", type=int, default=20,
                        help="Maximum duration of audio chunks in seconds (default: 20)")
    return parser.parse_args()


if __name__ == "__main__":
    ### Parse the CLI arguments
    args = parse_arguments()

    ### Step 1: Convert all MP3s in subfolders to WAVs
    convert_mp3_to_wav(args.input_dir, args.raw_data_dir)

    ### Step 2: Create chunks of audios and filter based on duration
    create_chunks_and_filter(args.raw_data_dir, args.chunked_data_dir, args.min_duration, args.max_duration)

    ### Step 3: Create and push the dataset to Hugging Face
    create_and_push_to_hf(args.chunked_data_dir, args.chunked_data_dir, args.hf_repo)

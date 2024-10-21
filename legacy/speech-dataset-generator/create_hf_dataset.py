### basic usage: python create_hf_dataset.py -i ./data/chunked_data -o ./data/chunked_data/audio -r "ArissBandoss/moore-tts-new-yt-dataset"


import argparse
import os
import pandas as pd
import librosa
from datasets import Dataset, DatasetDict, Audio
from huggingface_hub import login
from dotenv import load_dotenv

load_dotenv()
auth_token = os.getenv('HF_TOKEN')
login(token=auth_token)


def create_dataset_from_transcriptions(input_dir, output_dir, repo_id, sample_rate=16000):
    """Convert the transcription output into a DatasetDict format for Hugging Face Hub.

    Args:
        input_dir (str): The directory containing the processed audio and metadata.csv.
        output_dir (str): The directory to save the final dataset files (optional).
        repo_id (str): The Hugging Face Hub repo ID (username/repo_name).
        sample_rate (int): Target sample rate for the audio files (default: 16000).
    """
    # Load metadata CSV
    metadata_csv_path = os.path.join(input_dir, "metadata.csv")
    if not os.path.exists(metadata_csv_path):
        raise FileNotFoundError(f"Metadata file {metadata_csv_path} does not exist!")

    metadata_df = pd.read_csv(metadata_csv_path, sep="|", header=None, names=["ID", "text", "textCleaned"])

    audio_paths = []
    audio_lengths = []

    # Process audio files
    for idx, row in metadata_df.iterrows():
        audio_file = os.path.join(input_dir, "audio", f"{row['ID']}.wav")
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file {audio_file} does not exist!")

        # Load the audio and calculate its length (duration in seconds)
        audio_data, sr = librosa.load(audio_file, sr=sample_rate)
        audio_length = librosa.get_duration(y=audio_data, sr=sample_rate)

        # Store the path (instead of the actual array) for Hugging Face Audio recognition
        audio_paths.append(audio_file)
        audio_lengths.append(audio_length)

    # Create DatasetDict with proper Audio, text, and audio_length columns
    dataset = Dataset.from_dict({
        "audio": audio_paths,
        "text": metadata_df["text"],
        "audio_length": audio_lengths,
        "valid": [1] * len(metadata_df)  # Default 'valid' is 1
    })

    # Cast 'audio' column to the appropriate Audio feature with a sample rate of 16000
    dataset = dataset.cast_column("audio", Audio(sampling_rate=sample_rate))

    dataset_dict = DatasetDict({"train": dataset})

    # Save the dataset locally (optional)
    if output_dir:
        dataset_dict.save_to_disk(output_dir)
        print(f"Dataset saved to {output_dir}")

    # Push to Hugging Face Hub
    print(f"Pushing dataset to Hugging Face Hub at {repo_id}...")
    dataset_dict.push_to_hub(repo_id)
    print("Dataset uploaded successfully!")


def parse_arguments():
    """Parse command line arguments for the dataset creation script."""
    parser = argparse.ArgumentParser(description="Convert transcription output to DatasetDict for Hugging Face.")
    parser.add_argument("-i", "--input_dir", type=str, required=True, help="Directory containing transcriptions (metadata.csv and audio files).")
    parser.add_argument("-o", "--output_dir", type=str, help="Directory to save the final dataset files (optional).")
    parser.add_argument("-r", "--repo_id", type=str, required=True, help="Hugging Face repo ID (e.g., username/repo_name).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    # Create dataset and push to Hugging Face Hub
    create_dataset_from_transcriptions(args.input_dir, args.output_dir, args.repo_id)
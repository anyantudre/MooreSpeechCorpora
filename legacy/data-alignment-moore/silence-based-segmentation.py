import os
import argparse
from pydub import AudioSegment
from pydub.silence import split_on_silence
import numpy as np
import nltk
from datasets import load_dataset, Dataset, Audio
from huggingface_hub import login 

nltk.download('punkt')  # tokenizer for sentence splitting
nltk.download('punkt_tab')

def split_audio_on_silence(audio, silence_thresh=-50, min_silence_len=500, output_folder="segments"):
    # Split the audio based on silence
    audio_chunks = split_on_silence(
        audio, 
        min_silence_len=min_silence_len,  # Minimum length of silence (in ms)
        silence_thresh=silence_thresh     # Silence threshold (in dBFS)
    )
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Save each audio segment and store their file paths
    segment_paths = []
    for i, chunk in enumerate(audio_chunks):
        segment_name = f"segment_{i}.mp3"
        segment_path = os.path.join(output_folder, segment_name)
        chunk.export(segment_path, format="mp3")
        segment_paths.append(segment_path)
    
    return segment_paths


def process_row(row, silence_thresh, min_silence_len, output_folder):
    """
    Processes a single row of the dataset by segmenting its audio based on silence,
    and splitting its transcription by sentences.
    
    Args:
        row (dict): A single row of the dataset, containing 'audio' and 'transcription' fields.
        silence_thresh (int): Silence threshold in dBFS.
        min_silence_len (int): Minimum length of silence in milliseconds.
        output_folder (str): Folder to store the segmented audio files.
    
    Returns:
        dict: A dictionary with segmented audio paths and corresponding transcription parts.
    """
    audio_data = row['audio']['array']  # Get the raw audio array
    sample_rate = row['audio']['sampling_rate']  # Get the sample rate

    #print(f"==================DEBUGGING===================> array size {audio_data.shape}")
    #print(f"==================DEBUGGING===================> array type {audio_data.dtype}")
    #print(f"==================DEBUGGING===================> array {audio_data}")

    # Check audio data shape
    if len(audio_data.shape) == 1:  # Mono
        channels = 1
    elif len(audio_data.shape) == 2:  # Stereo
        channels = audio_data.shape[1]
    else:
        raise ValueError("Unsupported audio format")

    # If the audio data is in float format, normalize it and convert to int16
    #if audio_data.dtype == np.float32:
    #    audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)

    # Create an AudioSegment from the array and sample rate
    audio_segment = AudioSegment(
        audio_data.tobytes(), 
        frame_rate=sample_rate, 
        sample_width=2, 
        channels=channels  # Set channels based on audio data shape
    )
    
    # Split the audio into segments based on silence
    #print(f"==================DEBUGGING===================> Splitting the audio into segments")
    audio_segments = split_audio_on_silence(audio_segment, silence_thresh, min_silence_len, output_folder)
    
    # Split the transcription into sentences
    transcription_segments = nltk.tokenize.sent_tokenize(row["transcript"])  # Split transcription into sentences
    
    # If the number of audio segments and transcription segments don't match, we can flag it for manual review
    if len(audio_segments) != len(transcription_segments):
        print(f"Warning: Mismatch between number of audio segments and transcription segments for {row['audio']['path']}")
    
    return {
        "audio_segments": audio_segments,
        "segment_transcriptions": transcription_segments
    }


def process_dataset(dataset, output_folder, silence_thresh, min_silence_len):
    """
    Processes the entire dataset by segmenting all audio files based on silence.
    
    Args:
        dataset (Dataset): Hugging Face dataset containing 'audio' and 'transcription' columns.
        output_folder (str): Folder where segmented audio files will be saved.
        silence_thresh (int): Silence threshold in dBFS.
        min_silence_len (int): Minimum length of silence in milliseconds.
    
    Returns:
        Dataset: A processed dataset with additional columns for segmented audio paths and corresponding transcriptions.
    """
    return dataset.map(lambda row: process_row(row, silence_thresh, min_silence_len, output_folder))


def main():
    """
    Main function to parse command-line arguments and run the audio segmentation process.
    """
    # Command-line argument parsing
    parser = argparse.ArgumentParser(description="Segment long audios based on silence and update Hugging Face dataset")
    
    # Required arguments
    parser.add_argument("--dataset_name", type=str, required=True, help="Name of the Hugging Face dataset (e.g., username/dataset_name)")
    parser.add_argument("--hf_token", type=str, required=True, help="Hugging Face token for authentication")
    parser.add_argument("--output_folder", type=str, required=True, help="Folder to save the segmented audio files")
    parser.add_argument("--output_dataset", type=str, required=True, help="Path to save the processed dataset (JSON format)")
    
    # Optional arguments for silence detection configuration
    parser.add_argument("--silence_thresh", type=int, default=-50, help="Silence threshold in dBFS (default: -50)")
    parser.add_argument("--min_silence_len", type=int, default=500, help="Minimum silence length in milliseconds (default: 500)")

    args = parser.parse_args()

    # Log in to Hugging Face using the provided token
    login(args.hf_token)
    
    # Load the dataset from Hugging Face Hub
    print(f"Loading dataset {args.dataset_name} from Hugging Face Hub...")
    dataset = load_dataset(args.dataset_name)
    
    # Process the dataset by applying silence-based segmentation to each audio file
    print("Processing dataset and segmenting audio files...")
    processed_dataset = process_dataset(dataset["train"], args.output_folder, args.silence_thresh, args.min_silence_len)
    
    # Save the processed dataset
    print(f"Saving processed dataset to {args.output_dataset}...")
    processed_dataset.to_json(args.output_dataset)
    
    print("Audio segmentation completed and dataset saved successfully!")


if __name__ == "__main__":
    main()

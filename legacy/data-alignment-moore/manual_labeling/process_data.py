import os
import argparse
import pandas as pd
from pydub import AudioSegment
from datasets import Dataset, Audio


def process_audio_and_transcripts(audio_dir, transcript_dir, output_dir):
    """
    Processes audio and corresponding transcript files to create audio clips and transcriptions.
    
    Args:
        audio_dir (str): Directory where the original audio files are stored.
        transcript_dir (str): Directory where the transcript files with timestamps are stored.
        output_dir (str): Directory where the processed audio clips will be saved.
    
    Returns:
        List[Dict]: A list of dictionaries where each entry contains the path to an audio clip and its transcription.
    """
    audio_files = os.listdir(audio_dir)
    data = []

    for audio_file in audio_files:
        audio_path = os.path.join(audio_dir, audio_file)
        # Automatically detect the file type based on the extension
        audio = AudioSegment.from_file(audio_path)  # Instead of from_wav(), use from_file() for format detection
        audio_filename = os.path.splitext(audio_file)[0]

        transcript_path = os.path.join(transcript_dir, f'{audio_filename}.txt')

        with open(transcript_path, 'r') as f:
            for line in f:
                # Parsing the start time, end time, and transcription from the .txt file
                #print(f"\n\n==============DEBUGG=============> line: {line}")
                #print(f"\n\n==============DEBUGG=============> file: {audio_file}")

                start_time, end_time, transcription = line.strip().split('\t', 2)

                # Convert start and end times from seconds to milliseconds
                start_time_ms = float(start_time) * 1000
                end_time_ms = float(end_time) * 1000

                # Extract audio clip
                audio_clip = audio[start_time_ms:end_time_ms]

                # Save the clipped audio segment to output directory
                clip_filename = f"{audio_filename}_{start_time_ms}_{end_time_ms}.wav"
                clip_filepath = os.path.join(output_dir, clip_filename)
                audio_clip.export(clip_filepath, format="wav")

                # Store the audio file path and its transcription
                data.append({
                    "audio": clip_filepath,
                    "transcription": transcription.strip('"'),
                    "audio_duration": float(end_time) - float(start_time)
                })

    return data



def create_hf_dataset(data, output_dataset_path):
    """
    Creates a Hugging Face Dataset from the processed audio-transcription pairs.
    
    Args:
        data (List[Dict]): A list of dictionaries with keys 'audio' and 'transcription'.
        output_dataset_path (str): Path to save the Hugging Face dataset.
    
    Returns:
        Dataset: The Hugging Face Dataset object created from the data.
    """

    # Convert the list of dictionaries into a Pandas DataFrame
    df = pd.DataFrame(data)

    # Create the Hugging Face Dataset from the DataFrame
    dataset = Dataset.from_pandas(df)
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))

    # Save the dataset to the specified path
    dataset.save_to_disk(output_dataset_path)

    return dataset


def main(audio_dir, transcript_dir, output_dir, output_dataset_path):
    """
    Main function to process audio and transcripts, and generate a Hugging Face Dataset.
    
    Args:
        audio_dir (str): Directory containing the original audio files.
        transcript_dir (str): Directory containing the transcript files with timestamps.
        output_dir (str): Directory to save the clipped audio segments.
        output_dataset_path (str): Path to save the final Hugging Face dataset.
    """
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process audio and transcripts
    print(f"Processing audio files from '{audio_dir}' and corresponding transcripts from '{transcript_dir}'...")
    data = process_audio_and_transcripts(audio_dir, transcript_dir, output_dir)

    # Create Hugging Face dataset
    print(f"Creating Hugging Face dataset at '{output_dataset_path}'...")
    dataset = create_hf_dataset(data, output_dataset_path)

    print("Dataset creation complete!")
    print(dataset)


if __name__ == "__main__":
    # Argument parser for command-line execution
    parser = argparse.ArgumentParser(description="Process audio files and transcripts to create a Hugging Face dataset.")
    parser.add_argument('--audio_dir', type=str, required=True, help="Directory containing the audio files.")
    parser.add_argument('--transcript_dir', type=str, required=True, help="Directory containing the transcript files.")
    parser.add_argument('--output_dir', type=str, required=True, help="Directory to save the processed audio clips.")
    parser.add_argument('--output_dataset_path', type=str, required=True, help="Path to save the Hugging Face dataset.")

    args = parser.parse_args()

    # Execute the main function with provided arguments
    main(args.audio_dir, args.transcript_dir, args.output_dir, args.output_dataset_path)
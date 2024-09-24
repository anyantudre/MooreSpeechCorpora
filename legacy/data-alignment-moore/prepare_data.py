import os
import argparse
import pandas as pd
import soundfile as sf
from datasets import Dataset, Audio


def process_audios(folder_path="./raw_data", output_path="./processed_data"):
    data = []

    # Ensure the output folder exists
    os.makedirs(output_path, exist_ok=True)

    # Iterate through the files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith(".mp3"):
            audio_path = os.path.join(folder_path, filename)
            transcript_path = os.path.join(folder_path, filename.replace(".mp3", ".txt"))
            
            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = f.read().strip()

            # Get audio metadata (duration, sampling rate, etc.)
            audio_info = sf.info(audio_path)
            
            data.append({
                "audio": audio_path,
                "transcript": transcript,
                "sampling_rate": audio_info.samplerate,
                "duration": audio_info.duration
            })

    # Convert to a pandas DataFrame
    df = pd.DataFrame(data)

    # Save the DataFrame to a CSV file
    df_csv_path = os.path.join(output_path, "processed_data.csv")
    df.to_csv(df_csv_path, index=False)
    print(f"DataFrame saved to {df_csv_path}")

    # Convert the DataFrame into a Hugging Face Dataset
    dataset = Dataset.from_pandas(df)

    # Format the "audio" column to contain actual audio data
    dataset = dataset.cast_column("audio", Audio())

    # Save the dataset to disk
    dataset_path = os.path.join(output_path, "hf_dataset")
    dataset.save_to_disk(dataset_path)
    print(f"Hugging Face dataset saved to {dataset_path}")


if __name__ == "__main__":
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Process MP3 audio files and transcripts.")
    
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the folder containing MP3 files and transcripts.")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to the folder where the processed data should be saved.")
    
    # Parse command-line arguments
    args = parser.parse_args()
    
    # Call the processing function
    process_audios(args.input_folder, args.output_folder)

### basic usage:  python create-ljspeech.py -i "./data/raw_data" -o "./data/chunked_data" --min_duration 4 --max_duration 20

import argparse
from pydub import AudioSegment
from pydub.silence import split_on_silence
import pandas as pd
import os
import glob
import numpy as np
import torch
from dotenv import load_dotenv
from transformers import WhisperProcessor, WhisperForConditionalGeneration, pipeline
from huggingface_hub import login

load_dotenv()
auth_token = os.getenv('HF_TOKEN')
login(token=auth_token)

device = 0 if torch.cuda.is_available() else "cpu"


def transcribe(inputs, model, language):
    if inputs is None:
        print("No audio file submitted!")
        return None
    
    pipe = pipeline(
        task="automatic-speech-recognition",
        model=model,
        device=device,
        return_timestamps=True
    )
    
    output = pipe(inputs)
    return output['text']



### function to process audio files
def process_audio_files(input_dir, output_dir, min_duration=3, max_duration=15):
    """Process audio files to split them into chunks, transcribe them, and save metadata.

    Args:
        input_dir (str): The directory containing the input WAV files.
        output_dir (str): The directory to save chunked audio files and metadata.
        min_duration (float): Minimum duration for audio chunks in seconds.
        max_duration (float): Maximum duration for audio chunks in seconds.
    """
    audio_dir = os.path.join(output_dir, "audio")
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    metadata = []

    ### parameters for splitting on silence
    min_silence_len = 500  ### minimum length of silence (in ms) to be used for a split
    silence_thresh = None  ### will be calculated for each file
    keep_silence = 200  ### amount of silence (in ms) to leave at the beginning and end of each chunk

    ### get list of all WAV files in the directory, sorted alphabetically
    wav_files = sorted(glob.glob(os.path.join(input_dir, "*.wav")))

    for wav_file in wav_files:
        ### load audio file
        print("--> Processing " + wav_file)
        audio = AudioSegment.from_wav(wav_file)

        ### calculate silence threshold for the current file
        if silence_thresh is None:
            silence_thresh = audio.dBFS - 14

        ### split the audio into chunks based on silence
        audio_chunks = split_on_silence(audio, 
                                        min_silence_len=min_silence_len, 
                                        silence_thresh=silence_thresh, 
                                        keep_silence=keep_silence)

        ### transcribe each chunk and save with metadata
        for i, chunk in enumerate(audio_chunks):
            chunk_duration_sec = len(chunk) / 1000.0  ### chunk duration in seconds

            ### discard chunks that don't meet the duration criteria
            if chunk_duration_sec < min_duration or chunk_duration_sec > max_duration:
                print(f"Skipping chunk {i} (Duration: {chunk_duration_sec:.2f} seconds)")
                continue

            ### convert chunk to mono if it's not
            chunk = chunk.set_channels(1)

            ### convert chunk to numpy array
            audio_data = np.array(chunk.get_array_of_samples(), dtype=np.float32)

            ### normalize the audio data to [-1.0, 1.0]
            audio_data /= np.max(np.abs(audio_data))

            ### export chunk as temporary wav file
            chunk_path = os.path.join(output_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")

            ### transcribe chunk
            result = transcribe(
                        inputs=chunk_path, 
                        model="ArissBandoss/whisper-small-mos", 
                        language="fr",
                    )

            ### get the transcribed text
            text = result.strip()

            ### save chunk with unique ID
            sentence_id = f"LJ{str(len(metadata) + 1).zfill(4)}"
            sentence_path = os.path.join(audio_dir, f"{sentence_id}.wav")
            chunk.export(sentence_path, format="wav")

            metadata.append({
                "ID": sentence_id,
                "text": text,
                "textCleaned": text.lower()  ### TODO: Add textcleaner library (multilanguage support)
            })

            print(f"Transcription for {sentence_id} =====> {text}\n\n")

            ### remove temporary chunk file
            os.remove(chunk_path)

    ### create a metadata.csv file with sentences and corresponding audio file IDs
    metadata_df = pd.DataFrame(metadata)
    metadata_csv_path = os.path.join(output_dir, "metadata.csv")
    metadata_df.to_csv(metadata_csv_path, sep="|", header=False, index=False)

    print(f"Processed {len(metadata)} sentences.")
    print(f"CSV file saved to {metadata_csv_path}")



### function to handle CLI arguments
def parse_arguments():
    """Parse command line arguments for the audio processing script.

    Returns:
        Namespace: Parsed arguments including input and output directories.
    """
    parser = argparse.ArgumentParser(description="Process WAV audio files into chunks and transcribe them.")
    parser.add_argument("-i", "--input_dir", type=str, required=True, help="the directory containing the input WAV files")
    parser.add_argument("-o", "--output_dir", type=str, required=True, help="the directory to save chunked audio files and metadata")
    parser.add_argument("--min_duration", type=float, default=3, help="Minimum duration for audio chunks in seconds")
    parser.add_argument("--max_duration", type=float, default=15, help="Maximum duration for audio chunks in seconds")
    return parser.parse_args()


if __name__ == "__main__":
    ### parse the CLI arguments
    args = parse_arguments()

    ### process the audio files in the specified input directory and save to output directory
    process_audio_files(args.input_dir, args.output_dir, min_duration=args.min_duration, max_duration=args.max_duration)
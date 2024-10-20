import argparse
from pydub import AudioSegment
from pydub.silence import split_on_silence
import pandas as pd
import os
import glob

from transformers import WhisperProcessor, WhisperForConditionalGeneration


### login to hugging face please!!!


### load model and processor
processor = WhisperProcessor.from_pretrained("ArissBandoss/whisper-small-mos")
model = WhisperForConditionalGeneration.from_pretrained("ArissBandoss/whisper-small-mos")
forced_decoder_ids = processor.get_decoder_prompt_ids(language="french", task="transcribe")


### function to process audio files
def process_audio_files(input_dir, output_dir):
    """Process audio files to split them into chunks, transcribe them, and save metadata.

    Args:
        input_dir (str): The directory containing the input WAV files.
        output_dir (str): The directory to save chunked audio files and metadata.
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
        audio_chunks = split_on_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh, keep_silence=keep_silence)

        ### transcribe each chunk and save with metadata
        for i, chunk in enumerate(audio_chunks):
            ### export chunk as temporary wav file
            chunk_path = os.path.join(output_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")

            ### transcribe chunk
            input_features = processor(chunk, sampling_rate=16000, return_tensors="pt").input_features

            ### generate token ids
            predicted_ids = model.generate(input_features, forced_decoder_ids=forced_decoder_ids)
            result = processor.batch_decode(predicted_ids, skip_special_tokens=True)

            ### get the transcribed text
            text = result[0].strip()

            ### save chunk with unique ID
            sentence_id = f"LJ{str(len(metadata) + 1).zfill(4)}"
            sentence_path = os.path.join(audio_dir, f"{sentence_id}.wav")
            chunk.export(sentence_path, format="wav")

            metadata.append({
                "ID": sentence_id,
                "text": text,
                "textCleaned": text.lower()  ### TODO: Add textcleaner library (multilanguage support)
            })

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
    parser.add_argument("input_dir", type=str, help="the directory containing the input WAV files")
    parser.add_argument("output_dir", type=str, help="the directory to save chunked audio files and metadata")
    return parser.parse_args()


if __name__ == "__main__":
    ### parse the CLI arguments
    args = parse_arguments()

    ### process the audio files in the specified input directory and save to output directory
    process_audio_files(args.input_dir, args.output_dir)



### basic usage: python process_audio.py /path/to/input_dir /path/to/output_dir

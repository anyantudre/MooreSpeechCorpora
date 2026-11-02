### basic usage: python convert_to_wav.py -i "./youtube-mp3-downloads/kibaye-wakato" -o "./data/raw_data"

import argparse
from pydub import AudioSegment
import os
#from utils import sanitize_filename


### function to convert downloaded files to wav
def convert_to_wav(input_file, output_dir):
    """Convert an audio file to WAV format.

    Args:
        input_file (str): The path of the input audio file.
        output_dir (str): The directory where the converted WAV file will be saved.
    
    Returns:
        str: The path of the converted WAV file, or None if conversion failed.
    """
    try:
        print(f"converting {input_file} to WAV...")
        base, ext = os.path.splitext(input_file)
        wav_file = f"{base}.wav"
        
        ### move the wav file to output_dir
        wav_file_final_path = os.path.join(output_dir, os.path.basename(wav_file))

        ### Check if the WAV file already exists
        if os.path.exists(wav_file_final_path):
            print(f"WAV file already exists: {wav_file_final_path}. Skipping conversion.")
            return wav_file_final_path

        ### convert to wav using pydub
        audio = AudioSegment.from_file(input_file)
        audio.export(wav_file, format="wav")
        
        os.rename(wav_file, wav_file_final_path)
        
        print(f"converted and saved WAV file: {wav_file_final_path}")
        return wav_file_final_path
    except Exception as e:
        print(f"failed to convert {input_file}: {e}")
        return None


### function to handle CLI arguments
def parse_arguments():
    """Parse command line arguments for the audio file converter.

    Returns:
        Namespace: Parsed arguments including input directory and output directory.
    """
    parser = argparse.ArgumentParser(description="Convert downloaded audio files to WAV format.")
    parser.add_argument("-i", "--input_dir", type=str, default="./youtube-downloads",
                        help="directory containing the downloaded audio files (default: './youtube-mp3-downloads')")
    parser.add_argument("-o", "--output_dir", type=str, default="./data/wavs",
                        help="directory to save the converted WAV files (default: './data/wavs')")
    return parser.parse_args()



if __name__ == "__main__":
    ### parse the CLI arguments
    args = parse_arguments()

    ### ensure the output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    ### get the list of downloaded files in the input_dir
    downloaded_files = [f for f in os.listdir(args.input_dir) if f.endswith(".mp3")]

    ### convert all downloaded files to wav
    for file in downloaded_files:
        file_path = os.path.join(args.input_dir, file)
        convert_to_wav(file_path, args.output_dir)

    print("all audio files have been converted to WAV.")

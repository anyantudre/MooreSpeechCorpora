import os
import re
from pydub import AudioSegment


def sanitize_filename(filename):
    """Sanitize filename by replacing special characters"""
    sanitized_filename = re.sub(r'[éè]', 'e', filename)
    sanitized_filename = re.sub(r'[à]', 'a', filename)
    sanitized_filename = re.sub(r'[^A-Za-z0-9_.-]', '_', filename)
    return sanitized_filename


def count_audio_files(output_dir):
    audio_extensions = {'.mp3', '.wav'} 
    count = 0
    
    for file in os.listdir(output_dir):
        if os.path.isfile(os.path.join(output_dir, file)):
            _, ext = os.path.splitext(file)
            if ext.lower() in audio_extensions:
                count += 1
    
    return count



def convert_to_wav(input_file, output_dir):
    """Convert an audio file from mp3 to WAV format."""
    try:
        print(f"converting {input_file} to WAV...")
        base, ext = os.path.splitext(input_file)
        wav_file = f"{base}.wav"
        
        #move wav file to output_dir
        wav_file_final_path = os.path.join(output_dir, os.path.basename(wav_file))

        #check if WAV file exists
        if os.path.exists(wav_file_final_path):
            print(f"WAV file already exists: {wav_file_final_path}. Skipping conversion.")
            return wav_file_final_path

        # convert to wav using pydub
        audio = AudioSegment.from_file(input_file)
        audio.export(wav_file, format="wav")
        
        os.rename(wav_file, wav_file_final_path)
        
        print(f"converted and saved WAV file: {wav_file_final_path}")
        return wav_file_final_path
    
    except Exception as e:
        print(f"failed to convert {input_file}: {e}")
        return None



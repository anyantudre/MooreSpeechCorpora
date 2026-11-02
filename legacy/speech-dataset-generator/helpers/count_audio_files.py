import argparse
import os


### function to count audio files in the specified directory
def count_audio_files(output_dir):
    """Count the number of audio files in the given directory.

    Args:
        output_dir (str): The directory to search for audio files.

    Returns:
        int: The count of audio files found.
    """
    audio_extensions = {'.mp3', '.wav'} 
    count = 0
    
    ### iterate through files in the specified directory
    for file in os.listdir(output_dir):
        if os.path.isfile(os.path.join(output_dir, file)):
            _, ext = os.path.splitext(file)
            if ext.lower() in audio_extensions:
                count += 1
    
    return count



### function to handle CLI arguments
def parse_arguments():
    """Parse command line arguments for the audio file counter.

    Returns:
        Namespace: Parsed arguments including output directory.
    """
    parser = argparse.ArgumentParser(description="Count the number of audio files in the specified output directory.")
    parser.add_argument("output_dir", type=str, help="the directory to count audio files in")
    return parser.parse_args()


if __name__ == "__main__":
    ### parse the CLI arguments
    args = parse_arguments()
    
    ### count audio files in the specified directory
    num_files = count_audio_files(args.output_dir)
    
    ### print the result
    print(f"Number of audio files in '{args.output_dir}': {num_files}")
# forced-alignment-moore


# Quick set-up using Codespaces

- Create and activate a virtual environment:
```
virtualenv ~/.venv
source ~/.venv/bin/activate
```

- Install all requirements at once:
```
makefile install
```

# Prepare dataset for Hugging Face Dataset format
Follow following steps to convert a folder with .mp3 audio files and corresponding .txt transcripts into a Hugging Face Dataset format, and then upload it to Hugging Face:

- **Step 1:** Ensure the raw_data folder is structured like this:
```
your_folder/
    audio1.mp3
    audio1.txt
    audio2.mp3
    audio2.txt
    ...
```

- **Step 2:** Load the audio and transcript files and prepare them for the Hugging Face Dataset format.
```
python prepare_data.py --input_folder ./raw_data --output_folder ./processed_data
```
This command with create:
1. **A CSV file** named processed_data.csv that will be saved in the output folder.
2. **A Hugging Face Dataset** that will be saved in a folder called hf_dataset inside the output folder.

- **Step 3:** push the dataset created in the processed_data folder to Hugging Face Hub
First make sure to create a .env file and store your Hugging Face token there:
```
HF_TOKEN=your_hugging_face_token_here
```
then run the following command:
```
python push_to_hf.py --dataset_path ./processed_data/hf_dataset --repo_id ArissBandoss/proverbes-moore-vol2
```

Perfect!!! Now check the uploaded dataset on the repo you gave below (ex: ArissBandoss/proverbes-moore-vol2)


# Audio Segmentation/Alignment based on pauses or silence

How to perform silence-based segmentation on the Hugging Face dataset.

**Note:** This won't align perfectly with transcription but can serve as an approximate solution and then we can manually align the segments with the corresponding transcriptions.


# Manual Data labeling using Audacity

- Step 1: Manually label audios using Audacity
For each audio file, you should have a corresponding .txt file with three fields: start time, end time, and the transcription. The structure of each .txt file should look something like this:
```
0.00, 5.35, "This is the first sentence."
5.36, 10.15, "This is the second sentence."
```

After ensure that .txt files and audio files are structured in a folder:
```
/dataset
  /audios
    audio_1.wav
    audio_2.wav
  /transcripts
    audio_1.txt
    audio_2.txt
```

- Step 2: Process the Data with the following command
```
python process_data.py --audio_dir audios/     --transcript_dir transcripts/ --output_dir clips/ --output_dataset_path processed_data/
```

- **Step 3:** push the dataset created  to Hugging Face Hub
Make sure to have the HF token in the .env file:
```
HF_TOKEN=your_hugging_face_token_here
```
then run the following command:
```
python push_to_hf.py
```

Perfect!!! Now check the uploaded dataset on the repo you gave below (ex: ArissBandoss/proverbes-moore-vol2)
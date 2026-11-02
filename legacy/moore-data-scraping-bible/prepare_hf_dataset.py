import logging
import json
from pathlib import Path

import datasets
from datasets import DatasetDict

# don't forget to run `huggingface-cli login` to set your HF token in the environment

logging.disable(logging.INFO)
logging.disable(logging.DEBUG)
logging.disable(logging.WARNING)

# features: audio (16 kHz), transcription (string), duration (float), chapter (string)
features = datasets.Features({
    "audio": datasets.features.Audio(sampling_rate=16_000),
    "transcription": datasets.Value("string"),
    "duration": datasets.Value("float"),
    "chapter": datasets.Value("string"),
})

# Generator function that walks through each chapter folder and yields one example per aligned segment
def dataset_generator(input_folder: str):
    input_folder = Path(input_folder)
    for chapter_dir in sorted(input_folder.glob("*/")):
        manifest_path = chapter_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        for line in open(manifest_path, "r", encoding="utf-8"):
            entry = json.loads(line.strip())  # Unicode escapes become real characters here
            audio_fp = entry["audio_filepath"]
            # Strip leading "../" if present so we don't duplicate the prefix
            if audio_fp.startswith("../"):
                audio_fp = audio_fp[3:]
            # Now audio_fp is like "MooreBible/aligned/Mooré/CHAPTER/segmentXX.flac"
            text = entry["text"]
            duration = round(entry["duration"], 2)
            chapter = chapter_dir.name
            yield {
                "audio": audio_fp,
                "transcription": text,
                "duration": duration,
                "chapter": chapter
            }

# create Dataset from the generator
raw_dataset = datasets.Dataset.from_generator(
    dataset_generator,
    features=features,
    gen_kwargs={ "input_folder": "MooreBible/aligned/Mooré" }
).cast_column("audio", datasets.Audio())  # cast 'audio' to an Audio feature

dataset_dict: DatasetDict = raw_dataset.train_test_split(test_size=0.10, seed=2025)

# inspect a few examples to verify Unicode is correct
print("→ A training example:", dataset_dict["train"][0])
print("→ A testing example: ", dataset_dict["test"][0])

# push to HF
repo_id = "anyantudre/moore-audios-bible"
dataset_dict.push_to_hub(repo_id)

print(f"Successfully pushed dataset to: https://huggingface.co/{repo_id}")

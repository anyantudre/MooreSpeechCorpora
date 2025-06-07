import json
import argparse
from pathlib import Path
import datasets
from datasets import Dataset

def parse_args():
    parser = argparse.ArgumentParser(description="Upload aligned audio dataset to Hugging Face Hub")
    parser.add_argument("--input_folder", required=True, help="Path to aligned chapter folders")
    parser.add_argument("--repo_id", required=True, help="Hugging Face repo ID to upload to")
    parser.add_argument("--hf_token", required=False, help="Optional HF token (if not already logged in)")
    return parser.parse_args()

def dataset_generator(input_folder: str):
    input_folder = Path(input_folder)
    for chapter_dir in sorted(input_folder.glob("*/")):
        manifest_path = chapter_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        for line in open(manifest_path, "r", encoding="utf-8"):
            entry = json.loads(line.strip())
            audio_fp = entry["audio_filepath"]
            if audio_fp.startswith("../"):
                audio_fp = audio_fp[3:]
            yield {
                "audio": audio_fp,
                "transcription": entry["text"],
                "duration": round(entry["duration"], 2),
                "chapter": chapter_dir.name
            }


def main():
    args = parse_args()

    if args.hf_token:
        from huggingface_hub import login
        login(token=args.hf_token)

    features = datasets.Features({
        "audio": datasets.features.Audio(sampling_rate=16_000),
        "transcription": datasets.Value("string"),
        "duration": datasets.Value("float"),
        "chapter": datasets.Value("string"),
    })

    # Collect examples in a list to compute total duration
    examples = list(dataset_generator(args.input_folder))

    total_duration_sec = sum(x["duration"] for x in examples)
    total_hours = total_duration_sec / 3600

    dataset = Dataset.from_list(examples, features=features).cast_column("audio", datasets.Audio())

    dataset.push_to_hub(args.repo_id)
    print(f"✅ Successfully pushed to https://huggingface.co/datasets/{args.repo_id}")
    print(f"🎉 Total audio duration: {total_hours:.2f} hours")


if __name__ == "__main__":
    main()

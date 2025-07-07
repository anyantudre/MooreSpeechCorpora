from pathlib import Path
import argparse
import json
import sys

from datasets import Dataset
import datasets


def parse_args():
    parser = argparse.ArgumentParser(description="Upload aligned audio dataset to Hugging Face Hub")
    parser.add_argument("--input_folder", required=True, help="Path to aligned chapter folders")
    parser.add_argument("--repo_id", required=True, help="Hugging Face repo ID to upload to")
    parser.add_argument("--split", required=False, default="train", help="Dataset split name (default: train)")
    parser.add_argument("--hf_token", required=False, help="Optional HF token (if not already logged in)")
    return parser.parse_args()

def dataset_generator(input_folder: Path):
    for chapter_dir in sorted(input_folder.glob("*/")):
        manifest_path = chapter_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
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
    input_path = Path(args.input_folder)
    if not input_path.is_dir():
        print(f"Error: input_folder '{args.input_folder}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)

    if args.hf_token:
        from huggingface_hub import login
        login(token=args.hf_token)

    features = datasets.Features({
        "audio": datasets.features.Audio(sampling_rate=16_000),
        "transcription": datasets.Value("string"),
        "duration": datasets.Value("float"),
        "chapter": datasets.Value("string"),
    })

    examples = list(dataset_generator(input_path))
    if not examples:
        print(f"Error: no examples found under '{args.input_folder}'. Check your path and folder structure.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(examples)} examples")

    total_duration_sec = sum(x["duration"] for x in examples)
    total_hours = total_duration_sec / 3600

    dataset = Dataset.from_list(examples, features=features).cast_column("audio", datasets.Audio())
    dataset.push_to_hub(args.repo_id, split=args.split, private=True)

    print(f"✅ Successfully pushed to https://huggingface.co/datasets/{args.repo_id}")
    print(f"🎉 Total audio duration: {total_hours:.2f} hours")


if __name__ == "__main__":
    main()

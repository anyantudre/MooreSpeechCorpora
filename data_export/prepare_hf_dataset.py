from pathlib import Path
import argparse
import json
import sys

from datasets import Dataset
import datasets


def get_first_sentence(text):
    """Extract only the first sentence (before first period)"""
    first_sentence = text.split('.')[0].strip()
    return first_sentence + '.' if first_sentence else text


def parse_args():
    parser = argparse.ArgumentParser(description="Upload aligned audio dataset to Hugging Face Hub")
    parser.add_argument("--input_folder", required=True, help="Path to aligned chapter folders")
    parser.add_argument("--repo_id", required=True, help="Hugging Face repo ID to upload to")
    parser.add_argument("--split", required=False, default="train", help="Dataset split name (default: train)")
    parser.add_argument("--hf_token", required=False, help="Optional HF token (if not already logged in)")
    parser.add_argument("--remove_duplicates", action="store_true", help="Keep only the first sentence in transcription")
    return parser.parse_args()

def dataset_generator(input_folder: Path, remove_duplicates=False):
    #tokens to filter out (noise/music segments)
    filter_tokens = {"silence", "<star>"}
    
    for chapter_dir in sorted(input_folder.glob("*/")):
        manifest_path = chapter_dir / "manifest.json"
        if not manifest_path.exists():
            continue
            
        # Extract metadata from folder name (format: idx_speaker_id_voice)
        folder_parts = chapter_dir.name.split('_')
        if len(folder_parts) >= 3:
            speaker_id = folder_parts[1] 
            voice = folder_parts[2]
        else:
            # Fallback for other naming formats
            speaker_id = "unknown"
            voice = "unknown"
            
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line.strip())
                
                #skip noise/music segments
                if entry["normalized_text"].strip() in filter_tokens:
                    continue
                
                transcription = entry["normalized_text"]
                if remove_duplicates:
                    transcription = get_first_sentence(transcription)
                    
                audio_fp = entry["audio_filepath"]
                if audio_fp.startswith("../"):
                    audio_fp = audio_fp[3:]
                yield {
                    "audio": audio_fp,
                    "transcription": transcription,
                    "duration": round(entry["duration"], 2),
                    "voice": voice,
                    "speaker_id": speaker_id,
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
        "voice": datasets.Value("string"),
        "speaker_id": datasets.Value("string"),
        "chapter": datasets.Value("string"),
    })

    examples = list(dataset_generator(input_path, args.remove_duplicates))
    if not examples:
        print(f"Error: no examples found under '{args.input_folder}'. Check your path and folder structure.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(examples)} examples")
    if args.remove_duplicates:
        print("✂️ Applied first sentence extraction")

    total_duration_sec = sum(x["duration"] for x in examples)
    total_hours = total_duration_sec / 3600

    dataset = Dataset.from_list(examples, features=features).cast_column("audio", datasets.Audio())
    dataset.push_to_hub(args.repo_id, split=args.split, private=True)

    # #save locally
    # local_path = f"datasets/hf_cache/{args.repo_id.replace('/', '_')}"
    # print(f"💾 Saving dataset locally to {local_path}...")
    # dataset.save_to_disk(local_path)
    
    # #push to hub
    # print(f"📤 Loading and uploading dataset to {args.repo_id}...")
    # local_dataset = Dataset.load_from_disk(local_path)
    # local_dataset.push_to_hub(args.repo_id, split=args.split, private=True)

    print(f"✅ Successfully pushed to https://huggingface.co/datasets/{args.repo_id}")
    print(f"🎉 Total audio duration: {total_hours:.2f} hours")


if __name__ == "__main__":
    main()

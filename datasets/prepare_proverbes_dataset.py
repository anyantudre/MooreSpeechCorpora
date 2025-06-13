# python datasets/prepare_proverbes_dataset.py \
#   --input_folder datasets/proverbes_moore/vol2/aligned/moore \
#   --repo_id anyantudre/moore-speech-proverbes-vol1 \
#   --split "vol2"


from pathlib import Path
import argparse
import json
import sys

from datasets import Dataset
import datasets


def parse_args():
    parser = argparse.ArgumentParser(description="Upload aligned proverbes dataset to Hugging Face Hub")
    parser.add_argument("--input_folder", required=True, help="Path to aligned proverbes folders")
    parser.add_argument("--repo_id", required=True, help="Hugging Face repo ID to upload to")
    parser.add_argument("--split", required=False, default="train", help="Dataset split name (default: train)")
    parser.add_argument("--hf_token", required=False, help="Optional HF token (if not already logged in)")
    return parser.parse_args()

def dataset_generator(input_folder: Path):
    moore_only_examples = []  # Pour les phrases Mooré sans traduction
    
    for chapter_dir in sorted(input_folder.glob("*/")):
        manifest_path = chapter_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f]
            #print(lines)
        
        # Traite par groupes de 3 (mooré, français, mooré)
        # for i in range(0, len(lines), 3):
        #     if i + 2 >= len(lines):
        #         break
                
        #     moore1 = lines[i]     # Premier segment Mooré
        #     french = lines[i + 1] # Segment français
        #     moore2 = lines[i + 2] # Deuxième segment Mooré
            
        #     # Nettoie les chemins audio
        #     moore1_audio = moore1["audio_filepath"][3:] if moore1["audio_filepath"].startswith("../") else moore1["audio_filepath"]
        #     french_audio = french["audio_filepath"][3:] if french["audio_filepath"].startswith("../") else french["audio_filepath"]
        #     moore2_audio = moore2["audio_filepath"][3:] if moore2["audio_filepath"].startswith("../") else moore2["audio_filepath"]
            
        #     # Premier pair Mooré-Français
        #     yield {
        #         "moore_audio": moore1_audio,
        #         "moore_text": moore1["text"],
        #         "french_text": french["text"],
        #         "french_audio": french_audio,
        #         "duration_moore": round(moore1["duration"], 2),
        #         "duration_french": round(french["duration"], 2),
        #         "chapter": chapter_dir.name
        #     }
            
        #     # Deuxième pair Mooré-Français (français répété)
        #     yield {
        #         "moore_audio": moore2_audio,
        #         "moore_text": moore2["text"],
        #         "french_text": french["text"],  # Répété
        #         "french_audio": french_audio,   # Répété
        #         "duration_moore": round(moore2["duration"], 2),
        #         "duration_french": round(french["duration"], 2),
        #         "chapter": chapter_dir.name
        #     }


        # réadapté pour le vol11
        i = 0
        while i < len(lines):
            moore = lines[i]
            
            # Vérifier s'il y a une ligne suivante et si c'est du français
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Si la ligne suivante contient des caractères Mooré, c'est du Mooré (pas du français)
                if any(c in next_line["text"] for c in ["ã", "ẽ", "ɛ", "ĩ", "ɩ", "õ", "ũ", "ʋ"]):
                    # Phrase Mooré sans traduction française
                    moore_audio = moore["audio_filepath"][3:] if moore["audio_filepath"].startswith("../") else moore["audio_filepath"]
                    moore_only_examples.append({
                        "moore_audio": moore_audio,
                        "moore_text": moore["text"],
                        "duration_moore": round(moore["duration"], 2),
                        "chapter": chapter_dir.name
                    })
                    i += 1  # Passer à la ligne suivante
                    continue
                
                # Sinon, c'est une paire Mooré-Français normale
                french = next_line
                moore_audio = moore["audio_filepath"][3:] if moore["audio_filepath"].startswith("../") else moore["audio_filepath"]
                french_audio = french["audio_filepath"][3:] if french["audio_filepath"].startswith("../") else french["audio_filepath"]
                
                yield {
                    "moore_audio": moore_audio,
                    "moore_text": moore["text"],
                    "french_text": french["text"],
                    "french_audio": french_audio,
                    "duration_moore": round(moore["duration"], 2),
                    "duration_french": round(french["duration"], 2),
                    "chapter": chapter_dir.name
                }
                i += 2  # Passer aux deux lignes suivantes
            else:
                # Dernière ligne, forcément Mooré seul
                moore_audio = moore["audio_filepath"][3:] if moore["audio_filepath"].startswith("../") else moore["audio_filepath"]
                moore_only_examples.append({
                    "moore_audio": moore_audio,
                    "moore_text": moore["text"],
                    "duration_moore": round(moore["duration"], 2),
                    "chapter": chapter_dir.name
                })
                i += 1

def get_moore_only_examples(input_folder: Path):
    moore_only_examples = []  
    
    for chapter_dir in sorted(input_folder.glob("*/")):
        manifest_path = chapter_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f]

        i = 0
        while i < len(lines):
            moore = lines[i]
            
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if any(c in next_line["text"] for c in ["ã", "ẽ", "ɛ", "ĩ", "ɩ", "õ", "ũ", "ʋ"]):
                    moore_audio = moore["audio_filepath"][3:] if moore["audio_filepath"].startswith("../") else moore["audio_filepath"]
                    moore_only_examples.append({
                        "moore_audio": moore_audio,
                        "moore_text": moore["text"],
                        "duration_moore": round(moore["duration"], 2),
                        "chapter": chapter_dir.name
                    })
                    i += 1
                    continue
                i += 2
            else:
                moore_audio = moore["audio_filepath"][3:] if moore["audio_filepath"].startswith("../") else moore["audio_filepath"]
                moore_only_examples.append({
                    "moore_audio": moore_audio,
                    "moore_text": moore["text"],
                    "duration_moore": round(moore["duration"], 2),
                    "chapter": chapter_dir.name
                })
                i += 1
    
    return moore_only_examples


def main():
    args = parse_args()
    input_path = Path(args.input_folder)
    if not input_path.is_dir():
        print(f"❌ Error: input_folder '{args.input_folder}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)

    if args.hf_token:
        from huggingface_hub import login
        login(token=args.hf_token)

    features = datasets.Features({
        "moore_audio": datasets.features.Audio(sampling_rate=16_000),
        "moore_text": datasets.Value("string"),
        "french_text": datasets.Value("string"),
        "french_audio": datasets.features.Audio(sampling_rate=16_000),
        "duration_moore": datasets.Value("float"),
        "duration_french": datasets.Value("float"),
        "chapter": datasets.Value("string"),
    })

    # Générer les exemples Mooré-Français
    examples = list(dataset_generator(input_path))
    # Générer les exemples Mooré seul
    moore_only_examples = get_moore_only_examples(input_path)

    print(f"Loaded {len(examples)} proverbes pairs (Mooré-Français)")
    print(f"Loaded {len(moore_only_examples)} proverbes Mooré uniquement")

    # Dataset principal Mooré-Français
    if examples:
        total_moore_duration = sum(x["duration_moore"] for x in examples)
        total_french_duration = sum(x["duration_french"] for x in examples)
        total_hours_moore = total_moore_duration / 3600
        total_hours_french = total_french_duration / 3600

        dataset = Dataset.from_list(examples, features=features)
        dataset = dataset.cast_column("moore_audio", datasets.Audio())
        dataset = dataset.cast_column("french_audio", datasets.Audio())
        dataset.push_to_hub(args.repo_id, split=args.split, private=True)

        print(f"✅ Successfully pushed Mooré-Français to https://huggingface.co/datasets/{args.repo_id}")
        print(f"🎉 Total Mooré audio: {total_hours_moore:.2f} hours")
        print(f"🎉 Total French audio: {total_hours_french:.2f} hours")

    # Dataset Mooré seul
    if moore_only_examples:
        moore_only_features = datasets.Features({
            "moore_audio": datasets.features.Audio(sampling_rate=16_000),
            "moore_text": datasets.Value("string"),
            "duration_moore": datasets.Value("float"),
            "chapter": datasets.Value("string"),
        })

        moore_only_duration = sum(x["duration_moore"] for x in moore_only_examples)
        moore_only_hours = moore_only_duration / 3600

        moore_dataset = Dataset.from_list(moore_only_examples, features=moore_only_features)
        moore_dataset = moore_dataset.cast_column("moore_audio", datasets.Audio())
        moore_only_repo = f"{args.repo_id}-moore-only"
        moore_dataset.push_to_hub(moore_only_repo, split=args.split, private=True)

        print(f"✅ Successfully pushed Mooré-only to https://huggingface.co/datasets/{moore_only_repo}")
        print(f"🎉 Total Mooré-only audio: {moore_only_hours:.2f} hours")

if __name__ == "__main__":
    main() 
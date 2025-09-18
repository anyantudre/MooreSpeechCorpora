#!/usr/bin/env python3
"""
Reverse Pipeline: Convert HF Dataset back to Raw Format
Author: @anyantudre

Converts Hugging Face dataset with columns (audio, text, duration, voice, speaker_id) 
back to raw format with audio files (.wav) and text files (.txt) for manual correction 
and re-alignment.

Usage:
    python data_export/reverse_hf_to_raw.py \
        --dataset_id anyantudre/MooreSpeechCorpora \
        --output_folder datasets/MooreSpeechCorporaCorrected/raw \
        --split train
"""

from pathlib import Path
import argparse
import sys
import json
from typing import Optional

from datasets import load_dataset
import soundfile as sf


def parse_args():
    parser = argparse.ArgumentParser(description="Convert HF dataset back to raw format")
    parser.add_argument("--dataset_id", required=True, help="Hugging Face dataset ID to download")
    parser.add_argument("--output_folder", required=True, help="Output folder for raw files")
    parser.add_argument("--split", default="train", help="Dataset split to process (default: train)")
    parser.add_argument("--hf_token", required=False, help="Optional HF token (if private dataset)")
    parser.add_argument("--organize_by_speaker", action="store_true", 
                        help="Organize files in speaker subfolders")
    return parser.parse_args()


def create_safe_filename(text: str, max_length: int = 50) -> str:
    """Create a safe filename from text content."""
    # Remove special characters and limit length
    safe_chars = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_chars = safe_chars.replace(' ', '_')[:max_length]
    return safe_chars if safe_chars else "segment"


def main():
    args = parse_args()
    
    # Login if token provided
    if args.hf_token:
        from huggingface_hub import login
        login(token=args.hf_token)
    
    # Create output directory
    output_path = Path(args.output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Loading dataset '{args.dataset_id}' split '{args.split}'...")
    
    try:
        dataset = load_dataset(args.dataset_id, split=args.split, revision="d9a9ce5f53f09047ea44d3367ab5d940a7415ad0")
    except Exception as e:
        print(f"❌ Error loading dataset: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate required columns
    required_columns = ["audio", "text", "duration", "voice", "speaker_id"]
    missing_columns = [col for col in required_columns if col not in dataset.column_names]
    if missing_columns:
        print(f"❌ Missing required columns: {missing_columns}", file=sys.stderr)
        print(f"Available columns: {dataset.column_names}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ Dataset loaded: {len(dataset)} examples")
    print(f"📂 Output folder: {output_path}")
    
    # Create metadata file
    metadata = {
        "dataset_id": args.dataset_id,
        "split": args.split,
        "total_examples": len(dataset),
        "columns": dataset.column_names,
        "speakers": list(set(dataset["speaker_id"])),
        "voices": list(set(dataset["voice"]))
    }
    
    with open(output_path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Process each example
    for idx, example in enumerate(dataset):
        try:
            # Extract data
            audio_data = example["audio"]
            text = example["text"]
            duration = example["duration"]
            voice = example["voice"]
            speaker_id = example["speaker_id"]
            
            # Create filename
            text_prefix = create_safe_filename(text)
            filename = f"{idx:06d}_{speaker_id}_{voice}"
            
            # Determine output directory
            if args.organize_by_speaker:
                file_output_dir = output_path / str(speaker_id)
                file_output_dir.mkdir(exist_ok=True)
            else:
                file_output_dir = output_path
            
            # Save audio file
            audio_file = file_output_dir / f"{filename}.wav"
            sf.write(audio_file, audio_data["array"], audio_data["sampling_rate"])
            
            # Save text file with metadata
            text_file = file_output_dir / f"{filename}.txt"
            with open(text_file, "w", encoding="utf-8") as f:
                # Write text content with distinctive tokens for music/noise parts
                # Using tokens that survive MMS normalization and allow proper segmentation
                # Each line represents a separate segment for alignment
                f.write(f"silence\n")  # Maps to music/noise at start
                f.write(f"{text}\n")  # Maps to actual speech  
                f.write(f"silence\n")  # Maps to music/noise at end
                # Optional: Write metadata as comments at the end
                # f.write(f"# Original Index: {idx}\n")
                # f.write(f"# Duration: {duration}\n")
                # f.write(f"# Voice: {voice}\n")
                # f.write(f"# Speaker ID: {speaker_id}\n")
            
            if (idx + 1) % 100 == 0:
                print(f"  Processed {idx + 1}/{len(dataset)} examples...")
                
        except Exception as e:
            print(f"⚠️  Error processing example {idx}: {e}")
            continue
    
    total_duration = sum(dataset["duration"])
    total_hours = total_duration / 3600
    
    print(f"\n✅ Reverse pipeline completed!")
    print(f"📊 Processed {len(dataset)} examples")
    print(f"🎉 Total audio duration: {total_hours:.2f} hours")
    print(f"📁 Files saved to: {output_path}")
    print(f"\n💡 Next steps:")
    print(f"   1. Manually correct text files in {output_path}")
    print(f"   2. Run resampling: bash preprocessing/resample.sh --input_folder {output_path} --output_folder <resampled_folder>")
    print(f"   3. Run alignment: bash forced_alignement/align_and_segment.sh --audio_folder <resampled_folder> --text_folder <resampled_folder> --output_folder <aligned_folder> --lang mos --uroman_path uroman_tools/bin")


if __name__ == "__main__":
    main() 
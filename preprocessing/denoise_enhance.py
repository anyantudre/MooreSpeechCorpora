import argparse
import sys
import torch

from datasets import load_dataset, Audio, DatasetDict
from resemble_enhance.enhancer.inference import denoise, enhance

device = "cuda" if torch.cuda.is_available() else "cpu"


def parse_args():
    parser = argparse.ArgumentParser(description="Apply denoise/enhance to audio dataset and push to HF Hub")
    parser.add_argument("--dataset_id", required=True, help="Hugging Face dataset ID (e.g. user/my_dataset)")
    parser.add_argument("--output_repo_id", required=True, help="HF repo ID to push enhanced dataset to")
    parser.add_argument("--hf_token", required=False, help="Optional HF token")
    parser.add_argument("--enhance_audio", action="store_true", help="Whether to apply enhancement after denoising (default: False)")
    parser.add_argument("--keep_original_audio", action="store_true", default=True, help="Whether to keep original 'audio' column (default: True)")
    return parser.parse_args()


def denoise_enhance_audio(
        batch,
        solver='midpoint',
        nfe=90,
        tau=0.6,
        denoise_before_enhancement=False,
        apply_enhance=False
    ):
    """
    Process a batch of audio samples by applying denoising and/or enhancement.

    Parameters:
        batch (dict): A dictionary containing a batch of audio data in Hugging Face format,
                      with key 'audio' -> list of {'array', 'sampling_rate'}.
        solver (str): Numerical solver to use for enhancement. Default is 'midpoint'.
        nfe (int): Number of function evaluations for the enhancement process. Default is 90.
        tau (float): Step size or damping factor used in the enhancement. Default is 0.6.
        denoise_before_enhancement (bool): Whether to prioritize denoising before enhancement. Default is True.
        apply_enhance (bool): Whether to run the enhancement step. Default is False.

    Returns:
        dict: A dictionary with new keys:
              'denoised_audio', and optionally 'enhanced_audio', each containing a list of processed audio as numpy arrays.
    """
    lambd = 0.9 if denoise_before_enhancement else 0.1

    denoised_list = []
    enhanced_list = []

    for audio in batch['audio']:
        audio_array,  sampling_rate= audio['array'], audio['sampling_rate']
        audio_tensor = torch.tensor(audio_array, dtype=torch.float32)

        try:
            denoised_audio, new_sr = denoise(audio_tensor, sampling_rate, device)
        except Exception as e:
            print(f"Error during denoising: {e}")
            denoised_audio = audio_tensor

        denoised_list.append({
            "array": denoised_audio.cpu().numpy(),
            "sampling_rate": new_sr
        })

        if apply_enhance:
            try:
                enhanced_audio, new_sr = enhance(audio_tensor, sampling_rate, device, nfe=nfe, solver=solver, lambd=lambd, tau=tau)
            except Exception as e:
                print(f"Error during enhancement: {e}")
                enhanced_audio = audio_tensor

            enhanced_list.append({
                "array": enhanced_audio.cpu().numpy(),
                "sampling_rate": new_sr
            })

    result = {
        "denoised_audio": denoised_list
    }

    if apply_enhance:
        result["enhanced_audio"] = enhanced_list

    return result


def main():
    args = parse_args()

    if args.hf_token:
        from huggingface_hub import login
        login(token=args.hf_token)

    dataset_dict = load_dataset(args.dataset_id)

    processed_dict = DatasetDict()
    for split, dataset in dataset_dict.items():
        print(f"\n🔄 Processing split: {split} with {len(dataset)} examples")
        dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))

        processed = dataset.map(
            lambda batch: denoise_enhance_audio(batch, apply_enhance=args.enhance_audio),
            batched=True,
            batch_size=12,
            writer_batch_size=8,
        )

        processed = processed.cast_column("denoised_audio", Audio(sampling_rate=16000))
        if args.enhance_audio:
            processed = processed.cast_column("enhanced_audio", Audio(sampling_rate=16000))

        if not args.keep_original_audio and "audio" in processed.column_names:
            processed = processed.remove_columns("audio")

        processed_dict[split] = processed

    processed_dict.push_to_hub(args.output_repo_id, private=True)
    print(f"\n✅ Dataset pushed to: https://huggingface.co/datasets/{args.output_repo_id}")


if __name__ == "__main__":
    main()

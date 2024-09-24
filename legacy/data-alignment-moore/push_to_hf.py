import os
import argparse
from datasets import load_from_disk
from huggingface_hub import HfApi

from dotenv import load_dotenv


def login_hugging_face() -> None:
    """
    Loging to Hugging Face portal with a given token.
    """
    load_dotenv()
    HF_TOKEN = os.getenv("HF_TOKEN")

    if HF_TOKEN is None:
        raise ValueError("Hugging Face token not found. Please store it in a .env file.")

    api = HfApi(token=HF_TOKEN)
    #api.set_access_token(token)
    #folder = HfFolder()
    #folder.save_token(token)
    return None


def push_dataset_to_hf(dataset_path="processed_data/hf_dataset", repo_id="ArissBandoss/proverbes-moore-vol2"):
    # Load the dataset from the specified path
    dataset = load_from_disk(dataset_path)

    # Log to HF
    login_hugging_face()

    # Push the dataset to HF
    print(f"Pushing dataset from {dataset_path} to Hugging Face Hub repository {repo_id}...")
    dataset.push_to_hub(repo_id)

    print(f"Yeahh!!! Dataset successfully pushed to {repo_id} !!!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push Hugging Face Dataset to the Hub.")

    parser.add_argument("--dataset_path", type=str, required=True, help="Path to the folder containing the processed dataset.")
    parser.add_argument("--repo_id", type=str, required=True, help="The ID of the Hugging Face dataset repository (e.g., username/repo_name).")

    args = parser.parse_args()

    push_dataset_to_hf(args.dataset_path, args.repo_id)

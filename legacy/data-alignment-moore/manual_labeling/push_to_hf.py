import os
from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

dataset_path = "./processed_data" 
dataset = Dataset.load_from_disk(dataset_path)

api = HfApi(token=HF_TOKEN)

repo_id = "ArissBandoss/bible-moore-audios"
dataset.push_to_hub(repo_id)

print(f"Dataset successfully pushed to Hugging Face Hub at: https://huggingface.co/{repo_id}")

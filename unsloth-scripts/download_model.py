import os
import argparse

os.environ['HF_HOME'] = '/media/data/hf/'
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'


from transformers import AutoTokenizer, AutoModel

def download_model(model_name: str, save_dir: str = "./downloaded_model"):
    """
    Downloads a model and its tokenizer from Hugging Face and saves it locally.

    Args:
        model_name (str): The model name or path from Hugging Face Hub (e.g., "bert-base-uncased").
        save_dir (str): The directory where the model and tokenizer will be saved.
    """
    os.makedirs(save_dir, exist_ok=True)

    print(f"Downloading model and tokenizer: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    tokenizer.save_pretrained(save_dir)
    model.save_pretrained(save_dir)

    print(f"Model and tokenizer saved to: {save_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a Hugging Face transformer model and tokenizer.")
    parser.add_argument("model_name", type=str, help="The model name or path (e.g., 'bert-base-uncased')")
    parser.add_argument("--save_dir", type=str, default="./downloaded_model", help="Directory to save the model and tokenizer")
    args = parser.parse_args()

    download_model(args.model_name, args.save_dir)

import os
from huggingface_hub import snapshot_download

snapshot_download(
    "unsloth/qwen2.5-1.5b-unsloth-bnb-4bit",
    token=os.environ.get('HF_TOKEN'),
)

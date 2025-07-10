import os
os.environ['HF_HOME'] = '/media/data/hf/'
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
import argparse
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TextStreamer,
    BitsAndBytesConfig,
)

def load_model(model_name, device_str, quantization):
    """
    Load the model and tokenizer with optional quantization and device selection.
    """
    print(f"Loading model: {model_name}")

    # Determine device
    if device_str == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_str)

    kwargs = {}

    # Use safe dtype for CPU
    if device.type == "cpu":
        kwargs["torch_dtype"] = torch.float32
    else:
        kwargs["torch_dtype"] = torch.float16
        kwargs["device_map"] = "auto"

        if quantization == "4bit":
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"  # or "fp4" if supported
            )
            kwargs["quantization_config"] = quant_config
        elif quantization == "8bit":
            kwargs["load_in_8bit"] = True

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)

    if device.type == "cpu":
        model.to(device)

    print(f"Model loaded on {device} with quantization: {quantization or 'none'}")
    return tokenizer, model, device


def chat_stream(tokenizer, model, device, max_length=512):
    """
    Interactive chat loop with streaming and optional chat template.
    """
    history = []
    print("\n>>> Interactive chat started. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        history.append({"role": "user", "content": user_input})

        # Format with chat template if available
        if hasattr(tokenizer, "apply_chat_template"):
            prompt = tokenizer.apply_chat_template(
                history,
                tokenize=False,
                add_generation_prompt=True,
                return_tensors=None
            )
        else:
            prompt = "\n".join([f"User: {msg['content']}" if msg["role"] == "user"
                                else f"Assistant: {msg['content']}" for msg in history])
            prompt += "\nAssistant:"

        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

        print("Assistant:", end=" ", flush=True)

        model.generate(
            **inputs,
            max_length=max_length,
            pad_token_id=tokenizer.eos_token_id,
            streamer=streamer,
        )
        print()  # newline

        full_output = tokenizer.decode(inputs["input_ids"][0], skip_special_tokens=True)
        assistant_reply = full_output[len(prompt):].strip()
        history.append({"role": "assistant", "content": assistant_reply})


def main():
    parser = argparse.ArgumentParser(description="Chat with a Hugging Face model with optional quantization and device control.")
    parser.add_argument("model_name", type=str, help="Model ID from Hugging Face hub (e.g., mistralai/Mistral-7B-Instruct-v0.2)")
    parser.add_argument("--max_length", type=int, default=512, help="Maximum generation length")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"], help="Device to run the model on")
    parser.add_argument("--quant", type=str, choices=["4bit", "8bit"], help="Optional quantization: 4bit or 8bit")

    args = parser.parse_args()

    tokenizer, model, device = load_model(args.model_name, args.device, args.quant)
    chat_stream(tokenizer, model, device, args.max_length)


if __name__ == "__main__":
    main()

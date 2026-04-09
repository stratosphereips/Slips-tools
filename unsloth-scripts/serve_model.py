import os
os.environ['HF_HOME'] = '/home/harpo/CEPH/LLM-models/'
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'

import argparse
import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI()

# Global model state
tokenizer = None
model = None
device = None
model_name = None
executor = ThreadPoolExecutor(max_workers=1)


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: list[Message]
    max_completion_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.0
    stream: Optional[bool] = False


def load_model(name, device_str, quantization, alias=None):
    global tokenizer, model, device, model_name
    model_name = alias if alias else name
    print(f"Loading model: {name}")

    if device_str == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_str)

    kwargs = {}
    if device.type == "cpu":
        kwargs["dtype"] = torch.float32
    else:
        kwargs["device_map"] = "auto"

        if quantization == "4bit":
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif quantization == "8bit":
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_8bit=True,
            )
        else:
            kwargs["dtype"] = torch.float16

    tokenizer = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(name, **kwargs)

    if device.type == "cpu":
        model.to(device)

    model.eval()
    print(f"Model loaded on {device} with quantization: {quantization or 'none'}, serving as: {model_name}")


def generate_reply(messages: list[dict], max_tokens: int, temperature: float) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        prompt = "\n".join(
            f"User: {m['content']}" if m["role"] == "user" else f"Assistant: {m['content']}"
            for m in messages
        )
        prompt += "\nAssistant:"

    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    do_sample = temperature > 0
    gen_kwargs = dict(
        max_new_tokens=max_tokens,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=do_sample,
        use_cache=True,
    )
    if do_sample:
        gen_kwargs["temperature"] = temperature

    with torch.no_grad():
        output_ids = model.generate(**inputs, **gen_kwargs)

    new_tokens = output_ids[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [{"id": model_name, "object": "model"}],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    loop = asyncio.get_event_loop()
    temperature = req.temperature if req.temperature is not None else 0.0
    reply = await loop.run_in_executor(
        executor, generate_reply, messages, req.max_completion_tokens or 512, temperature
    )

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": -1,
            "completion_tokens": -1,
            "total_tokens": -1,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="OpenAI-compatible API server for HuggingFace models")
    parser.add_argument("model_name", type=str, help="Model path or HF hub ID")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--quant", type=str, choices=["4bit", "8bit"])
    parser.add_argument("--model-alias", type=str, default=None, help="Model alias to expose via API (default: model_name)")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    load_model(args.model_name, args.device, args.quant, alias=args.model_alias)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

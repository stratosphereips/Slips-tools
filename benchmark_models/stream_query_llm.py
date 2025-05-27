import openai
import time
import argparse
import os

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

def stream_chat_with_usage(prompt, base_url,model,stats_only):
    client = openai.OpenAI(
        api_key = os.getenv("OPENAI_API_KEY"),
        base_url = base_url
    )

    messages = [{"role": "user", "content": prompt}]
    #model = "gpt-4"  # Change this if your local model uses a different name

    if not stats_only:
        print("AI:", end=" ", flush=True)
    full_reply = ""
    usage_info = None

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True}
    )

    start_time = time.time()
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            part = chunk.choices[0].delta.content
            if not stats_only:
                print(part, end="", flush=True)
            full_reply += part
        if hasattr(chunk, "usage") and chunk.usage:
            usage_info = chunk.usage

    end_time = time.time()
    duration = end_time - start_time

    print("\n\n🧠 Stats:")
    if usage_info:
        prompt_tokens = usage_info.prompt_tokens
        completion_tokens = usage_info.completion_tokens
        total_tokens = usage_info.total_tokens
        tps = completion_tokens / duration if duration > 0 else 0

        print(f"  Prompt tokens:     {prompt_tokens}")
        print(f"  Completion tokens: {completion_tokens}")
        print(f"  Total tokens:      {total_tokens}")
        print(f"  Time taken:        {duration:.2f} sec")
        print(f"  Tokens per second: {tps:.2f} TPS")
    else:
        print("  Usage information not available.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream chat completions with usage metrics.")
    parser.add_argument("--base_url", default="http://10.147.20.102:11434/v1", help="Base URL of the OpenAI-compatible API")
    parser.add_argument("--prompt", required=True, help="Prompt to send to the model")
    parser.add_argument("--model", default="qwen2.5:3b", help="the model to use")
    parser.add_argument("--stats_only",action="store_true", help="Print only the stats, no prompt nor completion")

    args = parser.parse_args()

    stream_chat_with_usage(args.prompt, args.base_url,args.model, args.stats_only)


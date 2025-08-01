"""
A script for benchmarking LLM performance by streaming chat completions and measuring usage metrics.
This script supports both direct prompts and prompts loaded from files, and provides detailed
token usage and timing statistics.
"""

import openai
import time
import argparse
import os

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


def load_prompt(prompt_arg):
    """
    Loads the prompt from a file if the argument is a valid file path,
    otherwise returns the argument as a raw prompt string.
    
    Args:
        prompt_arg (str): Either a file path to a prompt file or a raw prompt string
        
    Returns:
        str: The prompt text to be sent to the model
    """
    if os.path.isfile(prompt_arg):
        with open(prompt_arg, 'r', encoding='utf-8') as f:
            return f.read()
    return prompt_arg

def stream_chat_with_usage(prompt, base_url, model, stats_only):
    """
    Streams a chat completion from an LLM and collects usage statistics.
    
    Args:
        prompt (str): The prompt to send to the model
        base_url (str): The base URL for the OpenAI-compatible API
        model (str): The name of the model to use
        stats_only (bool): If True, only print statistics, not the prompt or completion
    """
    # Initialize OpenAI client with custom base URL and extended timeout
    client = openai.OpenAI(
        api_key = os.getenv("OPENAI_API_KEY"),
        base_url=base_url,
        timeout=1200000  # 20 minutes timeout
    )

    # Prepare the message for the chat completion
    messages = [{"role": "user", "content": prompt}]
    if not stats_only:
        print("AI:", end=" ", flush=True)
    full_reply = ""
    usage_info = None

    # Create streaming chat completion request
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True}
    )

    # Process the streaming response
    start_time = time.time()
    for chunk in response:
        # Handle content chunks
        if chunk.choices and chunk.choices[0].delta.content:
            part = chunk.choices[0].delta.content
            if not stats_only:
                print(part, end="", flush=True)
            full_reply += part
        # Capture usage information when available
        if hasattr(chunk, "usage") and chunk.usage:
            usage_info = chunk.usage

    end_time = time.time()
    duration = end_time - start_time

    # Print detailed statistics
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
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Stream chat completions with usage metrics.")
    parser.add_argument("--base_url", default="http://10.147.20.102:11434/v1", 
                       help="Base URL of the OpenAI-compatible API")
    parser.add_argument("--prompt", required=True, 
                       help="Prompt to send to the model or path to a text file")
    parser.add_argument("--model", default="qwen2.5:3b", 
                       help="The model to use")
    parser.add_argument("--stats_only", action="store_true", 
                       help="Print only the stats, no prompt nor completion")

    args = parser.parse_args()

    # Load prompt and start streaming chat
    prompt_text = load_prompt(args.prompt)
    stream_chat_with_usage(prompt_text, args.base_url, args.model, args.stats_only)


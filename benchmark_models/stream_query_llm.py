import openai
import time
import argparse
import os

from dotenv import load_dotenv
# Load environment variables from a .env file if present
load_dotenv()

def stream_chat_with_usage(prompt, base_url, model, stats_only):
    # Create an OpenAI client instance using the API key and base URL from environment/config
    client = openai.OpenAI(
        api_key = os.getenv("OPENAI_API_KEY"),
        base_url = base_url
    )

    # Construct the message payload for the chat completion API
    messages = [{"role": "user", "content": prompt}]
    # Optionally, you can change the model name here if needed

    # If not in stats-only mode, print the AI label before streaming the response
    if not stats_only:
        print("AI:", end=" ", flush=True)
    full_reply = ""  # Accumulates the full AI response as it streams in
    usage_info = None  # Will hold token usage statistics from the API

    # Send a streaming chat completion request, asking for usage info in the stream
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True}
    )

    start_time = time.time()  # Record the start time to measure response duration
    for chunk in response:
        # Each chunk may contain a part of the response or usage info
        if chunk.choices and chunk.choices[0].delta.content:
            # Extract the content from the chunk
            part = chunk.choices[0].delta.content
            # Print the content immediately if not in stats-only mode
            if not stats_only:
                print(part, end="", flush=True)
            # Append the content to the full reply
            full_reply += part
        # If this chunk contains usage statistics, store them for later reporting
        if hasattr(chunk, "usage") and chunk.usage:
            usage_info = chunk.usage

    end_time = time.time()  # Record the end time after streaming completes
    duration = end_time - start_time  # Calculate total time taken for the response

    print("\n\n🧠 Stats:")  # Print a header for the statistics section
    if usage_info:
        # Extract token usage statistics from the usage_info object
        prompt_tokens = usage_info.prompt_tokens
        completion_tokens = usage_info.completion_tokens
        total_tokens = usage_info.total_tokens
        # Calculate tokens per second (TPS) for the completion
        tps = completion_tokens / duration if duration > 0 else 0

        # Print detailed usage statistics for analysis
        print(f"  Prompt tokens:     {prompt_tokens}")
        print(f"  Completion tokens: {completion_tokens}")
        print(f"  Total tokens:      {total_tokens}")
        print(f"  Time taken:        {duration:.2f} sec")
        print(f"  Tokens per second: {tps:.2f} TPS")
    else:
        # If usage info was not returned, notify the user
        print("  Usage information not available.")

if __name__ == "__main__":
    # Set up command-line argument parsing for flexible usage
    parser = argparse.ArgumentParser(description="Stream chat completions with usage metrics.")
    parser.add_argument("--base_url", default="http://10.147.20.102:11434/v1", help="Base URL of the OpenAI-compatible API")
    parser.add_argument("--prompt", required=True, help="Prompt to send to the model")
    parser.add_argument("--model", default="qwen2.5:3b", help="the model to use")
    parser.add_argument("--stats_only", action="store_true", help="Print only the stats, no prompt nor completion")

    args = parser.parse_args()

    # Call the main streaming function with parsed arguments from the CLI
    stream_chat_with_usage(args.prompt, args.base_url, args.model, args.stats_only)


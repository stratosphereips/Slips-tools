## Tool for querying other LLMs

### LLM Query and Benchmarking Script
**Location:** `../benchmark_models/stream_query_llm_long_prompt.py`

A Python tool for benchmarking LLM performance by streaming chat completions and measuring detailed usage metrics.

#### Features
- Streams responses from OpenAI-compatible APIs
- Measures token usage, timing, and tokens-per-second
- Supports loading prompts from files or direct strings
- 20-minute timeout for long operations
- Stats-only mode for quiet benchmarking

#### Usage
```bash
# Basic usage with direct prompt
python3 ../benchmark_models/stream_query_llm_long_prompt.py --prompt "Your question here"

# Load prompt from file
python3 ../benchmark_models/stream_query_llm_long_prompt.py --prompt prompt.txt

# Test with OpenAI GPT models
python3 ../benchmark_models/stream_query_llm_long_prompt.py --prompt "What is 2+2?" --model gpt-4o-mini --base_url https://api.openai.com/v1

# Custom Ollama endpoint
python3 ../benchmark_models/stream_query_llm_long_prompt.py --prompt "test" --model llama2 --base_url http://10.147.20.102:11434/v1

# Stats only (no response text)
python3 ../benchmark_models/stream_query_llm_long_prompt.py --prompt "test" --stats_only
```

#### Requirements
- Python packages: `openai`, `python-dotenv`
- Environment variable: `OPENAI_API_KEY`
- Default endpoint: `http://10.147.20.102:11434/v1` (Ollama)
- Default model: `qwen2.5:3b`

#### Tested Performance
- **GPT-4o-mini**: 21.65 TPS, 0.37s response time for simple queries


- there is docker where zeek is located. Check first is the docker is running. If it you can test a signature using docker-compose exec -T zeek-validator /signatures/validate_zeek_sig.sh /signatures/test_signature.sig
- check the README.md for more info about the project
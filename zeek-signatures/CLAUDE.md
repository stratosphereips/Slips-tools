# Zeek Signature Toolkit

LLM-powered tools for generating, varying, and validating Zeek network security signatures.

## Core Tools

### Signature Generation
- **`generate_zeek_signature_dataset.py`** - Generate synthetic Zeek signature datasets for LLM training
- **`vary_zeek_signature.py`** - Create broader/stricter variations of existing signatures
- **`download_webpage.py`** - Web content retrieval utility for signature research

### Validation and Testing
- **`validate_zeek_sig.sh`** - Signature syntax and traffic validation script
- **Docker environment** - Containerized Zeek validation setup

## Key Commands

### Docker-based Validation
```bash
# Check if Docker is running
docker ps

# Build and start the validation environment
docker-compose up -d

# Test signature syntax only
docker-compose exec -T zeek-validator /signatures/validate_zeek_sig.sh /signatures/test_signature.sig

# Test signature against traffic
docker-compose exec -T zeek-validator /signatures/validate_zeek_sig.sh /signatures/test_signature.sig /test_data/sample.pcap

# Interactive shell for debugging
docker-compose exec zeek-validator bash
```

### Signature Generation and Variation
```bash
# Generate signature dataset
python3 generate_zeek_signature_dataset.py

# Create signature variations
python3 vary_zeek_signature.py --input signatures.json --output varied_signatures.json

# Download web content for analysis
python3 download_webpage.py --url https://example.com --output content.txt
```

## Documentation

- **[Dataset Generator](generate_zeek_signature_dataset_overview.md)** - LLM-based signature dataset generation
- **[Signature Variation](vary_zeek_signature_overview.md)** - Pattern modification and variation strategies  
- **[Validation Workflow](zeek_validation_workflow_overview.md)** - Testing and validation process
- **[Zeek Signature Framework](zeek_signature_framework.md)** - Comprehensive guide to Zeek signature syntax

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

## Development Notes

- Check if Docker is running before testing signatures
- Test signatures using: `docker-compose exec -T zeek-validator /signatures/validate_zeek_sig.sh /signatures/test_signature.sig`
- Check the README.md for more project information
- Don't mention CLAUDE in commit messages

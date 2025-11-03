# Zeek Signature Dataset Generator

## Overview

`generate_zeek_signature_dataset.py` is a Python script that generates synthetic datasets of Zeek network security signatures for machine learning model fine-tuning. It creates diverse signature generation tasks using large language models (LLMs) to produce training data in the Alpaca format.

## Purpose

The script addresses the need for high-quality training data for LLMs that can generate Zeek signatures for network security detection. It creates varied examples across different threat types, protocols, and complexity levels to ensure comprehensive training coverage.

## Key Features

### Dataset Generation
- Generates training examples in Alpaca format (`instruction`, `input`, `output`)
- Creates diverse signature scenarios with randomized parameters
- Supports configurable output counts (default: 10 examples)
- Validates generated signatures for proper Zeek syntax

### Threat Coverage
- **20+ threat types**: malware C&C, SQL injection, XSS, ransomware, etc.
- **11 protocols**: HTTP/HTTPS, DNS, SSH, FTP, SMTP, TCP, UDP, TLS, SMB, ICMP
- **6 complexity levels**: simple patterns to stateful analysis
- **8 network contexts**: enterprise, web server, IoT, cloud infrastructure

### LLM Integration
- OpenAI-compatible API support (GPT models, Ollama endpoints)
- Streaming responses with 20-minute timeout
- Comprehensive error handling for API failures
- Rate limiting and retry logic

### Validation & Quality Control
- Syntax validation for Zeek signature format
- Detection of YARA rule contamination
- Markdown artifact removal and cleanup
- Brace balancing and field validation
- Up to 3x retry attempts for failed generations

## Usage Examples

```bash
# Generate 100 signatures with default GPT-4o-mini
python3 generate_zeek_signature_dataset.py --count 100 --output signatures_dataset.json

# Use local Ollama endpoint
python3 generate_zeek_signature_dataset.py --model qwen2.5:3b --base_url http://localhost:11434/v1

# Include reference documentation for better quality
python3 generate_zeek_signature_dataset.py --reference-doc zeek_examples.txt --count 50

# Debug mode with signature printing
python3 generate_zeek_signature_dataset.py --count 10 --print-signatures
```

## Architecture

### Core Classes

- **`ZeekSignaturePromptGenerator`**: Creates varied prompts with threat scenarios, protocol contexts, and detection requirements
- **`ZeekDatasetGenerator`**: Manages LLM interaction, signature validation, and dataset compilation

### Validation Pipeline

1. **Preprocessing**: Removes markdown code blocks and formatting artifacts
2. **Structure checking**: Validates signature keyword, brace balance, naming format
3. **Field validation**: Ensures presence of valid Zeek signature components
4. **Format compliance**: Detects YARA rule contamination and improper syntax

## Output Format

Generates JSON files with Alpaca-format training examples:

```json
{
  "instruction": "Create a Zeek signature to detect malware command and control communication",
  "input": "Protocol: HTTP\nNetwork Context: enterprise network environment\nDetection Method: HTTP header and body analysis\nAdditional Requirement: include proper signature metadata and event description",
  "output": "signature malware-c2-http {\n    ip-proto == tcp\n    dst-port == 80\n    payload /POST.*\\/update.*malware/\n    event \"Malware C2 communication detected\"\n}"
}
```

## Dependencies

- **Python packages**: `openai`, `python-dotenv`, `pathlib`
- **Environment**: `OPENAI_API_KEY` for commercial APIs
- **Optional**: Reference documentation files (max 50KB)

## Quality Features

- **Error resilience**: Handles API failures, rate limits, authentication errors
- **Progress tracking**: Real-time generation status and validation feedback  
- **File management**: Automatic directory creation and permission checking
- **Memory efficiency**: Streaming responses and size limits for reference docs
# Zeek Signature Variation Generator

## Overview

`vary_zeek_signature.py` is a Python script that takes an existing Zeek network security signature as input and generates multiple variations with modified regex patterns. It uses large language models (LLMs) to create diverse signature variations while maintaining the original detection intent, enabling broader or more precise threat detection coverage.

## Purpose

The script addresses the need to create multiple variations of effective Zeek signatures to:
- **Expand detection coverage**: Generate broader patterns that catch more evasion attempts
- **Improve precision**: Create stricter patterns that reduce false positives
- **Build signature families**: Develop comprehensive detection rule sets from proven signatures
- **Test robustness**: Evaluate signature effectiveness across different matching strategies

## Key Features

### Signature Parsing & Analysis
- **Complete syntax parsing**: Extracts signature components (name, body, patterns, metadata)
- **Modifiable pattern detection**: Identifies regex patterns in `payload`, `http-request`, `http-reply` fields
- **Syntax validation**: Validates Zeek signature format with brace balancing and component checking
- **Error handling**: Comprehensive parsing error detection and reporting

### Variation Strategies

#### Broader Matching Patterns
- **Character variations**: `/root/` → `/r.{0,2}t/` (allows character substitutions)
- **Flexible spacing**: `/malware/` → `/.*mal.*ware.*/` (allows separating characters)
- **Wildcard expansion**: `/GET /` → `/GET.*/` (less specific path matching)
- **Case insensitivity**: `/admin/` → `/[aA][dD][mM][iI][nN]/` (case variations)

#### Stricter Matching Patterns  
- **Word boundaries**: `/root/` → `/\broot\b/` (exact word matching)
- **Anchored patterns**: `/GET.*/` → `/^GET \/specific\/path/` (exact path matching)
- **End constraints**: `/admin/` → `/admin(?=\s|$)/` (require word end)
- **Precise extensions**: `/.exe/` → `/\.exe$/` (exact file extension at end)

#### Mixed Strategy
- Combines both broader and stricter approaches
- Generates approximately half broader, half stricter patterns
- Provides comprehensive coverage for different detection scenarios

### LLM Integration
- **OpenAI-compatible APIs**: Supports GPT models and Ollama endpoints
- **Streaming responses**: Handles large variations efficiently
- **20-minute timeout**: Accommodates complex pattern generation
- **Robust error handling**: Manages authentication, rate limits, and connection issues

## Usage Examples

```bash
# Generate broader variations from file
python3 vary_zeek_signature.py --input malware_sig.sig --count 5 --strategy broader

# Generate stricter variations from direct input
python3 vary_zeek_signature.py --signature "signature test { payload /root/; event 'test'; }" --count 3 --strategy stricter

# Mixed variations with custom model
python3 vary_zeek_signature.py --input signature.sig --count 10 --strategy mixed --model gpt-4o

# Save to JSON file with metadata
python3 vary_zeek_signature.py --input sig.sig --count 5 --output variations.json --format json

# Save as raw signature files
python3 vary_zeek_signature.py --input sig.sig --count 5 --output variations.sig --format sig

# Use local Ollama endpoint
python3 vary_zeek_signature.py --input sig.sig --base_url http://localhost:11434/v1 --model qwen2.5:3b
```

## Architecture

### Core Classes

- **`ZeekSignatureParser`**: Parses Zeek signatures and extracts modifiable components using regex patterns
- **`SignatureVariationGenerator`**: Manages LLM interaction and variation processing with comprehensive validation

### Processing Pipeline

1. **Input validation**: Load and validate input signature syntax
2. **Component extraction**: Parse signature structure and identify modifiable regex patterns  
3. **Prompt generation**: Create strategy-specific prompts with examples and constraints
4. **LLM generation**: Query LLM for signature variations with streaming response
5. **Output processing**: Split and validate individual signatures from LLM response
6. **Metadata creation**: Build variation objects with parsed components and strategy info

## Input/Output Formats

### Input Options
- **File input**: Load signature from `.sig` file (`--input signature.sig`)
- **Direct input**: Provide signature string directly (`--signature "signature ..."`)

### Output Formats

#### JSON Format (default)
```json
[
  {
    "signature": "signature malware-c2-v1 {\n    ip-proto == tcp\n    dst-port == 80\n    payload /.*mal.*ware.*/\n    event \"Broader malware detection\"\n}",
    "name": "malware-c2-v1",
    "strategy": "broader",
    "index": 1,
    "modifiable_patterns": [
      {
        "type": "payload",
        "pattern": ".*mal.*ware.*",
        "flags": ""
      }
    ],
    "valid": true
  }
]
```

#### Raw Signature Format (.sig)
```
signature malware-c2-v1 {
    ip-proto == tcp
    dst-port == 80
    payload /.*mal.*ware.*/
    event "Broader malware detection"
}

signature malware-c2-v2 {
    ip-proto == tcp
    dst-port == 80
    payload /\bmalware\b/
    event "Stricter malware detection"
}
```

## Component Recognition

### Supported Zeek Fields
- **Network layer**: `ip-proto`, `src-ip`, `dst-ip`, `src-port`, `dst-port`
- **Content matching**: `payload`, `http-request`, `http-reply` (with regex patterns)
- **Connection state**: `tcp-state`
- **Event metadata**: `event` (description string)

### Regex Pattern Processing
- Extracts patterns with format `/pattern/flags`
- Identifies modifiable regex components for variation
- Preserves non-regex signature elements unchanged
- Maintains proper Zeek syntax throughout variations

## Quality Assurance

- **Syntax validation**: Real-time validation of generated variations
- **Parse verification**: Confirms signature components parse correctly  
- **Strategy compliance**: Ensures variations follow requested broader/stricter approach
- **Unique naming**: Automatically generates unique variation names with suffixes
- **Progress tracking**: Reports successful vs. failed variation generation
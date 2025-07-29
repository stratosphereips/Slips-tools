# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The `alert_summary` directory contains the **Slips Evidence Log DAG Generator**, a Python tool that parses Slips network security evidence logs and generates textual DAG (Directed Acyclic Graph) visualizations showing chronological security events for IP addresses.

## Core Architecture

### Main Components

- **`slips_dag_generator.py`** - Main Python script with comprehensive log parsing and DAG generation
- **`sample_logs/`** - Test data directory containing various Slips evidence log formats
- **`examples/`** - Output examples showing different DAG formats and use cases
- **`tests/`** - Test directory (currently empty)

### Key Classes

- **`EvidenceEvent`** - Dataclass representing individual security events with timestamp, IP, threat level, and confidence
- **`Alert`** - Dataclass representing Slips alerts/analyses with associated evidence events and timewindow metadata
- **`SlipsLogParser`** - Core parser class handling multiple log formats, evidence extraction, and alert parsing
- **`DAGGenerator`** - Main DAG generation class supporting both IP-based and analysis-based output modes

## Usage Commands

### Basic Analysis

#### IP-based Analysis (Default Mode)
```bash
# Single IP analysis (default compact format)
python3 slips_dag_generator.py sample_logs/test_data.log 192.168.1.113

# All IPs in log file
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips

# Output to file
python3 slips_dag_generator.py sample_logs/test_data.log 192.168.1.113 --output results.txt
```

#### Analysis-based Mode (DAG per Alert)
```bash
# Generate separate DAG for each alert/analysis
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --compact

# Per-analysis for specific IP
python3 slips_dag_generator.py sample_logs/slips.log 192.168.1.113 --per-analysis --minimal

# All analyses with threat level information
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --include-threat-level --minimal
```

### Output Format Options
```bash
# Compact format (default) - single line per event
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --compact

# Minimal format - bullet-point summaries
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --minimal

# Pattern analysis - attack phase breakdown
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --pattern

# Full verbose format - original detailed output
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --full
```

### Filtering and Analysis
```bash
# Filter by threat level (IP-based mode)
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --min-threat high

# Limit number of events (IP-based mode)
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --max-events 20

# Include threat level information (works with both modes)
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --include-threat-level

# Export as JSON for further processing (IP-based mode)
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --json

# Include summary statistics
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --summary
```

### Common Workflows

#### IP-based Workflows
```bash
# Incident response - quick overview of all threats
python3 slips_dag_generator.py sample_logs/slips-evidence.log --all-ips --minimal --min-threat medium

# Forensic analysis - detailed single IP investigation
python3 slips_dag_generator.py sample_logs/slips.log 192.168.1.113 --full --summary

# Report generation - structured export
python3 slips_dag_generator.py sample_logs/slips.log --all-ips --json --output network_threats.json
```

#### Analysis-based Workflows
```bash
# Alert investigation - analyze each detection separately
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --minimal --include-threat-level

# Incident timeline - chronological analysis breakdown
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --pattern

# Threat hunting - compare evidence patterns across alerts
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --compact --summary

# Alert-focused reporting
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --output alert_analysis.txt
```

## Log Format Support

The parser handles multiple Slips log formats:

### Standard Format
```
2023/10/14 12:19:32.101019 [evidence.py:1089] [INFO] [IP 192.168.1.113] 
given the following evidence:
- Detected a horizontal port scan to port 80/TCP. 5 unique dst IPs...
```

### Grouped Alerts Format (Supports Per-Analysis Mode)
```
2024/04/05 16:53:07.882348 [evidence.py:1089] [INFO] [IP 10.0.2.15] 
detected as malicious in timewindow 12
given the following evidence:
	- Detected Non-SSL connection to 185.29.135.234:443...
```

**Note**: Per-analysis mode (`--per-analysis`) is only supported with the grouped alerts format. Use IP-based mode for standard format logs.

## Evidence Types Detected

1. **Port Scans** - Horizontal and vertical scanning activities
2. **C&C Channels** - Command and control server connections
3. **Blacklisted IPs** - Known malicious IP connections
4. **Suspicious Connections** - Non-HTTP/SSL connections to unexpected ports
5. **Private IP Connections** - Internal network communications
6. **DNS Issues** - Connections without DNS resolution
7. **Unencrypted Traffic** - HTTP traffic that should be encrypted
8. **Malicious Detections** - IPs flagged as malicious by Slips

## Sample Data

### Test Files
- **`test_data.log`** - Controlled test scenarios for development
- **`slips-evidence.log`** - Clean evidence-only format

### Malware Capture Logs
- **`slips.log`**, **`slips-1.log`**, **`slips-5.log`** - Real malware behavior patterns
- Contains C&C channels, port scans, blacklisted IPs

### Normal Network Logs
- **`slips-normal.log`**, **`slips-normal-2.log`**, **`slips-normal-3.log`** - Benign network activity
- Useful for baseline testing and false positive analysis

## Development Notes

### Dependencies
- Python 3.6+ (uses dataclasses, type hints)
- Standard library only - no external dependencies required
- Compatible with argparse, re, json, datetime modules

### Testing
```bash
# Quick functionality test (IP-based mode)
python3 slips_dag_generator.py sample_logs/test_data.log 192.168.1.113

# Test all output formats (IP-based mode)
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --compact
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --minimal
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --pattern
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --full

# Test per-analysis mode (requires grouped alerts format)
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --compact
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --minimal --include-threat-level
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --pattern
```

### Performance
- Efficient parsing of large log files
- Memory usage scales with events per IP (IP-based) or events per alert (analysis-based)
- Suitable for real-time incident analysis

## Analysis Modes

### IP-based Mode (Default)
- **Use case**: Traditional chronological analysis of all activity for specific IP addresses
- **Output**: Single DAG per IP showing all evidence events in chronological order
- **Best for**: Timeline reconstruction, comprehensive IP behavior analysis
- **Log format support**: Both standard and grouped alerts formats

### Analysis-based Mode (`--per-analysis`)
- **Use case**: Focus on individual Slips alert detections and their specific evidence
- **Output**: Separate DAG for each alert/analysis with associated evidence grouped by timewindow
- **Best for**: Alert investigation, incident response, evidence validation
- **Log format support**: Grouped alerts format only
- **Key benefits**:
  - Preserves alert context and evidence grouping
  - Individual risk assessment per analysis
  - Clear separation between different detection events
  - Easier correlation of evidence to specific alerts

## Shell Script Integration

### LLM Analysis Wrapper
**Location:** `analyze_slips_with_llm.sh`

Enhanced shell script supporting both analysis modes with LLM integration:

```bash
# IP-based analysis with LLM
./analyze_slips_with_llm.sh sample_logs/slips.log 192.168.1.113 --detailed

# Per-analysis mode with LLM
./analyze_slips_with_llm.sh sample_logs/slips.log --per-analysis --format minimal

# DAG-only output (no LLM analysis)
./analyze_slips_with_llm.sh sample_logs/slips.log --per-analysis --dag-only --include-threat-level
```

### Script Features
- **Automatic format detection**: Handles both log formats appropriately
- **LLM integration**: Feeds DAG output to language models for security analysis
- **Flexible options**: Supports all DAG generation parameters
- **Output management**: Structured reporting with both DAG and LLM analysis

## Integration

The tool integrates with:
- Security orchestration platforms (SOAR)
- Incident response workflows
- Threat hunting pipelines
- SIEM systems via JSON export

## Security Context

This is a defensive security tool for analyzing network security evidence. All sample logs are sanitized research data from controlled environments. The tool helps security analysts understand attack patterns and timeline reconstruction from Slips network security analysis output.

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

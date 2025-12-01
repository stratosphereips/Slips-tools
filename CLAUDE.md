# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Slips-tools is a collection of tools and scripts for testing and evaluating Slips (network security analysis). The repository contains five main components:

1. **Alert Summary Tools** (`alert_summary/`) - Slips Evidence Log DAG Generator with dual analysis modes (IP-based and per-analysis)
2. **LLM Unit Testing** (`llm-unittest/`) - Promptfoo-based test suite for evaluating small language models on security-related tasks
3. **Model Benchmarking** (`benchmark_models/`) - Performance benchmarking for Ollama-served models  
4. **Data Visualization** (`multi_line_chart_plotter/`) - CSV plotting utility for performance metrics
5. **System Monitoring** (`rpi_temperature_logger/`) - Raspberry Pi temperature logging

## Key Commands

### Alert Summary Tools
```bash
# IP-based analysis (traditional mode)
cd alert_summary/
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --minimal --include-threat-level

# Per-analysis mode (alert-focused)
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --compact

# LLM-enhanced analysis
./analyze_slips_with_llm.sh sample_logs/slips.log --per-analysis --format minimal

# Dataset generation - Summarization workflow
./sample_dataset.sh 100 my_dataset --seed 42
./generate_dag_analysis.sh datasets/my_dataset.jsonl
./generate_llm_analysis.sh datasets/my_dataset.jsonl --model gpt-4o-mini --group-events --behavior-analysis
python3 correlate_incidents.py datasets/my_dataset.*.json --jsonl datasets/my_dataset.jsonl -o final_dataset.json

# Dataset generation - Cause & Risk workflow
./generate_cause_risk_analysis.sh datasets/my_dataset.jsonl --model gpt-4o-mini --group-events
python3 correlate_risks.py datasets/my_dataset.*.json --jsonl datasets/my_dataset.jsonl -o final_dataset_risk.json
```

### LLM Unit Testing
```bash
# Run all test cases with Ollama backend
cd llm-unittest/
./run_tests.sh

# Run individual test case
promptfoo eval -c 01_test_action_json_parsing.yaml --max-concurrency 3 --no-cache --providers file://providers/ex_provider.yaml

# View results
promptfoo view
```

### Model Benchmarking
```bash
# Benchmark all available Ollama models
cd benchmark_models/
./benchmark_ollama_models.sh

# Test single OpenAI-compatible endpoint
./test_openai.sh
```

### Data Visualization
```bash
# Install dependencies
cd multi_line_chart_plotter/
pip install -r requirements.txt

# Generate multi-line plot
./plotter.py file1.csv file2.csv "Title" "X Label" "Y Label" output.png
```

### Temperature Monitoring
```bash
# Log Raspberry Pi temperature (requires RPi)
cd rpi_temperature_logger/
python3 rpi_temperature_logger.py
```

## Architecture

### LLM Testing Framework
- **Test Cases**: YAML files defining prompts and expected outputs for various security tasks (JSON parsing, Zeek analysis, tool use)
- **Providers**: Configuration for different model endpoints (Ollama, OpenAI-compatible APIs)
- **Evaluation**: Uses Promptfoo framework for systematic model evaluation

### Benchmarking System
- **stream_query_llm.py**: Core Python script for querying models and measuring performance metrics
- **benchmark_ollama_models.sh**: Orchestrates benchmarking across multiple models, collecting disk usage, RAM usage, and tokens-per-second
- **Results**: Outputs structured CSV data for analysis

### Provider Configuration
Models are configured in `llm-unittest/providers/` with endpoints typically pointing to:
- Ollama servers (e.g., `http://10.147.20.101:11434/v1`)
- Custom model endpoints for specialized models like BitNet

## Test Categories

The LLM unit tests focus on security-relevant capabilities:
- **Action JSON**: Parsing and understanding structured security actions
- **Zeek Analysis**: Network traffic log analysis and signature generation  
- **Tool Use**: Integration with security tools and workflows
- **Summarization**: Converting technical data into actionable insights

## Development Notes

- Promptfoo requires `npm install -g promptfoo`
- Python dependencies are minimal (openai, pandas, matplotlib)
- Shell scripts expect `jq` and `curl` for JSON processing
- Default configurations point to specific IP addresses that may need updating for different environments

## Conda Environment Setup

- Always use conda environment for running projects
- Activation command: 
  - `source $HOME/miniconda3/etc/profile.d/conda.sh && conda activate agents`
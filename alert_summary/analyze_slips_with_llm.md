# Slips DAG Analysis with LLM Integration

A bash script that combines Slips evidence log analysis with AI-powered security assessment.

## Overview

`analyze_slips_with_llm.sh` executes the Slips DAG generator and feeds the output to a large language model for intelligent security analysis. The script provides automated threat assessment, attack pattern identification, and actionable security recommendations.

## Features

- **Automated Analysis**: Combines DAG generation with LLM-powered security assessment
- **Multiple Output Formats**: Supports minimal, compact, pattern, and full analysis formats
- **Flexible Targeting**: Analyze all IPs or focus on specific addresses
- **Threat Filtering**: Filter by severity levels and limit event counts
- **Model Selection**: Works with various LLM models (OpenAI, Ollama, etc.)
- **Export Options**: Save both raw DAG output and LLM analysis to files

## Usage

### Basic Syntax
```bash
./analyze_slips_with_llm.sh <log_file> [ip_address] [options]
```

### Common Examples

```bash
# Quick analysis of all threats
./analyze_slips_with_llm.sh sample_logs/slips-evidence.log

# Detailed analysis of specific IP
./analyze_slips_with_llm.sh sample_logs/slips.log 192.168.1.113 --detailed

# Pattern analysis with custom model
./analyze_slips_with_llm.sh sample_logs/slips-5.log --format pattern --model qwen2.5:3b

# High-priority threats only, save to file
./analyze_slips_with_llm.sh sample_logs/slips.log --min-threat high --output analysis.txt

# DAG generation only (skip LLM analysis)
./analyze_slips_with_llm.sh sample_logs/test_data.log --dag-only
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format: minimal, compact, pattern, full | minimal |
| `--model MODEL` | LLM model to use | gpt-4o-mini |
| `--base-url URL` | LLM API base URL | https://api.openai.com/v1 |
| `--detailed` | Use full format with summary | - |
| `--all-ips` | Analyze all IPs (default if no IP specified) | - |
| `--max-events N` | Limit to N events per IP | - |
| `--min-threat LEVEL` | Filter by threat level: low, medium, high | - |
| `--output FILE` | Save analysis to file | - |
| `--dag-only` | Only run DAG generation, skip LLM | - |

## Analysis Output

The LLM provides structured security assessment with:

1. **Threat Severity**: Overall risk level (Critical/High/Medium/Low)
2. **Attack Patterns**: Key attack types and techniques identified
3. **Priority Actions**: Top 3 immediate actions for security team
4. **Key Findings**: Most concerning security events

## Requirements

- **Dependencies**: Python 3.6+, `openai`, `python-dotenv` packages
- **Environment**: `OPENAI_API_KEY` environment variable
- **Files**: `slips_dag_generator.py` and `../benchmark_models/stream_query_llm_long_prompt.py`

## Performance

- **Speed**: ~43 TPS with GPT-4o-mini for typical security analyses
- **Efficiency**: Handles large log files with memory usage scaling by IP events
- **Reliability**: Comprehensive error handling and validation

## Integration

Perfect for:
- **Incident Response**: Quick threat assessment and prioritization
- **Security Operations**: Automated analysis in SOC workflows  
- **Threat Hunting**: Pattern analysis across network logs
- **Forensic Analysis**: Detailed timeline reconstruction with AI insights

## Example Output

```
==================== SECURITY ANALYSIS REPORT ====================
### Assessment of Slips Network Security Evidence

1. **Threat Severity**: **Critical**
   - Multiple devices show sustained malicious activity

2. **Attack Patterns**:
   - **Command and Control (C&C) Communication**: Detected connections indicating compromise
   - **Port Scans**: Reconnaissance activities on ports 443, 80, and 22
   - **DNS Evasion Techniques**: Bypassing DNS-based security measures

3. **Priority Actions**:
   - **Isolate Compromised Hosts**: Remove affected IPs from network
   - **Analyze Traffic Logs**: Investigate C&C communications
   - **Update Security Protocols**: Enhance IDS and firewall rules

4. **Key Findings**:
   - **Sustained Malicious Activity**: Ongoing threat requiring immediate attention
   - **High-Risk Host Activity**: Coordinated attack patterns detected
   - **Port Scanning Behavior**: Vulnerability assessment activities

🧠 Stats:
  Prompt tokens:     322
  Completion tokens: 399
  Total tokens:      721
  Time taken:        9.26 sec
  Tokens per second: 43.07 TPS
====================================================================
```

## Security Context

This is a defensive security tool for analyzing network evidence logs. All sample data comes from controlled security research environments. The tool assists security analysts with threat assessment and incident response decision-making.
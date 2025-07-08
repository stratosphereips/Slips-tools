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
- **`SlipsLogParser`** - Core parser class handling multiple log formats and evidence extraction
- **`SlipsDAGGenerator`** - Main orchestrator class managing parsing, filtering, and output generation

## Usage Commands

### Basic Analysis
```bash
# Single IP analysis (default compact format)
python3 slips_dag_generator.py sample_logs/test_data.log 192.168.1.113

# All IPs in log file
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips

# Output to file
python3 slips_dag_generator.py sample_logs/test_data.log 192.168.1.113 --output results.txt
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
# Filter by threat level
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --min-threat high

# Limit number of events
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --max-events 20

# Export as JSON for further processing
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --json

# Include summary statistics
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --summary
```

### Common Workflows
```bash
# Incident response - quick overview of all threats
python3 slips_dag_generator.py sample_logs/slips-evidence.log --all-ips --minimal --min-threat medium

# Forensic analysis - detailed single IP investigation
python3 slips_dag_generator.py sample_logs/slips.log 192.168.1.113 --full --summary

# Threat hunting - pattern analysis across all IPs
python3 slips_dag_generator.py sample_logs/slips-5.log --all-ips --pattern

# Report generation - structured export
python3 slips_dag_generator.py sample_logs/slips.log --all-ips --json --output network_threats.json
```

## Log Format Support

The parser handles multiple Slips log formats:

### Standard Format
```
2023/10/14 12:19:32.101019 [evidence.py:1089] [INFO] [IP 192.168.1.113] 
given the following evidence:
- Detected a horizontal port scan to port 80/TCP. 5 unique dst IPs...
```

### Grouped Alerts Format
```
2024/04/05 16:53:07.882348 [evidence.py:1089] [INFO] [IP 10.0.2.15] 
detected as malicious in timewindow 12
given the following evidence:
	- Detected Non-SSL connection to 185.29.135.234:443...
```

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
# Quick functionality test
python3 slips_dag_generator.py sample_logs/test_data.log 192.168.1.113

# Test all output formats
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --compact
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --minimal
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --pattern
python3 slips_dag_generator.py sample_logs/test_data.log --all-ips --full
```

### Performance
- Efficient parsing of large log files
- Memory usage scales with events per IP, not total log size
- Suitable for real-time incident analysis

## Integration

The tool integrates with:
- Security orchestration platforms (SOAR)
- Incident response workflows
- Threat hunting pipelines
- SIEM systems via JSON export

## Security Context

This is a defensive security tool for analyzing network security evidence. All sample logs are sanitized research data from controlled environments. The tool helps security analysts understand attack patterns and timeline reconstruction from Slips network security analysis output.
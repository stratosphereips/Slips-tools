# Sample Logs Directory

This directory contains various Slips evidence log files retained as sample data. These logs represent different types of network security captures and processing methods.

Most sample logs are stored as gzip-compressed `.log.gz` files to save space. Decompress a file before using tools that expect a plain `.log` input.

## File Types and Origins

### Malware Capture Logs
These logs contain evidence from network traffic captures where malware was actively present and detected:

- **`slips.log.gz`** - Complete malware capture log with all Slips evidence detection
- **`slips-1.log.gz`** - Malware capture log from a different session/dataset
- **`slips-5.log.gz`** - Malware capture log from another session/dataset

**Characteristics:**
- Contains evidence of malicious activities (C&C channels, port scans, blacklisted IPs)
- Higher density of high-severity threats
- Represents real-world malware behavior patterns
- Useful as reference data for malware-capture behavior

### Normal Network Capture Logs
These logs contain evidence from normal network operations without active malware:

- **`slips-normal.log.gz`** - Normal network traffic capture
- **`slips-normal-2.log.gz`** - Additional normal network capture
- **`slips-normal-3.log.gz`** - Third normal network capture

**Characteristics:**
- Lower threat levels (mostly INFO/LOW/MEDIUM)
- Contains typical network activities (SSL connections, DNS queries, HTTP traffic)
- May include some false positives or benign suspicious activities
- Useful for baseline testing and false positive analysis

### Processed Evidence Logs
These logs are derived from other log files with specific processing applied:

- **`slips-evidence.log.gz`** - Similar to `slips.log.gz` but with all evidence entries filtered using grep
- **`test_data.log.gz`** - Synthetic or curated test data for development purposes

**Characteristics:**
- `slips-evidence.log.gz`: Clean evidence-only format, easier to parse after decompression
- `test_data.log.gz`: Controlled dataset for testing specific scenarios after decompression

## Log Format Variations

These compressed files contain multiple historical Slips log formats:

### Standard Format
```
2023/10/14 12:19:32.101019 [evidence.py:1089] [INFO] [IP 192.168.1.113] 
given the following evidence:
- Detected a horizontal port scan to port 80/TCP. 5 unique dst IPs...
```

### Grouped Alerts Format (Tab-prefixed)
```
2024/04/05 16:53:07.882348 [evidence.py:1089] [INFO] [IP 10.0.2.15] 
detected as malicious in timewindow 12
given the following evidence:
	- Detected Non-SSL connection to 185.29.135.234:443...
```

## Usage Notes

These compressed plain-text logs are retained as sample data. The current
analysis workflow uses JSONL/IDEA `alerts.json` files under
`sample_logs/alya_datasets/`.

```bash
# Decompress one sample for manual inspection
gzip -dk slips.log.gz

# Use the current JSONL/IDEA DAG parser on an alerts.json file
python3 ../alert_dag_parser.py alya_datasets/Malware/.../alerts.json
```

## File Size and Content Overview

| File | Type | Size | IPs | Primary Threats |
|------|------|------|-----|----------------|
| slips.log.gz | Malware | Large | Multiple | C&C, Port Scans, Blacklists |
| slips-1.log.gz | Malware | Medium | Few | Port Scans, Suspicious Connections |
| slips-5.log.gz | Malware | Medium | Few | Port Scans, Private IPs |
| slips-normal.log.gz | Normal | Large | Single | SSL, HTTP, User-agents |
| slips-normal-2.log.gz | Normal | Medium | Multiple | DNS, HTTP, SSL |
| slips-normal-3.log.gz | Normal | Medium | Multiple | Standard network activity |
| slips-evidence.log.gz | Processed | Medium | Multiple | Filtered evidence only |
| test_data.log.gz | Test | Small | Few | Controlled test scenarios |

## Best Practices

- Treat these files as archived plain-text reference data.
- Use `sample_logs/alya_datasets/**/alerts.json` for the current JSONL/IDEA workflow.
- Decompress `.log.gz` files only when you need manual inspection or ad hoc analysis.

## Data Sources

- **Malware Captures**: Network traffic from controlled malware execution environments
- **Normal Captures**: Legitimate network traffic from typical user activities
- **Evidence Filtering**: Processed using grep to extract only evidence entries
- **Test Data**: Synthetic or curated data for specific testing scenarios

## Security Note

All log files in this directory are for research and development purposes only. Malware capture logs contain evidence of malicious activities but are sanitized for safe analysis. No actual malware samples or sensitive data are present in these logs.

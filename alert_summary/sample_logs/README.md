# Sample Logs Directory

This directory contains various Slips evidence log files used for testing and demonstrating the DAG generator functionality. These logs represent different types of network security captures and processing methods.

## File Types and Origins

### Malware Capture Logs
These logs contain evidence from network traffic captures where malware was actively present and detected:

- **`slips.log`** - Complete malware capture log with all Slips evidence detection
- **`slips-1.log`** - Malware capture log from a different session/dataset
- **`slips-5.log`** - Malware capture log from another session/dataset

**Characteristics:**
- Contains evidence of malicious activities (C&C channels, port scans, blacklisted IPs)
- Higher density of high-severity threats
- Represents real-world malware behavior patterns
- Useful for testing attack pattern detection and incident response workflows

### Normal Network Capture Logs
These logs contain evidence from normal network operations without active malware:

- **`slips-normal.log`** - Normal network traffic capture
- **`slips-normal-2.log`** - Additional normal network capture
- **`slips-normal-3.log`** - Third normal network capture

**Characteristics:**
- Lower threat levels (mostly INFO/LOW/MEDIUM)
- Contains typical network activities (SSL connections, DNS queries, HTTP traffic)
- May include some false positives or benign suspicious activities
- Useful for baseline testing and false positive analysis

### Processed Evidence Logs
These logs are derived from other log files with specific processing applied:

- **`slips-evidence.log`** - Similar to `slips.log` but with all evidence entries filtered using grep
- **`test_data.log`** - Synthetic or curated test data for development purposes

**Characteristics:**
- `slips-evidence.log`: Clean evidence-only format, easier to parse
- `test_data.log`: Controlled dataset for testing specific scenarios

## Log Format Variations

The DAG generator supports multiple Slips log formats found in these files:

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

## Usage Examples

### Malware Analysis
```bash
# Analyze malware behavior patterns
python3 ../slips_dag_generator.py slips.log --all-ips --pattern

# Focus on high-severity threats from malware capture
python3 ../slips_dag_generator.py slips-5.log 192.168.1.113 --min-threat high
```

### Normal Network Analysis
```bash
# Baseline analysis of normal network activity
python3 ../slips_dag_generator.py slips-normal.log --all-ips --minimal

# Compare normal vs malware patterns
python3 ../slips_dag_generator.py slips-normal-2.log 10.0.2.15 --full
```

### Evidence Processing
```bash
# Clean evidence analysis
python3 ../slips_dag_generator.py slips-evidence.log --all-ips --json

# Development testing
python3 ../slips_dag_generator.py test_data.log 192.168.1.113
```

## File Size and Content Overview

| File | Type | Size | IPs | Primary Threats |
|------|------|------|-----|----------------|
| slips.log | Malware | Large | Multiple | C&C, Port Scans, Blacklists |
| slips-1.log | Malware | Medium | Few | Port Scans, Suspicious Connections |
| slips-5.log | Malware | Medium | Few | Port Scans, Private IPs |
| slips-normal.log | Normal | Large | Single | SSL, HTTP, User-agents |
| slips-normal-2.log | Normal | Medium | Multiple | DNS, HTTP, SSL |
| slips-normal-3.log | Normal | Medium | Multiple | Standard network activity |
| slips-evidence.log | Processed | Medium | Multiple | Filtered evidence only |
| test_data.log | Test | Small | Few | Controlled test scenarios |

## Best Practices

### For Testing
- Use `test_data.log` for quick functionality tests
- Use `slips-evidence.log` for clean parsing tests
- Use normal logs for false positive analysis

### For Demonstration
- Use `slips.log` for comprehensive malware analysis demos
- Use `slips-normal.log` for normal network analysis
- Use `slips-5.log` for focused malware incident response

### For Development
- Test with both malware and normal logs to ensure balanced detection
- Verify parsing works across different log formats
- Use various IP addresses to test multi-IP functionality

## Data Sources

- **Malware Captures**: Network traffic from controlled malware execution environments
- **Normal Captures**: Legitimate network traffic from typical user activities
- **Evidence Filtering**: Processed using grep to extract only evidence entries
- **Test Data**: Synthetic or curated data for specific testing scenarios

## Security Note

All log files in this directory are for research and development purposes only. Malware capture logs contain evidence of malicious activities but are sanitized for safe analysis. No actual malware samples or sensitive data are present in these logs.
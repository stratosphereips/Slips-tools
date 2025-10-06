# Generate Dataset Alerts

## Overview

`generate_dataset_alerts.sh` generates JSON datasets from Slips JSONL/IDEA format alert files with AI-enhanced multi-perspective analysis. This script uses the field-based `alert_dag_parser.py` for future-proof incident parsing.

## Key Differences from `generate_dataset.sh`

- **Input Format**: JSONL/IDEA format (`.json` files with Incidents and Events) vs plain text logs
- **Parser**: Uses `alert_dag_parser.py` (field-based) vs `slips_dag_generator.py` (regex-based)
- **Future-Proof**: Handles unknown alert types automatically without code changes
- **Output**: Identical JSON/text/CSV format

## Usage

```bash
# Basic usage
./generate_dataset_alerts.sh alerts.json dataset.json

# With custom model and text output
./generate_dataset_alerts.sh alerts.json dataset.json --model qwen2.5:3b --text-output report.txt

# Generate all output formats
./generate_dataset_alerts.sh alerts.json dataset.json --csv-output dataset.csv
```

## Options

- `--model MODEL` - LLM model to use (default: gpt-4o-mini)
- `--base-url URL` - LLM API endpoint (default: https://api.openai.com/v1)
- `--text-output FILE` - Generate human-readable text report
- `--csv-output FILE` - Generate CSV format output

## Enhanced Error Handling

### Features
- **Retry Logic**: 3 attempts per LLM query with 5-second delays
- **Pre-flight Check**: Validates LLM connectivity before processing
- **Graceful Interruption**: CTRL+C saves partial dataset with proper JSON closure
- **Error Logging**: Creates `<output>.errors.log` with timestamped errors
- **Skip Failed Alerts**: Continues processing if individual alerts fail

### Error Recovery
```bash
# If interrupted, partial dataset is saved
# Check error log for details
cat dataset.json.errors.log
```

## Input File Format

### JSONL/IDEA Format
```json
{"Status": "Incident", "ID": "uuid", "CorrelID": ["event-uuid-1", ...], ...}
{"Status": "Event", "ID": "uuid", "Severity": "High", "Source": [...], "Target": [...], ...}
```

### Validation
- Checks for valid JSONL format
- Verifies presence of Incidents
- Confirms Event correlation

## Output Format

### JSON Dataset
```json
{
  "dataset": [
    {
      "alert_id": 1,
      "evidence": "Incident analysis with events...",
      "behavior_explanation": "Technical network behavior analysis",
      "cause_analysis": "Root cause investigation",
      "risk_assessment": "Threat level and business impact"
    }
  ]
}
```

## Example Workflow

```bash
# 1. Test with sample malware capture data
./generate_dataset_alerts.sh \
  sample_logs/alya_datasets/Malware/CTU-Malware-Capture-Botnet-346-1/2018-04-03_win12-fixed/9/alerts.json \
  malware_dataset.json

# 2. Generate with text report
./generate_dataset_alerts.sh alerts.json dataset.json --text-output analysis.txt

# 3. If errors occur, check error log
cat dataset.json.errors.log
```

## Requirements

- Python 3.6+
- `alert_dag_parser.py` (included)
- `stream_query_llm_long_prompt.py` (LLM interface)
- `jq` (JSON processing)
- OpenAI API key in environment

## Performance

- **Pre-processing**: Validates file format and LLM connectivity (~2-5 seconds)
- **LLM Analysis**: 3 queries per incident (behavior, cause, risk)
- **Retry Overhead**: Up to 15 seconds per failed query (3 retries × 5 seconds)
- **Example**: 47 incidents × 3 queries = ~141 LLM calls

## Comparison

| Feature | generate_dataset_alerts.sh | generate_dataset.sh |
|---------|---------------------------|---------------------|
| Input Format | JSONL/IDEA | Plain text logs |
| Parser | alert_dag_parser.py | slips_dag_generator.py |
| Classification | Field-based | Regex-based |
| Future-proof | ✅ Yes | ❌ Requires updates |
| Error Handling | Enhanced | Enhanced |
| Output Format | JSON/text/CSV | JSON/text/CSV |

## Error Scenarios

### LLM Connectivity Failure
```
[ERROR] Cannot connect to LLM model at https://api.openai.com/v1
[ERROR] Please check API key and endpoint configuration
```

### Invalid File Format
```
[ERROR] File is not valid JSONL format (first line is not valid JSON)
[ERROR] No Incidents found in file (expected IDEA format with Status: Incident)
```

### Partial Completion
```
[WARNING] Completed with 3 failed incidents (skipped)
[WARNING] Errors were logged to: dataset.json.errors.log
```

## See Also

- `generate_dataset.sh` - For plain text Slips logs
- `alert_dag_parser.py` - Incident parser documentation
- `ALERT_DAG_PARSER.md` - Technical architecture details

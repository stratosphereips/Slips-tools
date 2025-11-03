# sample_dataset.py

Random sampling tool for Slips IDEA-format alert datasets. Samples incidents with their associated events while preserving the incident-event relationship.

## Purpose

Create representative subsets of large Slips alert datasets for testing, analysis, or LLM evaluation.

## Key Features

- **Incident-based sampling**: Samples INCIDENT alerts and automatically includes all related EVENT alerts (via CorrelID)
- **JSONL output**: Compatible with `alert_dag_parser.py` and other JSONL processors
- **Filtering**: By category (Normal/Malware), severity (Low/Medium/High)
- **Reproducible**: Use `--seed` for consistent sampling
- **Statistics**: Event counts, severity breakdown, dataset distribution

## Basic Usage

```bash
# Sample 10 random incidents
python3 sample_dataset.py --num-incidents 10 --output sample.jsonl

# Sample with statistics
python3 sample_dataset.py --num-incidents 10 --output sample.jsonl --include-stats

# Sample from 3 random files, 5 incidents each
python3 sample_dataset.py --num-files 3 --incidents-per-file 5 --output sample.jsonl
```

## Filtering

```bash
# Only malware incidents
python3 sample_dataset.py --category malware --num-incidents 20 --output malware.jsonl

# Only high-severity incidents
python3 sample_dataset.py --severity high --num-incidents 10 --output high.jsonl
```

## Reproducibility

```bash
# Same seed = same sample
python3 sample_dataset.py --num-incidents 15 --seed 42 --output reproducible.jsonl
```

## Use with Alert Parsers

```bash
# Create sample
python3 sample_dataset.py --num-incidents 5 --output sample.jsonl

# Analyze with DAG parser
python3 alert_dag_parser.py sample.jsonl

# Analyze with LLM parser
python3 alert_dag_parser_llm.py sample.jsonl --verbose
```

## Output Format

**JSONL (JSON Lines)**: One JSON object per line
- Each incident followed by its associated events
- Original IDEA 2.0 format preserved
- No wrapper structure

**Statistics** (with `--include-stats`):
- Separate `.stats.json` file
- Printed to stderr during execution

## Dataset Structure

Expected directory structure:
```
sample_logs/alya_datasets/
├── Normal/
│   └── CTU-Normal-XX/...
└── Malware/
    └── CTU-Malware-Capture-Botnet-XXX/...
```

Each dataset contains `alerts.json` files with INCIDENT and EVENT alerts in IDEA format.

## Options

| Option | Description |
|--------|-------------|
| `--num-incidents N` | Total incidents to sample across all files |
| `--num-files N` | Number of random files to sample from |
| `--incidents-per-file N` | Incidents to sample from each file |
| `--category {normal,malware}` | Filter by dataset category |
| `--severity {low,medium,high}` | Filter by incident severity |
| `--seed N` | Random seed for reproducibility |
| `--include-stats` | Generate statistics file |
| `--output FILE` | Output JSONL file path (required) |

## Dependencies

- Python 3.6+
- Standard library only (no external packages)

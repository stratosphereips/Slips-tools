# Current Repository Guide

This repository contains the current Slips alert analysis workflow for JSONL/IDEA alert files.

## Current Workflow

Use the root-level scripts for active dataset generation and evaluation:

- `sample_dataset.py` / `sample_dataset.sh` sample incidents from `sample_logs/alya_datasets`.
- `alert_dag_parser.py` / `generate_dag_analysis.sh` generate structured DAG-style incident analysis from JSONL/IDEA files.
- `alert_dag_parser_llm.py` / `generate_llm_analysis.sh` generate summary and behavior analysis.
- `alert_cause_risk_analyzer.py` / `generate_cause_risk_analysis.sh` generate cause and risk analysis.
- `correlate_incidents.py` merges summary analyses.
- `correlate_risks.py` merges cause/risk analyses.
- `evaluate_summaries.py` and `evaluate_risk.py` run LLM-as-judge evaluation.
- `analyze_results.py`, `analyze_results_risk.py`, and `generate_dashboard.py` create reports and dashboards.

## Main Pipelines

Summary workflow:

```bash
./sample_dataset.sh 100 datasets/my_dataset --seed 42
./generate_dag_analysis.sh datasets/my_dataset.jsonl
./generate_llm_analysis.sh datasets/my_dataset.jsonl --model gpt-4o-mini --group-events --behavior-analysis
python3 correlate_incidents.py datasets/my_dataset.*.json --jsonl datasets/my_dataset.jsonl -o datasets/final_dataset.json
```

Cause and risk workflow:

```bash
./sample_dataset.sh 100 datasets/my_dataset --seed 42
./generate_dag_analysis.sh datasets/my_dataset.jsonl
./generate_cause_risk_analysis.sh datasets/my_dataset.jsonl --model gpt-4o-mini --group-events
python3 correlate_risks.py datasets/my_dataset.*.json --jsonl datasets/my_dataset.jsonl -o datasets/final_dataset_risk.json
```

Unified inference:

```bash
python3 inference.py datasets/my_dataset.jsonl --task both --model gpt-4o-mini --group-events
```

## Documentation

- Summary workflow: `README_dataset_summary_workflow.md`
- Cause/risk workflow: `README_dataset_risk_workflow.md`
- Workflow comparison: `WORKFLOWS_OVERVIEW.md`
- Unified inference: `INFERENCE.md`
- Evaluation: `LLM_EVALUATION_GUIDE.md`

## Notes

The `utils/` directory contains deprecated legacy helpers and has its own README. Do not use those utilities for the current root-level workflows.

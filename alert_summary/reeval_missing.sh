#!/bin/bash
for id in 6d8fd038 bd1407ef; do python3 evaluate_risk.py --input datasets/risk_dataset.json --output datasets/risk_dataset_results_oss.json -j gpt-oss-120b --base-url https://llm.ai.e-infra.cz/v1 --entry $id; done

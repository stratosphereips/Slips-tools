#!/bin/bash
# Full pipeline execution
#./sample_dataset.sh 100 my_dataset_05
#./generate_dag_analysis.sh my_dataset_05.jsonl
./generate_cause_risk_analysis.sh datasets/my_dataset_05.jsonl --model gpt-4o-mini --group-events --verbose
./generate_cause_risk_analysis.sh datasets/my_dataset_05.jsonl --model gpt-4o --group-events  --verbose
./generate_cause_risk_analysis.sh datasets/my_dataset_05.jsonl --model qwen2.5:3b --base-url http://chatbotapi.ingenieria.uncuyo.edu.ar/v1 --group-events --verbose
mv datasets/my_dataset_05.cause_risk.qwen2.5.json  datasets/my_dataset_05.cause_risk.qwen2.5:3b.json
./generate_cause_risk_analysis.sh datasets/my_dataset_05.jsonl --model qwen2.5:1.5b --base-url http://chatbotapi.ingenieria.uncuyo.edu.ar/v1 --group-events --verbose
python3 correlate_risks.py datasets/my_dataset_05.cause_risk*.json --jsonl datasets/my_dataset_05.jsonl -o datasets/final_dataset_05_risk.json

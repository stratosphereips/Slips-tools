#!/bin/bash
# Full pipeline execution
./sample_dataset.sh 100 my_dataset_06
./generate_dag_analysis.sh datasets/my_dataset_06.jsonl
./generate_llm_analysis.sh datasets/my_dataset_06.jsonl --model gpt-4o-mini --group-events --behavior-analysis
./generate_llm_analysis.sh datasets/my_dataset_06.jsonl --model gpt-4o --group-events --behavior-analysis
./generate_llm_analysis.sh datasets/my_dataset_06.jsonl --model qwen2.5:3b --base-url http://chatbotapi.ingenieria.uncuyo.edu.ar/v1 --group-events --behavior-analysis --verbose
mv datasets/my_dataset_06.llm.qwen2.5.json datasets/my_dataset_06.llm.qwen2.5:3b.json
./generate_llm_analysis.sh datasets/my_dataset_06.jsonl --model qwen2.5:1.5b --base-url http://chatbotapi.ingenieria.uncuyo.edu.ar/v1 --group-events --behavior-analysis --verbose
python3 correlate_incidents.py datasets/my_dataset_06.llm.*.json --jsonl datasets/my_dataset_06.jsonl -o datasets/final_dataset_06.json

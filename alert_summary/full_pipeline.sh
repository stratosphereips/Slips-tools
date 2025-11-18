#!/bin/bash
# Full pipeline execution
./sample_dataset.sh 100 my_dataset_06
./generate_dag_analysis.sh my_dataset_06.jsonl
./generate_llm_analysis.sh my_dataset_06.jsonl --model gpt-4o-mini --group-events --behavior-analysis
./generate_llm_analysis.sh my_dataset_06.jsonl --model gpt-4o --group-events --behavior-analysis
./generate_llm_analysis.sh my_dataset_06.jsonl --model qwen2.5:3b --base-url http://chatbotapi.ingenieria.uncuyo.edu.ar/v1 --group-events --behavior-analysis --verbose
mv my_dataset_06.llm.qwen2.5.json my_dataset_06.llm.qwen2.5:15b.json
./generate_llm_analysis.sh my_dataset_06.jsonl --model qwen2.5:1.5b --base-url http://chatbotapi.ingenieria.uncuyo.edu.ar/v1 --group-events --behavior-analysis --verbose
python3 correlate_incidents.py my_dataset_06.*.json --jsonl my_dataset_06.jsonl -o final_dataset_06.json

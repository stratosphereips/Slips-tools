# Full pipeline execution
./sample_dataset.sh 20 my_dataset --category malware --seed 42
./generate_dag_analysis.sh my_dataset.jsonl
./generate_llm_analysis.sh my_dataset.jsonl --model gpt-4o-mini --group-events --behavior-analysis
./generate_llm_analysis.sh my_dataset.jsonl --model qwen2.5:3b --base-url http://10.147.20.102:11434/v1 --group-events --behavior-analysis
./generate_llm_analysis.sh my_dataset.jsonl --model qwen2.5:1.5b --base-url http://10.147.20.102:11434/v1 --group-events --behavior-analysis
python3 correlate_incidents.py my_dataset.*.json -o final_dataset.json

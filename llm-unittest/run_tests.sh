#!/bin/bash

unittests="
01_test_action_json_parsing.yaml
02_test_action_json_understanding.yaml
03_test_action_json_w_parameters.yaml
04_test_action_json.yaml
05_test_zeek_analysis.yaml
06_test_zeek_generation.yaml
07_test_zeek_summary.yaml
08_test_tool_use.yaml
09_test_action_json_parsing_fmt_openai_api.yaml
10_test_zeek_sig_generation.yaml
"

#for test_case in `ls *.yaml`
for test_case in `echo $unittests`
do
	echo $test_case
	#do  OLLAMA_BASE_URL="http://10.16.20.252:11434" promptfoo eval -c $test_case  
	#OPENAI_API_KEY="ollama" OPENAI_BASE_URL="http://10.16.20.252:11434/v1" promptfoo eval -c $test_case  
	
	promptfoo eval -c $test_case  --max-concurrency 1 --no-cache
done


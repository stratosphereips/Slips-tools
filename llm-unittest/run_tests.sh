#!/bin/bash

for test_case in `ls *.yaml`
do
	echo $test_case
	#do  OLLAMA_BASE_URL="http://10.16.20.252:11434" promptfoo eval -c $test_case  
	OPENAI_API_KEY="ollama" OPENAI_BASE_URL="http://10.16.20.252:11434/v1" promptfoo eval -c $test_case  
done


#!/bin/bash
python stream_query_llm.py --model qwen3:14b --prompt "\nothink write a bash script for monitoring a service" --base_url http://cabildo:11434/v1

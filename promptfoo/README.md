List of tests

```
01_test_action_json_parsing.yaml 
02_test_action_json_understanding.yaml
03_test_action_json_w_parameters.yaml
04_test_action_json.yaml
05_test_zeek_analysis.yaml
06_test_zeek_generation.yaml
07_test_zeek_summary.yaml
08_test_tool_use.yaml
```

For using with ollama

```
OLLAMA_BASE_URL="http://<ollama_server>:11434" promptfoo eval -c <yaml_file>
```

Afterwards, you can view the results by running `promptfoo view`

# Promptfoo Test Suite for small models based on OLLAMA

This repository contains a collection of YAML-based test files for evaluating prompts using [Promptfoo](https://github.com/promptfoo/promptfoo) with [Ollama](https://ollama.com/).

## 🛠️ Prerequisites

- Ollama running on your server or local machine
- Promptfoo installed:
  ```bash
  npm install -g promptfoo
  ```

## ⚙️ Usage

To run a test:

```bash
OPENAI_API_KEY="ollama" OPENAI_BASE_URL="http://10.16.20.252:11434/v1" promptfoo eval -c <yaml_file>
```

or is you want to run all the tests:
```bash
for test_case in `ls *.yaml`;do OPENAI_API_KEY="ollama" OPENAI_BASE_URL="http://10.16.20.252:11434/v1" promptfoo eval -c $test_case  ;done
```

Replace `<ollama_server>` with your actual Ollama host (e.g., `localhost`).

To view the results:

```bash
promptfoo view
```

## 🧪 Test Cases

### 01 - Action JSON Parsing
**File**: `01_test_action_json_parsing.yaml`  
Tests the model's ability to correctly parse structured JSON responses from prompt output.

---

### 02 - Action JSON Understanding
**File**: `02_test_action_json_understanding.yaml`  
Evaluates whether the model can interpret and reason about the meaning and structure of JSON action definitions.

---

### 03 - Action JSON with Parameters
**File**: `03_test_action_json_w_parameters.yaml`  
Focuses on the model's handling of JSON actions that include dynamic parameters.

---

### 04 - Action JSON General
**File**: `04_test_action_json.yaml`  
Focuses on the model's handling of simpler JSON actions.

---

### 05 - Zeek Analysis
**File**: `05_test_zeek_analysis.yaml`  
Assesses the model’s understanding and analysis of [Zeek](https://zeek.org/) network traffic logs.

---

### 06 - Zeek Generation
**File**: `06_test_zeek_generation.yaml`  
Tests the model’s ability to generate Zeek logs. The idea is to check how good is model's internal undestanding of zeek.

---

### 07 - Zeek Summary
**File**: `07_test_zeek_summary.yaml`  
Checks how well the model can summarize Zeek data into human-readable security insights. Also include some minimal decision making about particular IP addresses.

---

### 08 - Tool Use
**File**: `08_test_tool_use.yaml`  
Evaluates how well the model understands and integrates tool-based workflows or simulated tool use in prompt outputs.

### 09 - Action JSON General API
**File**: `09_test_action_json_parsing_fmt_openai_api.yaml`
SImilar to test 03, but using openai API for validating and parsing JSON format.

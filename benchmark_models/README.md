# Ollama Model Benchmark Script

This directory contains a Bash script for benchmarking models. The script automates the benchmarking of models served by a remote Ollama instance. It fetches the list of available models, runs a specified prompt against each model using a local Python script, and measures the model's performance. For each model, it collects:

Quantization level

Disk size (from /api/tags)

RAM usage while loaded (from /api/ps)

Tokens per second (TPS) from the Python output

The data is printed in a formatted table and also saved to a CSV file (results.csv) for further analysi

##  Requirements

* Bash
* `curl`
* [`jq`](https://stedolan.github.io/jq/) for JSON parsing
* Python script: `stream_query_llm.py` that supports:

  * `--model`
  * `--prompt`
  * `--base_url`
  * `--stats_only` flag

##  Files

* `benchmark_ollama_models.sh` — Main benchmarking script
* `results.csv` — Output file containing the benchmark results
* `stream_query_llm.py` — Your local script that streams responses and prints usage stats

## Collected Metrics

The script gathers and logs the following for each model:

| Metric            | Source        | Description                                   |
| ----------------- | ------------- | --------------------------------------------- |
| Model name        | /api/tags     | Name of the model (e.g., llama3:8b)           |
| Quantization      | /api/ps       | Runtime quantization level (e.g., Q4\_K\_M)   |
| Disk size (MB)    | /api/tags     | Size of the GGUF model on disk                |
| RAM size (MB)     | /api/ps       | Actual loaded model size in memory            |
| Tokens per second | Python script | Measured performance (completion tokens/time) |

##  Usage

1. Make the script executable:

```bash
chmod +x benchmark_ollama_models.sh
```

2. Run it:

```bash
./benchmark_ollama_models.sh
```

This will:

* Call each available model
* Run a prompt
* Log and print performance data
* Save results to `results.csv`

##  Configuration

Inside the script, you can customize:

* `OLLAMA_HOST`: IP or hostname of your Ollama server
* `PORT`: Ollama server port (default is `11434`)
* `PROMPT`: Prompt string to be used for benchmarking

##  Notes

* Only models successfully loaded and used will return RAM size
* If TPS extraction fails, the script will mark the entry as `ERROR`
* The script assumes Ollama's REST API is accessible remotely


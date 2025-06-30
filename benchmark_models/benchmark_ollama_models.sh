#!/bin/bash

# --- Configuration ---
OLLAMA_HOST="10.147.20.104"
PORT="11434"
BASE_URL="http://$OLLAMA_HOST:$PORT/v1"
API_TAGS_URL="http://$OLLAMA_HOST:$PORT/api/tags"
API_PS_URL="http://$OLLAMA_HOST:$PORT/api/ps"
PYTHON_SCRIPT="stream_query_llm.py"
PROMPT="generate a zeek script for detecting Suspicious HTTP User-Agents. Be concise."
CSV_FILE="results.csv"

# --- Check prerequisites ---
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
  echo "❌ Python script '$PYTHON_SCRIPT' not found!"
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "❌ 'jq' is required but not installed."
  exit 1
fi

# --- Fetch model list ---
tags_response=$(curl -s "$API_TAGS_URL")
if [[ -z "$tags_response" ]]; then
  echo "❌ Failed to fetch models from $API_TAGS_URL"
  exit 1
fi

# --- CSV Output File ---
echo "model,quantization,disk_size_mb,ram_size_mb,tokens_per_second" > "$CSV_FILE"

# --- Table Header ---
echo -e "\n📊 Remote Model Benchmark Summary:"
printf "%-25s %-12s %14s %14s %10s\n" "Model" "Quantization" "Disk Size (MB)" "RAM Size (MB)" "TPS"
printf "%-25s %-12s %14s %14s %10s\n" "-----" "------------" "--------------" "-------------" "----"

# --- Loop through models ---
models=$(echo "$tags_response" | jq -c '.models[]')

for model_json in $models; do
  model=$(echo "$model_json" | jq -r '.name')
  quant=$(echo "$model_json" | jq -r '.details.quantization_level // "N/A"')
  disk_bytes=$(echo "$model_json" | jq -r '.size // 0')
  disk_mb=$(awk "BEGIN {printf \"%.1f\", $disk_bytes/1024/1024}")

  # Run benchmark
  output=$(python3 "$PYTHON_SCRIPT" \
    --prompt "$PROMPT" \
    --base_url "$BASE_URL" \
    --model "$model" \
    --stats_only 2>/dev/null)

  # Extract TPS
  tps=$(echo "$output" | grep "Tokens per second" | awk '{print $(NF-1)}')
  display_tps="${tps:-ERROR}"
  csv_tps="${tps:-}"

  # Query /api/ps for live RAM usage
  ps_response=$(curl -s "$API_PS_URL")
  ps_entry=$(echo "$ps_response" | jq -c --arg name "$model" '.models[] | select(.name == $name)')

  ram_bytes=$(echo "$ps_entry" | jq -r '.size // 0')
  ram_mb=$(awk "BEGIN {printf \"%.1f\", $ram_bytes/1024/1024}")

  # Print to terminal
  printf "%-25s %-12s %14s %14s %10s\n" "$model" "$quant" "$disk_mb" "$ram_mb" "$display_tps"

  # Append to CSV
  echo "$model,$quant,$disk_mb,$ram_mb,$csv_tps" >> "$CSV_FILE"
done

echo -e "\n✅ Results saved to: $CSV_FILE"


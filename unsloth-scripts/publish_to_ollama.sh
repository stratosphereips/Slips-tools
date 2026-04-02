#!/usr/bin/env bash
# Publish Q4_K_M and Q5_K_M GGUF models to Ollama.
#
# Prerequisites:
#   - Run `ollama login` before executing this script
#   - venv in unsloth-scripts must have unsloth installed
#
# Usage:
#   ./publish_to_ollama.sh [model_path]
#
# Default model path: /home/harpo/CEPH/LLM-models/qwen_finetuned_merged_16bit

set -euo pipefail

MODEL_PATH="${1:-/home/harpo/CEPH/LLM-models/qwen_finetuned_merged_16bit}"
OLLAMA_NAME="stratosphere/qwen2.5-1.5b-slips-immune-summarization"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_Q4="${SCRIPT_DIR}/gguf_q4_k_m"
OUT_Q5="${SCRIPT_DIR}/gguf_q5_k_m"

echo "Model path: ${MODEL_PATH}"
echo "Ollama name: ${OLLAMA_NAME}"
echo

# Activate venv (unsloth required for conversion)
source "${SCRIPT_DIR}/venv/bin/activate"

# 1. Convert both quants
echo "==> Converting Q4_K_M..."
python3 "${SCRIPT_DIR}/convert_to_gguf.py" "$MODEL_PATH" --quant q4_k_m --output "$OUT_Q4"

echo "==> Converting Q5_K_M..."
python3 "${SCRIPT_DIR}/convert_to_gguf.py" "$MODEL_PATH" --quant q5_k_m --output "$OUT_Q5"

# 2. Register locally with Ollama
echo "==> Creating Ollama model: ${OLLAMA_NAME}:q4_k_m"
(cd "$OUT_Q4" && ollama create "${OLLAMA_NAME}:q4_k_m" -f Modelfile)

echo "==> Creating Ollama model: ${OLLAMA_NAME}:q5_k_m"
(cd "$OUT_Q5" && ollama create "${OLLAMA_NAME}:q5_k_m" -f Modelfile)

# 3. Tag Q4_K_M as latest
echo "==> Tagging Q4_K_M as latest..."
ollama cp "${OLLAMA_NAME}:q4_k_m" "${OLLAMA_NAME}:latest"

# 4. Push all three tags
echo "==> Pushing ${OLLAMA_NAME}:q4_k_m..."
ollama push "${OLLAMA_NAME}:q4_k_m"

echo "==> Pushing ${OLLAMA_NAME}:q5_k_m..."
ollama push "${OLLAMA_NAME}:q5_k_m"

echo "==> Pushing ${OLLAMA_NAME}:latest..."
ollama push "${OLLAMA_NAME}:latest"

echo
echo "Done. Published ${OLLAMA_NAME} (q4_k_m, q5_k_m, latest)"
echo "Verify at: https://ollama.com/stratosphere/qwen2.5-1.5b-slips-immune-summarization"

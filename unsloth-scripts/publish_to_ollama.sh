#!/usr/bin/env bash
# Publish GGUF models to Ollama.
#
# Prerequisites:
#   - Run `ollama login` before executing this script
#   - venv in unsloth-scripts must have unsloth installed
#
# Usage:
#   ./publish_to_ollama.sh [--model path] [--quant quant]
#
#   --model     Path to merged 16-bit model (default: /home/harpo/CEPH/LLM-models/qwen_finetuned_merged_16bit)
#   --quant     One of: q4_k_m, q5_k_m, q8_0  (default: build and push all three)
#
# Examples:
#   ./publish_to_ollama.sh                              # build q4_k_m, q5_k_m, q8_0
#   ./publish_to_ollama.sh --quant q5_k_m              # build q5_k_m only
#   ./publish_to_ollama.sh --model /path/to/model --quant q8_0

set -euo pipefail

MODEL_PATH="/home/harpo/CEPH/LLM-models/qwen_finetuned_merged_16bit"
QUANT_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL_PATH="$2"; shift 2 ;;
        --quant) QUANT_ARG="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done
OLLAMA_NAME="stratosphere/qwen2.5-1.5b-slips-immune-summarization"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_QUANTS=(q4_k_m q5_k_m q8_0)

# Determine which quants to build
if [[ -n "$QUANT_ARG" ]]; then
    QUANTS=("${QUANT_ARG,,}")  # normalise to lowercase
else
    QUANTS=("${DEFAULT_QUANTS[@]}")
fi

echo "Model path:  ${MODEL_PATH}"
echo "Ollama name: ${OLLAMA_NAME}"
echo "Quants:      ${QUANTS[*]}"
echo

# Activate venv (unsloth required for conversion)
source "${SCRIPT_DIR}/venv/bin/activate"

TAGS_BUILT=()

for QUANT in "${QUANTS[@]}"; do
    OUT_DIR="${SCRIPT_DIR}/gguf_${QUANT}"
    TAG="${OLLAMA_NAME}:${QUANT}"

    # 1. Convert
    echo "==> Converting ${QUANT^^}..."
    python3 "${SCRIPT_DIR}/convert_to_gguf.py" "$MODEL_PATH" --quant "$QUANT" --output "$OUT_DIR"

    # 2. Register locally
    echo "==> Creating Ollama model: ${TAG}"
    (cd "$OUT_DIR" && ollama create "$TAG" -f Modelfile)

    TAGS_BUILT+=("$TAG")
done

# 3. Tag latest = q4_k_m if it was built, otherwise first quant built
LATEST_SOURCE="${OLLAMA_NAME}:${QUANTS[0]}"
echo "==> Tagging ${QUANTS[0]} as latest..."
ollama cp "$LATEST_SOURCE" "${OLLAMA_NAME}:latest"

# 4. Push all built tags + latest
for TAG in "${TAGS_BUILT[@]}"; do
    echo "==> Pushing ${TAG}..."
    ollama push "$TAG"
done

echo "==> Pushing ${OLLAMA_NAME}:latest..."
ollama push "${OLLAMA_NAME}:latest"

echo
echo "Done. Published ${OLLAMA_NAME} (${QUANTS[*]}, latest)"
echo "Verify at: https://ollama.com/stratosphere/qwen2.5-1.5b-slips-immune-summarization"

#!/usr/bin/env bash
# Publish risk model GGUF to Ollama.
#
# Downloads the model directly from HuggingFace to ensure we always use the
# canonical published weights (stratosphere/qwen2.5-1.5b-slips-immune-risk).
#
# Prerequisites:
#   - Run `ollama login` before executing this script
#   - venv in unsloth-scripts must have unsloth installed
#   - huggingface_hub installed in venv (for snapshot_download)
#
# Usage:
#   ./publish_to_ollama_risk.sh [--quant quant]
#
#   --quant     One of: q4_k_m, q5_k_m, q8_0  (default: build and push all three)
#
# Examples:
#   ./publish_to_ollama_risk.sh                # build q4_k_m, q5_k_m, q8_0
#   ./publish_to_ollama_risk.sh --quant q5_k_m # build q5_k_m only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HF_REPO_ID="stratosphere/qwen2.5-1.5b-slips-immune-risk"
QUANT_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quant) QUANT_ARG="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

OLLAMA_NAME="stratosphere/qwen2.5-1.5b-slips-immune-risk"
DEFAULT_QUANTS=(q4_k_m q5_k_m q8_0)

if [[ -n "$QUANT_ARG" ]]; then
    QUANTS=("${QUANT_ARG,,}")
else
    QUANTS=("${DEFAULT_QUANTS[@]}")
fi

source "${SCRIPT_DIR}/venv/bin/activate"

# Download model from HuggingFace to ensure canonical weights are used
echo "==> Downloading ${HF_REPO_ID} from HuggingFace..."
MODEL_PATH=$(python3 -c "
from huggingface_hub import snapshot_download
path = snapshot_download(repo_id='${HF_REPO_ID}')
print(path)
")
echo "    Downloaded to: ${MODEL_PATH}"
echo

echo "Model path:  ${MODEL_PATH}"
echo "Ollama name: ${OLLAMA_NAME}"
echo "Quants:      ${QUANTS[*]}"
echo

LLAMA_CPP_DIR="/home/harpo/.unsloth/llama.cpp"
CONVERT_SCRIPT="${LLAMA_CPP_DIR}/convert_hf_to_gguf.py"
LLAMA_QUANTIZE="${LLAMA_CPP_DIR}/llama-quantize"
GGUF_BASE_DIR="${SCRIPT_DIR}/gguf_risk_base"

declare -A QUANT_NAME_MAP
QUANT_NAME_MAP[q4_k_m]="Q4_K_M"
QUANT_NAME_MAP[q5_k_m]="Q5_K_M"
QUANT_NAME_MAP[q8_0]="Q8_0"

# 1. Convert HF model to F16 GGUF once
mkdir -p "${GGUF_BASE_DIR}"
F16_GGUF="${GGUF_BASE_DIR}/model-f16.gguf"
if [[ ! -f "${F16_GGUF}" ]]; then
    echo "==> Converting HF model to F16 GGUF..."
    python3 "${CONVERT_SCRIPT}" "${MODEL_PATH}" --outtype f16 --outfile "${F16_GGUF}"
else
    echo "==> F16 GGUF already exists, skipping conversion."
fi

TAGS_BUILT=()

for QUANT in "${QUANTS[@]}"; do
    OUT_DIR="${SCRIPT_DIR}/gguf_risk_${QUANT}"
    TAG="${OLLAMA_NAME}:${QUANT}"
    QUANT_UPPER="${QUANT_NAME_MAP[$QUANT]}"
    QUANT_GGUF="${OUT_DIR}/model-${QUANT_UPPER}.gguf"

    mkdir -p "${OUT_DIR}"

    # 2. Quantize
    echo "==> Quantizing to ${QUANT_UPPER}..."
    "${LLAMA_QUANTIZE}" "${F16_GGUF}" "${QUANT_GGUF}" "${QUANT_UPPER}"

    # 3. Write Modelfile
    cat > "${OUT_DIR}/Modelfile" <<EOF
FROM ./model-${QUANT_UPPER}.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
{{ .Response }}<|im_end|>
"""

PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
EOF

    # 4. Copy README
    cp "${SCRIPT_DIR}/README_risk_model.md" "${OUT_DIR}/README.md"

    # 5. Register locally with Ollama
    echo "==> Creating Ollama model: ${TAG}"
    (cd "$OUT_DIR" && ollama create "$TAG" -f Modelfile)

    TAGS_BUILT+=("$TAG")
done

# 3. Tag latest = first quant built (q4_k_m by default)
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
echo "Verify at: https://ollama.com/stratosphere/qwen2.5-1.5b-slips-immune-risk"

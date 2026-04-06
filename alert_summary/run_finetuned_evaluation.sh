#!/bin/bash
# Evaluate finetuned model against 4-model baseline using LLM-as-judge

JUDGE_MODEL="gpt-oss-120b"           # e.g. gpt-4o, qwen2.5:72b
BASE_URL="https://llm.ai.e-infra.cz/v1"              # e.g. http://localhost:11434/v1  (leave empty for OpenAI)
API_KEY="sk-bdeda8f16bdf44ac88f80d61c19d6c8e"               # leave empty to use OPENAI_API_KEY env var

INPUT="../unsloth-scripts/finetuned_eval_results.json"
OUTPUT="results/finetuned_results.json"

# Build arguments
ARGS="--input $INPUT --output $OUTPUT"
[ -n "$JUDGE_MODEL" ] && ARGS="$ARGS --judge $JUDGE_MODEL"
[ -n "$BASE_URL" ]    && ARGS="$ARGS --base-url $BASE_URL"
[ -n "$API_KEY" ]     && ARGS="$ARGS --api-key $API_KEY"

mkdir -p results

echo "Running finetuned model evaluation..."
echo "Input:  $INPUT"
echo "Output: $OUTPUT"
echo "Judge:  ${JUDGE_MODEL:-gpt-4o (default)}"
echo "URL:    ${BASE_URL:-OpenAI default}"
echo ""

python3 evaluate_summaries.py $ARGS

echo ""
echo "Analyzing results..."
python3 analyze_results.py --results "$OUTPUT" --summary results/finetuned_report.md --csv results/finetuned_data.csv

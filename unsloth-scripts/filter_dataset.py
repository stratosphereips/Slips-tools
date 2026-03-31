#!/usr/bin/env python3
"""
Filter low-quality training examples and produce a 90/10 train/eval split.

Inputs:
  ../alert_summary/datasets/summarization_dataset_v3.json         (532 incidents, 4 responses each)
  ../alert_summary/datasets/summarization_dataset_v3_results_oss.json  (judge scores)

Outputs (written to unsloth-scripts/):
  filtered_train.json   — 90% split, each item has incident fields + scores attached
  filtered_eval.json    — 10% split

Filters applied per incident:
  1. Best score < 4  → reject (bottom quartile)
  2. Best response (summary field) token count < 50 or > 400  → reject
"""

import json
import sys
import os
from sklearn.model_selection import train_test_split

DATASET_PATH = os.path.join(os.path.dirname(__file__), "../alert_summary/datasets/summarization_dataset_v3.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "../alert_summary/datasets/summarization_dataset_v3_results_oss.json")
TRAIN_OUT = os.path.join(os.path.dirname(__file__), "filtered_train.json")
EVAL_OUT  = os.path.join(os.path.dirname(__file__), "filtered_eval.json")

# Map judge result model names → dataset field names
MODEL_NAME_TO_FIELD = {
    "GPT-4o-mini": "llm_gpt4o_mini_analysis",
    "GPT-4o":      "llm_gpt_4o_analysis",
    "Qwen2.5 3b":  "llm_qwen2_5:3b_analysis",
    "Qwen2.5":     "llm_qwen2_5_analysis",
}

MIN_TOKENS = 50
MAX_TOKENS = 400
MIN_SCORE  = 4


def approx_tokens(text: str) -> int:
    """Approximate token count by splitting on whitespace."""
    return len(text.split()) if text else 0


def get_best_model_and_score(scores: dict) -> tuple[str, int]:
    """Return (model_name, score) for the highest-scoring model."""
    return max(scores.items(), key=lambda x: x[1])


def load_and_index(path: str, key: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    return {item[key]: item for item in data}


def main():
    print("Loading datasets...")
    incidents = load_and_index(DATASET_PATH, "incident_id")
    results   = load_and_index(RESULTS_PATH, "incident_id")

    if len(incidents) != len(results):
        print(f"WARNING: incident count mismatch: {len(incidents)} vs {len(results)}", file=sys.stderr)

    kept = []
    rejected = {"low_score": 0, "token_length": 0, "missing": 0}

    for iid, result in results.items():
        if iid not in incidents:
            rejected["missing"] += 1
            continue

        incident = incidents[iid]
        scores = result["scores"]

        best_model, best_score = get_best_model_and_score(scores)

        # Filter 1: score threshold
        if best_score < MIN_SCORE:
            rejected["low_score"] += 1
            continue

        # Filter 2: token length of best response summary
        field = MODEL_NAME_TO_FIELD.get(best_model)
        if field is None:
            rejected["missing"] += 1
            continue

        response = incident.get(field, {})
        summary_text = response.get("summary", "") if isinstance(response, dict) else ""
        token_count = approx_tokens(summary_text)

        if token_count < MIN_TOKENS or token_count > MAX_TOKENS:
            rejected["token_length"] += 1
            continue

        # Merge incident + scores into one record
        merged = {**incident, "scores": scores}
        kept.append(merged)

    total = len(results)
    print(f"Total incidents:    {total}")
    print(f"Kept:               {len(kept)}")
    print(f"Rejected (score):   {rejected['low_score']}")
    print(f"Rejected (tokens):  {rejected['token_length']}")
    print(f"Rejected (missing): {rejected['missing']}")

    # 90/10 split
    train, eval_ = train_test_split(kept, test_size=0.1, random_state=42, shuffle=True)

    with open(TRAIN_OUT, "w") as f:
        json.dump(train, f, indent=2)
    with open(EVAL_OUT, "w") as f:
        json.dump(eval_, f, indent=2)

    print(f"\nOutput:")
    print(f"  Train: {len(train)} → {TRAIN_OUT}")
    print(f"  Eval:  {len(eval_)} → {EVAL_OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Filter low-quality training examples from the risk dataset and produce a 90/10 train/eval split.

Inputs:
  ../alert_summary/datasets/risk_dataset_v2.json                   (826 incidents, 4 responses each)
  ../alert_summary/datasets/risk_dataset_v2_results_qwen35.json    (judge scores)

Outputs (written to unsloth-scripts/):
  risk_filtered_train.json   — 90% split, each item has incident fields + scores attached
  risk_filtered_eval.json    — 10% split

Filters applied per incident:
  1. Best-of-N cause_scores.total < 14  → reject (bottom quartile; cause totals range ~7-24)
  2. Best-of-N risk_scores.total  < 10  → reject (bottom quartile; risk totals range ~8-18)
  3. cause_analysis token count < 50 or > 600  → reject
  4. risk_assessment token count < 30 or > 300  → reject
  5. risk_assessment missing risk level keyword (Critical/High/Medium/Low)  → reject

NOTE: dag_analysis is used as the training input (known mismatch with original prompt format,
see https://github.com/stratosphereips/Slips-tools/issues/24).
"""

import argparse
import json
import re
import sys
import os
from sklearn.model_selection import train_test_split

DEFAULT_DATASET_PATH = os.path.join(os.path.dirname(__file__), "../alert_summary/datasets/risk_dataset_v2.json")
DEFAULT_RESULTS_PATH = os.path.join(os.path.dirname(__file__), "../alert_summary/datasets/risk_dataset_v2_results_qwen35.json")
TRAIN_OUT = os.path.join(os.path.dirname(__file__), "risk_filtered_train.json")
EVAL_OUT  = os.path.join(os.path.dirname(__file__), "risk_filtered_eval.json")

# Map judge display names → dataset field names
MODEL_NAME_TO_FIELD = {
    "GPT-4o":      "cause_risk_gpt_4o",
    "GPT-4o-mini": "cause_risk_gpt_4o_mini",
    "Qwen2.5 3B":  "cause_risk_qwen2_5:3b",
    "Qwen2.5 1.5B": "cause_risk_qwen2_5",
}

DEFAULT_MIN_CAUSE_SCORE = 14
DEFAULT_MIN_RISK_SCORE  = 10
DEFAULT_MIN_CAUSE_TOKENS = 50
DEFAULT_MAX_CAUSE_TOKENS = 600
DEFAULT_MIN_RISK_TOKENS  = 30
DEFAULT_MAX_RISK_TOKENS  = 300

RISK_LEVEL_PATTERN = re.compile(r'\b(Critical|High|Medium|Low)\b', re.IGNORECASE)


def approx_tokens(text: str) -> int:
    return len(text.split()) if text else 0


def get_winner(result: dict) -> tuple[str, str] | None:
    """Return (display_name, dataset_field) for the rank-1 model."""
    rankings = result.get("rankings", {})
    winner_name = rankings.get("1")
    if not winner_name:
        return None
    field = MODEL_NAME_TO_FIELD.get(winner_name)
    if not field:
        return None
    return winner_name, field


def load_and_index(path: str, key: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    return {item[key]: item for item in data}


def parse_args():
    parser = argparse.ArgumentParser(description="Filter risk dataset and produce 90/10 train/eval split.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET_PATH)
    parser.add_argument("--results", default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--min-cause-score", type=int, default=DEFAULT_MIN_CAUSE_SCORE)
    parser.add_argument("--min-risk-score",  type=int, default=DEFAULT_MIN_RISK_SCORE)
    parser.add_argument("--min-cause-tokens", type=int, default=DEFAULT_MIN_CAUSE_TOKENS)
    parser.add_argument("--max-cause-tokens", type=int, default=DEFAULT_MAX_CAUSE_TOKENS)
    parser.add_argument("--min-risk-tokens",  type=int, default=DEFAULT_MIN_RISK_TOKENS)
    parser.add_argument("--max-risk-tokens",  type=int, default=DEFAULT_MAX_RISK_TOKENS)
    return parser.parse_args()


def main():
    args = parse_args()

    print("Input datasets:")
    print(f"  incidents: {os.path.abspath(args.dataset)}")
    print(f"  results:   {os.path.abspath(args.results)}")
    print(f"Output datasets:")
    print(f"  train: {os.path.abspath(TRAIN_OUT)}")
    print(f"  eval:  {os.path.abspath(EVAL_OUT)}")
    print()
    print("Loading datasets...")
    incidents = load_and_index(args.dataset, "incident_id")
    results   = load_and_index(args.results, "incident_id")

    if len(incidents) != len(results):
        print(f"WARNING: count mismatch: {len(incidents)} incidents vs {len(results)} results", file=sys.stderr)

    kept = []
    rejected = {"low_cause_score": 0, "low_risk_score": 0, "token_length": 0, "no_risk_level": 0, "missing": 0}

    for iid, result in results.items():
        if iid not in incidents:
            rejected["missing"] += 1
            continue

        incident = incidents[iid]

        winner = get_winner(result)
        if winner is None:
            rejected["missing"] += 1
            continue
        winner_name, field = winner

        cause_total = result["cause_scores"].get(winner_name, {}).get("total", 0)
        risk_total  = result["risk_scores"].get(winner_name, {}).get("total", 0)

        # Filter 1: cause score threshold
        if cause_total < args.min_cause_score:
            rejected["low_cause_score"] += 1
            continue

        # Filter 2: risk score threshold
        if risk_total < args.min_risk_score:
            rejected["low_risk_score"] += 1
            continue

        response = incident.get(field, {})
        cause_text = response.get("cause_analysis", "") if isinstance(response, dict) else ""
        risk_text  = response.get("risk_assessment", "") if isinstance(response, dict) else ""

        # Filter 3: token length
        cause_tokens = approx_tokens(cause_text)
        risk_tokens  = approx_tokens(risk_text)
        if (cause_tokens < args.min_cause_tokens or cause_tokens > args.max_cause_tokens or
                risk_tokens < args.min_risk_tokens or risk_tokens > args.max_risk_tokens):
            rejected["token_length"] += 1
            continue

        # Filter 4: risk level keyword
        if not RISK_LEVEL_PATTERN.search(risk_text):
            rejected["no_risk_level"] += 1
            continue

        merged = {
            **incident,
            "cause_scores": result["cause_scores"],
            "risk_scores":  result["risk_scores"],
            "rankings":     result["rankings"],
            "winner_name":  winner_name,
            "winner_field": field,
        }
        kept.append(merged)

    total = len(results)
    print(f"Total incidents:          {total}")
    print(f"Kept:                     {len(kept)}")
    print(f"Rejected (cause score):   {rejected['low_cause_score']}")
    print(f"Rejected (risk score):    {rejected['low_risk_score']}")
    print(f"Rejected (token length):  {rejected['token_length']}")
    print(f"Rejected (no risk level): {rejected['no_risk_level']}")
    print(f"Rejected (missing):       {rejected['missing']}")

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

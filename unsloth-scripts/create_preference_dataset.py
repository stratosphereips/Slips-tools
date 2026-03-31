#!/usr/bin/env python3
"""
Build DPO/ORPO preference datasets from filtered incident splits.

Inputs (from unsloth-scripts/):
  filtered_train.json  — training split with all 4 responses + scores per incident
  filtered_eval.json   — eval split, same format

Outputs (written to unsloth-scripts/):
  dpo_train_dataset.json
  dpo_eval_dataset.json

Per incident:
  - chosen:   response with highest score
  - rejected: response with lowest score
  If chosen model == rejected model (degenerate), the incident is skipped.
"""

import json
import os

FILTERED_TRAIN = os.path.join(os.path.dirname(__file__), "filtered_train.json")
FILTERED_EVAL  = os.path.join(os.path.dirname(__file__), "filtered_eval.json")
DPO_TRAIN_OUT  = os.path.join(os.path.dirname(__file__), "dpo_train_dataset.json")
DPO_EVAL_OUT   = os.path.join(os.path.dirname(__file__), "dpo_eval_dataset.json")

MODEL_NAME_TO_FIELD = {
    "GPT-4o-mini": "llm_gpt4o_mini_analysis",
    "GPT-4o":      "llm_gpt_4o_analysis",
    "Qwen2.5 3b":  "llm_qwen2_5:3b_analysis",
    "Qwen2.5":     "llm_qwen2_5_analysis",
}

SYSTEM_PROMPT = (
    "You are a security analyst. Your task is to translate technical security events "
    "into clear, concise, human-readable summaries and assess their severity."
)


def get_best_model(scores: dict) -> tuple[str, int]:
    return max(scores.items(), key=lambda x: x[1])


def get_worst_model(scores: dict) -> tuple[str, int]:
    return min(scores.items(), key=lambda x: x[1])


def get_summary(incident: dict, model_name: str) -> str:
    field = MODEL_NAME_TO_FIELD.get(model_name)
    if field is None:
        return ""
    response = incident.get(field, {})
    return response.get("summary", "") if isinstance(response, dict) else ""


def build_dpo_record(incident: dict) -> dict | None:
    scores = incident.get("scores", {})
    if not scores:
        return None

    chosen_model, chosen_score   = get_best_model(scores)
    rejected_model, rejected_score = get_worst_model(scores)

    # Degenerate case: same model is both best and worst
    if chosen_model == rejected_model:
        return None

    chosen_text   = get_summary(incident, chosen_model)
    rejected_text = get_summary(incident, rejected_model)

    if not chosen_text or not rejected_text:
        return None

    dag_analysis = incident.get("dag_analysis", "")

    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": dag_analysis},
        ],
        "chosen": [
            {"role": "assistant", "content": chosen_text},
        ],
        "rejected": [
            {"role": "assistant", "content": rejected_text},
        ],
        "incident_id":    incident.get("incident_id"),
        "chosen_model":   chosen_model,
        "chosen_score":   chosen_score,
        "rejected_model": rejected_model,
        "rejected_score": rejected_score,
    }


def process_split(input_path: str, output_path: str, split_name: str):
    with open(input_path) as f:
        incidents = json.load(f)

    records = []
    skipped = 0
    chosen_counts:   dict[str, int] = {}
    rejected_counts: dict[str, int] = {}

    for incident in incidents:
        record = build_dpo_record(incident)
        if record is None:
            skipped += 1
            continue
        records.append(record)
        chosen_counts[record["chosen_model"]]   = chosen_counts.get(record["chosen_model"], 0) + 1
        rejected_counts[record["rejected_model"]] = rejected_counts.get(record["rejected_model"], 0) + 1

    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"{split_name}: {len(records)} records ({skipped} skipped) → {output_path}")
    print(f"  Chosen model distribution:")
    for model, count in sorted(chosen_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(records) if records else 0
        print(f"    {model}: {count} ({pct:.1f}%)")
    print(f"  Rejected model distribution:")
    for model, count in sorted(rejected_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(records) if records else 0
        print(f"    {model}: {count} ({pct:.1f}%)")


def main():
    print("Building DPO preference datasets from filtered splits...\n")
    process_split(FILTERED_TRAIN, DPO_TRAIN_OUT, "Train")
    print()
    process_split(FILTERED_EVAL,  DPO_EVAL_OUT,  "Eval")


if __name__ == "__main__":
    main()

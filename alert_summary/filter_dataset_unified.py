#!/usr/bin/env python3
"""
Step 3: Filter the unified dataset and produce train/eval splits.

Filtering matches the criteria used in the separate summarization and risk pipelines:

  Summary task:
    - Best summary score >= 4  (out of 10)
    - Summary response token length: 50–400

  Cause task:
    - Best cause total >= 14  (out of 30)
    - Cause response token length: 50–600

  Risk task:
    - Best risk total >= 10  (out of 30)
    - Risk response token length: 30–300
    - Risk assessment must contain a severity keyword (Critical/High/Medium/Low)

  Split: 90/10 train/eval, seed=42

Output:
  datasets/unified_filtered_train.json   (90%)
  datasets/unified_filtered_eval.json    (10%)
"""

import json
import os
import random
import re

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")

INPUT_PATH  = os.path.join(DATASETS_DIR, "unified_dataset.json")
TRAIN_PATH  = os.path.join(DATASETS_DIR, "unified_filtered_train.json")
EVAL_PATH   = os.path.join(DATASETS_DIR, "unified_filtered_eval.json")

# ── Thresholds (matching separate pipelines) ──────────────────────────────────
MIN_SUMMARY_SCORE = 4   # out of 10
MIN_CAUSE_TOTAL   = 14  # out of 30
MIN_RISK_TOTAL    = 10  # out of 30

MIN_SUMMARY_TOKENS = 50;  MAX_SUMMARY_TOKENS = 400
MIN_CAUSE_TOKENS   = 50;  MAX_CAUSE_TOKENS   = 600
MIN_RISK_TOKENS    = 30;  MAX_RISK_TOKENS    = 300

SEVERITY_KEYWORDS = re.compile(r'\b(Critical|High|Medium|Low)\b', re.IGNORECASE)

SEED = 42
EVAL_FRACTION = 0.10

# ── Score key → response field mappings ──────────────────────────────────────
SUMMARY_KEY_TO_FIELD = {
    "GPT-4o":      "llm_gpt_4o_analysis",
    "GPT-4o-mini": "llm_gpt4o_mini_analysis",
    "Qwen2.5":     "llm_qwen2_5_analysis",
    "Qwen2.5 3b":  "llm_qwen2_5:3b_analysis",
}

RISK_KEY_TO_FIELD = {
    "GPT-4o":      "cause_risk_gpt_4o",
    "GPT-4o-mini": "cause_risk_gpt_4o_mini",
    "Qwen2.5":     "cause_risk_qwen2_5",
    "Qwen2.5 3B":  "cause_risk_qwen2_5:3b",
}


def approx_tokens(text: str) -> int:
    return len(text) // 4 if text else 0


def get_summary_text(rec: dict, field: str) -> str:
    val = rec.get(field)
    if isinstance(val, dict):
        return val.get("summary", "")
    return val or ""


def get_cause_text(rec: dict, field: str) -> str:
    val = rec.get(field)
    if isinstance(val, dict):
        return val.get("cause_analysis", "")
    return val or ""


def get_risk_text(rec: dict, field: str) -> str:
    val = rec.get(field)
    if isinstance(val, dict):
        return val.get("risk_assessment", "")
    return val or ""


def best_summary_score(record: dict) -> tuple[int, str]:
    scores = record.get("summary_scores", {})
    if not scores:
        return 0, ""
    best_key = max(scores, key=lambda k: scores[k])
    return scores[best_key], best_key


def best_cause_total(record: dict) -> tuple[int, str]:
    cause_scores = record.get("risk_cause_scores", {})
    if not cause_scores:
        return 0, ""
    best_key = max(cause_scores, key=lambda k: cause_scores[k].get("total", 0))
    return cause_scores[best_key].get("total", 0), best_key


def best_risk_total(record: dict) -> tuple[int, str]:
    risk_scores = record.get("risk_risk_scores", {})
    if not risk_scores:
        return 0, ""
    best_key = max(risk_scores, key=lambda k: risk_scores[k].get("total", 0))
    return risk_scores[best_key].get("total", 0), best_key


def passes_summary_tokens(record: dict) -> bool:
    """At least one summary response must be within token bounds."""
    return any(
        MIN_SUMMARY_TOKENS <= approx_tokens(get_summary_text(record, f)) <= MAX_SUMMARY_TOKENS
        for f in SUMMARY_KEY_TO_FIELD.values()
    )


def passes_cause_tokens(record: dict) -> bool:
    """At least one cause response must be within token bounds."""
    return any(
        MIN_CAUSE_TOKENS <= approx_tokens(get_cause_text(record, f)) <= MAX_CAUSE_TOKENS
        for f in RISK_KEY_TO_FIELD.values()
    )


def passes_risk_tokens(record: dict) -> bool:
    """At least one risk response must be within token bounds."""
    return any(
        MIN_RISK_TOKENS <= approx_tokens(get_risk_text(record, f)) <= MAX_RISK_TOKENS
        for f in RISK_KEY_TO_FIELD.values()
    )


def passes_severity_keyword(record: dict) -> bool:
    """At least one risk response must contain a severity keyword."""
    return any(
        bool(SEVERITY_KEYWORDS.search(get_risk_text(record, f)))
        for f in RISK_KEY_TO_FIELD.values()
    )


def main():
    print("Loading unified dataset...")
    with open(INPUT_PATH) as f:
        data = json.load(f)
    print(f"  Total records: {len(data)}")

    kept = []
    rejected = {
        "summary_score":    0,
        "cause_total":      0,
        "risk_total":       0,
        "summary_tokens":   0,
        "cause_tokens":     0,
        "risk_tokens":      0,
        "severity_keyword": 0,
    }

    for rec in data:
        sum_score, _  = best_summary_score(rec)
        cause_total, _ = best_cause_total(rec)
        risk_total, _  = best_risk_total(rec)

        if sum_score < MIN_SUMMARY_SCORE:
            rejected["summary_score"] += 1
            continue
        if cause_total < MIN_CAUSE_TOTAL:
            rejected["cause_total"] += 1
            continue
        if risk_total < MIN_RISK_TOTAL:
            rejected["risk_total"] += 1
            continue
        if not passes_summary_tokens(rec):
            rejected["summary_tokens"] += 1
            continue
        if not passes_cause_tokens(rec):
            rejected["cause_tokens"] += 1
            continue
        if not passes_risk_tokens(rec):
            rejected["risk_tokens"] += 1
            continue
        if not passes_severity_keyword(rec):
            rejected["severity_keyword"] += 1
            continue

        kept.append(rec)

    print(f"\nRejected:")
    for reason, count in rejected.items():
        print(f"  {reason:20s}: {count}")
    print(f"\nKept: {len(kept)} / {len(data)} ({len(kept)/len(data)*100:.1f}%)")

    if not kept:
        print("ERROR: no records passed — check thresholds")
        return

    # Shuffle and split
    rng = random.Random(SEED)
    rng.shuffle(kept)

    n_eval  = max(1, round(len(kept) * EVAL_FRACTION))
    train_set = kept[n_eval:]
    eval_set  = kept[:n_eval]

    print(f"\nSplit (seed={SEED}):")
    print(f"  train: {len(train_set)}")
    print(f"  eval:  {len(eval_set)}")

    from collections import Counter
    sum_scores   = [best_summary_score(r)[0] for r in kept]
    cause_totals = [best_cause_total(r)[0] for r in kept]
    risk_totals  = [best_risk_total(r)[0] for r in kept]
    cats = Counter(r["category"] for r in kept)

    print(f"\nSummary score stats (best per incident):")
    print(f"  min={min(sum_scores)}  max={max(sum_scores)}  avg={sum(sum_scores)/len(sum_scores):.2f}")
    print(f"Cause total stats:")
    print(f"  min={min(cause_totals)}  max={max(cause_totals)}  avg={sum(cause_totals)/len(cause_totals):.2f}")
    print(f"Risk total stats:")
    print(f"  min={min(risk_totals)}  max={max(risk_totals)}  avg={sum(risk_totals)/len(risk_totals):.2f}")
    print(f"\nCategories: {dict(cats)}")

    with open(TRAIN_PATH, "w") as f:
        json.dump(train_set, f, indent=2)
    print(f"\nWritten: {TRAIN_PATH}")

    with open(EVAL_PATH, "w") as f:
        json.dump(eval_set, f, indent=2)
    print(f"Written: {EVAL_PATH}")


if __name__ == "__main__":
    main()

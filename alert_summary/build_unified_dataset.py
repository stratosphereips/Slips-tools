#!/usr/bin/env python3
"""
Step 2: Build the unified dataset by joining summarization_dataset_v4 and
risk_dataset_v2 on incident_id, keeping only the 802 incidents that have
judge scores on both tasks. dag_analysis is taken from risk_dataset_v2
(which has it for all 826 records) to ensure full coverage.

Inputs:
  datasets/summarization_dataset_v4.json          (961 incidents, summary LLM responses)
  datasets/risk_dataset_v2.json                   (826 incidents, risk LLM responses + dag_analysis)
  datasets/summarization_results_merged.json      (802 summary judge scores)
  datasets/risk_dataset_v2_results_qwen35.json    (826 risk judge scores)

Output:
  datasets/unified_dataset.json                   (802 incidents, all fields merged)
"""

import json
import os
from collections import Counter

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")

V4_PATH          = os.path.join(DATASETS_DIR, "summarization_dataset_v4.json")
RISK_V2_PATH     = os.path.join(DATASETS_DIR, "risk_dataset_v2.json")
SUM_RESULTS_PATH = os.path.join(DATASETS_DIR, "summarization_results_merged.json")
RISK_RESULTS_PATH= os.path.join(DATASETS_DIR, "risk_dataset_v2_results_qwen35.json")
OUTPUT_PATH      = os.path.join(DATASETS_DIR, "unified_dataset.json")


def main():
    print("Loading datasets...")
    with open(V4_PATH) as f:
        v4 = json.load(f)
    with open(RISK_V2_PATH) as f:
        risk_v2 = json.load(f)
    with open(SUM_RESULTS_PATH) as f:
        sum_results = json.load(f)
    with open(RISK_RESULTS_PATH) as f:
        risk_results = json.load(f)

    print(f"  v4 summary incidents:    {len(v4)}")
    print(f"  risk_v2 incidents:       {len(risk_v2)}")
    print(f"  summary judge results:   {len(sum_results)}")
    print(f"  risk judge results:      {len(risk_results)}")

    # Index all datasets by incident_id
    v4_by_id          = {r["incident_id"]: r for r in v4}
    risk_by_id        = {r["incident_id"]: r for r in risk_v2}
    sum_results_by_id = {r["incident_id"]: r for r in sum_results}
    risk_results_by_id= {r["incident_id"]: r for r in risk_results}

    # Target: incidents scored on both tasks
    target_ids = set(sum_results_by_id.keys()) & set(risk_results_by_id.keys())
    print(f"\nTarget incidents (scored on both tasks): {len(target_ids)}")

    merged = []
    skipped = {"no_v4": 0, "no_risk": 0}

    for iid in sorted(target_ids):
        if iid not in v4_by_id:
            skipped["no_v4"] += 1
            continue
        if iid not in risk_by_id:
            skipped["no_risk"] += 1
            continue

        v4_rec   = v4_by_id[iid]
        risk_rec = risk_by_id[iid]
        sum_res  = sum_results_by_id[iid]
        risk_res = risk_results_by_id[iid]

        record = {
            # Identity fields
            "incident_id":  iid,
            "category":     v4_rec["category"],
            "source_ip":    v4_rec["source_ip"],
            "timewindow":   v4_rec["timewindow"],
            "timeline":     v4_rec["timeline"],
            "threat_level": v4_rec["threat_level"],
            "event_count":  v4_rec["event_count"],

            # DAG text — always from risk_v2 (has it for all 802)
            "dag_analysis": risk_rec["dag_analysis"],

            # Summary LLM responses (from v4)
            "llm_gpt_4o_analysis":      v4_rec.get("llm_gpt_4o_analysis"),
            "llm_gpt4o_mini_analysis":  v4_rec.get("llm_gpt4o_mini_analysis"),
            "llm_qwen2_5_analysis":     v4_rec.get("llm_qwen2_5_analysis"),
            "llm_qwen2_5:3b_analysis":  v4_rec.get("llm_qwen2_5:3b_analysis"),

            # Risk LLM responses (from risk_v2)
            "cause_risk_gpt_4o":        risk_rec.get("cause_risk_gpt_4o"),
            "cause_risk_gpt_4o_mini":   risk_rec.get("cause_risk_gpt_4o_mini"),
            "cause_risk_qwen2_5":       risk_rec.get("cause_risk_qwen2_5"),
            "cause_risk_qwen2_5:3b":    risk_rec.get("cause_risk_qwen2_5:3b"),

            # Summary judge results
            "summary_scores":      sum_res["scores"],
            "summary_rankings":    sum_res["rankings"],
            "summary_randomization": sum_res["randomization"],

            # Risk judge results
            "risk_scores":         risk_res.get("scores", {}),
            "risk_cause_scores":   risk_res.get("cause_scores", {}),
            "risk_risk_scores":    risk_res.get("risk_scores", {}),
            "risk_rankings":       risk_res.get("rankings", {}),
            "risk_randomization":  risk_res.get("randomization", {}),
        }
        merged.append(record)

    print(f"Skipped — not in v4:     {skipped['no_v4']}")
    print(f"Skipped — not in risk:   {skipped['no_risk']}")
    print(f"Merged records:          {len(merged)}")

    # Sanity checks
    assert len(merged) == len({r["incident_id"] for r in merged}), "Duplicate IDs!"

    missing_dag = sum(1 for r in merged if not r.get("dag_analysis"))
    missing_summary = sum(1 for r in merged
                          if not any(r.get(k) for k in
                                     ["llm_gpt_4o_analysis","llm_gpt4o_mini_analysis",
                                      "llm_qwen2_5_analysis","llm_qwen2_5:3b_analysis"]))
    missing_risk = sum(1 for r in merged
                       if not any(r.get(k) for k in
                                  ["cause_risk_gpt_4o","cause_risk_gpt_4o_mini",
                                   "cause_risk_qwen2_5","cause_risk_qwen2_5:3b"]))
    print(f"\nSanity checks:")
    print(f"  Missing dag_analysis:    {missing_dag}")
    print(f"  Missing summary LLM:     {missing_summary}")
    print(f"  Missing risk LLM:        {missing_risk}")

    # Stats
    cats = Counter(r["category"] for r in merged)
    sum_winners = Counter(r["summary_rankings"].get("1","?") for r in merged)
    risk_winners = Counter(r["risk_rankings"].get("1","?") for r in merged)

    print(f"\nCategories: {dict(cats)}")
    print(f"\nSummary win rates:")
    for model, count in sum_winners.most_common():
        print(f"  {model}: {count} ({count/len(merged)*100:.1f}%)")
    print(f"\nRisk win rates:")
    for model, count in risk_winners.most_common():
        print(f"  {model}: {count} ({count/len(merged)*100:.1f}%)")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"\nWritten to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

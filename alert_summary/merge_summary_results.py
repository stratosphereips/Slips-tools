#!/usr/bin/env python3
"""
Merge summarization judge results from v3 (532 incidents) and v4-new (270 incidents)
into a single unified results file (802 incidents).

Inputs:
  datasets/summarization_dataset_v3_results_oss.json   (532 records)
  datasets/summarization_v4_new_results_oss.json       (270 records)

Output:
  datasets/summarization_results_merged.json           (802 records)
"""

import json
import os
import sys

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")

V3_RESULTS  = os.path.join(DATASETS_DIR, "summarization_dataset_v3_results_oss.json")
V4_RESULTS  = os.path.join(DATASETS_DIR, "summarization_v4_new_results_oss.json")
OUTPUT      = os.path.join(DATASETS_DIR, "summarization_results_merged.json")


def main():
    print("Loading results files...")
    with open(V3_RESULTS) as f:
        v3 = json.load(f)
    with open(V4_RESULTS) as f:
        v4_new = json.load(f)

    print(f"  v3 results:     {len(v3)} records")
    print(f"  v4-new results: {len(v4_new)} records")

    # Check for duplicate incident IDs across the two files
    v3_ids    = {r["incident_id"] for r in v3}
    v4_new_ids = {r["incident_id"] for r in v4_new}
    overlap = v3_ids & v4_new_ids
    if overlap:
        print(f"  WARNING: {len(overlap)} duplicate incident IDs — v3 takes precedence")

    # Merge: v3 first, then v4-new skipping any duplicates
    merged = list(v3)
    skipped = 0
    for r in v4_new:
        if r["incident_id"] in v3_ids:
            skipped += 1
        else:
            merged.append(r)

    if skipped:
        print(f"  Skipped {skipped} duplicates from v4-new")

    print(f"\nMerged total: {len(merged)} records")

    # Sanity checks
    all_ids = [r["incident_id"] for r in merged]
    assert len(all_ids) == len(set(all_ids)), "Duplicate incident IDs in merged output!"

    # Verify score types are all numeric
    bad = [(r["incident_id"][:8], r["scores"]) for r in merged
           if not all(isinstance(v, (int, float)) for v in r["scores"].values())]
    if bad:
        print(f"  WARNING: {len(bad)} records with non-numeric scores")
        for iid, scores in bad[:3]:
            print(f"    {iid}: {scores}")
    else:
        print("  Score types: all numeric OK")

    # Stats
    from collections import Counter
    winners = Counter(r["rankings"]["1"] for r in merged)
    all_scores = [v for r in merged for v in r["scores"].values()]
    cats = Counter(r["category"] for r in merged)

    print(f"\nScore stats: min={min(all_scores)} max={max(all_scores)} "
          f"avg={sum(all_scores)/len(all_scores):.2f}")
    print(f"\nWin rates:")
    for model, count in winners.most_common():
        print(f"  {model}: {count} ({count/len(merged)*100:.1f}%)")
    print(f"\nCategories: {dict(cats)}")

    with open(OUTPUT, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"\nWritten to: {OUTPUT}")


if __name__ == "__main__":
    main()

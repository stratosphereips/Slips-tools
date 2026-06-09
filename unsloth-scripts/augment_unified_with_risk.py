#!/usr/bin/env python3
"""
Augment unified_train_dataset.json with cause+risk records from risk-only incidents
(incidents present in risk_filtered_train.json but not in unified_filtered_train.json).

This gives the unified model more risk training signal without touching the summary split.

Inputs:
  unified_train_dataset.json             — existing 2025-record unified SFT dataset
  risk_filtered_train.json               — standalone risk train split (664 incidents)
  ../alert_summary/datasets/unified_filtered_train.json — to get unified incident IDs

Output:
  unified_train_dataset_augmented.json   — unified dataset + extra cause+risk records
"""

import json
import os

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
ALERT_DIR     = os.path.join(SCRIPT_DIR, "..", "alert_summary")

UNIFIED_TRAIN_DATASET = os.path.join(SCRIPT_DIR, "unified_train_dataset.json")
RISK_FILTERED_TRAIN   = os.path.join(SCRIPT_DIR, ".attic", "datasets", "risk_filtered_train.json")
UNIFIED_FILTERED_TRAIN = os.path.join(ALERT_DIR, "datasets", "unified_filtered_train.json")
OUTPUT = os.path.join(SCRIPT_DIR, "unified_train_dataset_augmented.json")

DEFAULT_MAX_DAG_TOKENS = 3500


def build_cause_prompt(incident: dict, evidence_text: str) -> str:
    return f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured analysis of possible causes.

INCIDENT METADATA:
- Incident ID: {incident['incident_id']}
- Source IP: {incident.get('source_ip', 'Unknown')}
- Timewindow: {incident.get('timewindow', 'Unknown')}
- Accumulated Threat Level: {incident.get('threat_level', 'Unknown')}
- Time Range: {incident.get('timeline', 'Unknown')}
- Total Events: {incident.get('event_count', 'Unknown')}

SECURITY EVIDENCE:
{evidence_text}

Output Requirements:
- Respond with ONLY the analysis content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:

**Possible Causes:**

**1. Malicious Activity:**
• [Specific attack technique or malicious cause]
• [Additional malicious possibilities if relevant]

**2. Legitimate Activity:**
• [Benign operational cause]
• [Additional legitimate possibilities if relevant]

**3. Misconfigurations:**
• [Technical misconfigurations that could cause this behavior]

**Conclusion:** [1-2 sentence assessment of most likely cause category with recommendation for further investigation]

Guidelines:
- Be succinct (fewer words than raw evidence)
- Focus on relevant causes only (attack techniques, misconfigurations, legitimate operations)
- Use precise analyst-level language
- Maintain consistent structure and depth across all analyses
- Avoid generic definitions or unnecessary context
"""


def build_risk_prompt(incident: dict, evidence_text: str) -> str:
    return f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured risk assessment.

INCIDENT METADATA:
- Incident ID: {incident['incident_id']}
- Source IP: {incident.get('source_ip', 'Unknown')}
- Timewindow: {incident.get('timewindow', 'Unknown')}
- Accumulated Threat Level: {incident.get('threat_level', 'Unknown')}
- Time Range: {incident.get('timeline', 'Unknown')}
- Total Events: {incident.get('event_count', 'Unknown')}

SECURITY EVIDENCE:
{evidence_text}

Output Requirements:
- Respond with ONLY the assessment content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:

**Risk Level:** [Critical/High/Medium/Low]

**Justification:** [1-2 sentence technical justification for the risk level]

**Business Impact:** [Single clear sentence describing the most relevant business effect]

**Likelihood of Malicious Activity:** [High/Medium/Low] - [Brief rationale]

**Investigation Priority:** [Immediate/High/Medium/Low] - [Brief justification]

Guidelines:
- Use only the four risk levels: Critical, High, Medium, Low
- Keep justifications concise and technical
- Focus business impact on most relevant effect (data access, service disruption, etc.)
- Use consistent language for likelihood assessments
- Maintain uniform structure and depth across all assessments
- Avoid verbose or generic text
"""


def truncate_dag(dag: str, max_tokens: int) -> tuple[str, bool]:
    if not max_tokens or len(dag.split()) <= max_tokens:
        return dag, False
    lines = dag.splitlines(keepends=True)
    kept, count = [], 0
    for line in lines:
        line_tokens = len(line.split())
        if count + line_tokens > max_tokens:
            break
        kept.append(line)
        count += line_tokens
    truncated = "".join(kept).rstrip()
    truncated += f"\n[truncated: showing first ~{max_tokens} tokens of full DAG]"
    return truncated, True


def build_conversations(incident: dict, max_dag_tokens: int = DEFAULT_MAX_DAG_TOKENS):
    field = incident.get("winner_field")
    winner_name = incident.get("winner_name")
    if not field or not winner_name:
        return None, None

    response = incident.get(field, {})
    if not isinstance(response, dict):
        return None, None

    cause_text = response.get("cause_analysis", "")
    risk_text  = response.get("risk_assessment", "")
    if not cause_text or not risk_text:
        return None, None

    dag_analysis, truncated = truncate_dag(incident.get("dag_analysis", ""), max_dag_tokens)

    cause_record = {
        "messages": [
            {"role": "user",      "content": build_cause_prompt(incident, dag_analysis)},
            {"role": "assistant", "content": cause_text},
        ],
        "incident_id":   incident.get("incident_id"),
        "winner_model":  winner_name,
        "dag_truncated": truncated,
    }
    risk_record = {
        "messages": [
            {"role": "user",      "content": build_risk_prompt(incident, dag_analysis)},
            {"role": "assistant", "content": risk_text},
        ],
        "incident_id":   incident.get("incident_id"),
        "winner_model":  winner_name,
        "dag_truncated": truncated,
    }
    return cause_record, risk_record


def main():
    # Load unified train incident IDs
    unified_filtered = json.load(open(UNIFIED_FILTERED_TRAIN))
    unified_ids = {r["incident_id"] for r in unified_filtered}
    print(f"Unified train incidents:       {len(unified_ids)}")

    # Load risk-only incidents not in unified
    risk_filtered = json.load(open(RISK_FILTERED_TRAIN))
    risk_only = [r for r in risk_filtered if r["incident_id"] not in unified_ids]
    print(f"Risk-only extra incidents:     {len(risk_only)}")

    # Build cause+risk records for risk-only incidents
    cause_records, risk_records = [], []
    skipped, truncated_count = 0, 0
    model_counts: dict[str, int] = {}

    for incident in risk_only:
        cause_rec, risk_rec = build_conversations(incident)
        if cause_rec is None:
            skipped += 1
            continue
        cause_records.append(cause_rec)
        risk_records.append(risk_rec)
        model_counts[cause_rec["winner_model"]] = model_counts.get(cause_rec["winner_model"], 0) + 1
        if cause_rec["dag_truncated"]:
            truncated_count += 1

    print(f"Built {len(cause_records)} cause + {len(risk_records)} risk records ({skipped} skipped, {truncated_count} DAGs truncated)")
    print(f"  Winner distribution:")
    for model, count in sorted(model_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(cause_records) if cause_records else 0
        print(f"    {model}: {count} ({pct:.1f}%)")

    # Interleave cause+risk per incident
    extra_records = []
    for c, r in zip(cause_records, risk_records):
        extra_records.append(c)
        extra_records.append(r)

    # Load existing unified dataset and append
    unified_dataset = json.load(open(UNIFIED_TRAIN_DATASET))
    print(f"\nExisting unified dataset:      {len(unified_dataset)} records")

    augmented = unified_dataset + extra_records
    print(f"Extra risk records added:      {len(extra_records)}")
    print(f"Augmented dataset total:       {len(augmented)} records")

    json.dump(augmented, open(OUTPUT, "w"), indent=2)
    print(f"\nWritten to: {OUTPUT}")


if __name__ == "__main__":
    main()

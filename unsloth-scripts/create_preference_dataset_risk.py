#!/usr/bin/env python3
"""
Build DPO/ORPO preference datasets for cause analysis and risk assessment tasks.

Inputs (from unsloth-scripts/):
  risk_filtered_train.json
  risk_filtered_eval.json

Outputs (written to unsloth-scripts/):
  risk_dpo_cause_train_dataset.json
  risk_dpo_cause_eval_dataset.json
  risk_dpo_assessment_train_dataset.json
  risk_dpo_assessment_eval_dataset.json

Per incident:
  - chosen:   rank-1 model response
  - rejected: rank-4 model response (lowest ranked, typically Qwen2.5 3B — the target model)
  If chosen == rejected (degenerate), the incident is skipped.
"""

import json
import os

FILTERED_TRAIN = os.path.join(os.path.dirname(__file__), "risk_filtered_train.json")
FILTERED_EVAL  = os.path.join(os.path.dirname(__file__), "risk_filtered_eval.json")

DPO_CAUSE_TRAIN_OUT      = os.path.join(os.path.dirname(__file__), "risk_dpo_cause_train_dataset.json")
DPO_CAUSE_EVAL_OUT       = os.path.join(os.path.dirname(__file__), "risk_dpo_cause_eval_dataset.json")
DPO_ASSESSMENT_TRAIN_OUT = os.path.join(os.path.dirname(__file__), "risk_dpo_assessment_train_dataset.json")
DPO_ASSESSMENT_EVAL_OUT  = os.path.join(os.path.dirname(__file__), "risk_dpo_assessment_eval_dataset.json")

MODEL_NAME_TO_FIELD = {
    "GPT-4o":       "cause_risk_gpt_4o",
    "GPT-4o-mini":  "cause_risk_gpt_4o_mini",
    "Qwen2.5 3B":   "cause_risk_qwen2_5:3b",
    "Qwen2.5 1.5B": "cause_risk_qwen2_5",
}


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


def get_response(incident: dict, model_name: str) -> dict | None:
    field = MODEL_NAME_TO_FIELD.get(model_name)
    if not field:
        return None
    response = incident.get(field, {})
    return response if isinstance(response, dict) else None


def build_dpo_records(incident: dict) -> tuple[dict | None, dict | None]:
    """Build (cause_dpo_record, risk_dpo_record) for one incident."""
    rankings = incident.get("rankings", {})
    chosen_name   = rankings.get("1")
    rejected_name = rankings.get("4")

    if not chosen_name or not rejected_name or chosen_name == rejected_name:
        return None, None

    chosen_resp   = get_response(incident, chosen_name)
    rejected_resp = get_response(incident, rejected_name)

    if not chosen_resp or not rejected_resp:
        return None, None

    chosen_cause   = chosen_resp.get("cause_analysis", "")
    chosen_risk    = chosen_resp.get("risk_assessment", "")
    rejected_cause = rejected_resp.get("cause_analysis", "")
    rejected_risk  = rejected_resp.get("risk_assessment", "")

    if not all([chosen_cause, chosen_risk, rejected_cause, rejected_risk]):
        return None, None

    dag_analysis = incident.get("dag_analysis", "")

    cause_record = {
        "prompt": [
            {"role": "user", "content": build_cause_prompt(incident, dag_analysis)},
        ],
        "chosen": [
            {"role": "assistant", "content": chosen_cause},
        ],
        "rejected": [
            {"role": "assistant", "content": rejected_cause},
        ],
        "incident_id":    incident.get("incident_id"),
        "chosen_model":   chosen_name,
        "chosen_score":   incident.get("cause_scores", {}).get(chosen_name, {}).get("total"),
        "rejected_model": rejected_name,
        "rejected_score": incident.get("cause_scores", {}).get(rejected_name, {}).get("total"),
    }

    risk_record = {
        "prompt": [
            {"role": "user", "content": build_risk_prompt(incident, dag_analysis)},
        ],
        "chosen": [
            {"role": "assistant", "content": chosen_risk},
        ],
        "rejected": [
            {"role": "assistant", "content": rejected_risk},
        ],
        "incident_id":    incident.get("incident_id"),
        "chosen_model":   chosen_name,
        "chosen_score":   incident.get("risk_scores", {}).get(chosen_name, {}).get("total"),
        "rejected_model": rejected_name,
        "rejected_score": incident.get("risk_scores", {}).get(rejected_name, {}).get("total"),
    }

    return cause_record, risk_record


def process_split(input_path: str, cause_out: str, assessment_out: str, split_name: str):
    with open(input_path) as f:
        incidents = json.load(f)

    cause_records, risk_records = [], []
    skipped = 0
    chosen_counts:   dict[str, int] = {}
    rejected_counts: dict[str, int] = {}

    for incident in incidents:
        cause_rec, risk_rec = build_dpo_records(incident)
        if cause_rec is None:
            skipped += 1
            continue
        cause_records.append(cause_rec)
        risk_records.append(risk_rec)
        chosen_counts[cause_rec["chosen_model"]]     = chosen_counts.get(cause_rec["chosen_model"], 0) + 1
        rejected_counts[cause_rec["rejected_model"]] = rejected_counts.get(cause_rec["rejected_model"], 0) + 1

    with open(cause_out, "w") as f:
        json.dump(cause_records, f, indent=2)
    with open(assessment_out, "w") as f:
        json.dump(risk_records, f, indent=2)

    print(f"{split_name}: {len(cause_records)} records ({skipped} skipped)")
    print(f"  → cause DPO:      {cause_out}")
    print(f"  → assessment DPO: {assessment_out}")
    print(f"  Chosen model distribution:")
    for model, count in sorted(chosen_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(cause_records) if cause_records else 0
        print(f"    {model}: {count} ({pct:.1f}%)")
    print(f"  Rejected model distribution:")
    for model, count in sorted(rejected_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(cause_records) if cause_records else 0
        print(f"    {model}: {count} ({pct:.1f}%)")


def main():
    print("Input datasets:")
    print(f"  train: {os.path.abspath(FILTERED_TRAIN)}")
    print(f"  eval:  {os.path.abspath(FILTERED_EVAL)}")
    print("Output datasets:")
    print(f"  cause DPO train:      {os.path.abspath(DPO_CAUSE_TRAIN_OUT)}")
    print(f"  cause DPO eval:       {os.path.abspath(DPO_CAUSE_EVAL_OUT)}")
    print(f"  assessment DPO train: {os.path.abspath(DPO_ASSESSMENT_TRAIN_OUT)}")
    print(f"  assessment DPO eval:  {os.path.abspath(DPO_ASSESSMENT_EVAL_OUT)}")
    print()
    print("Building DPO preference datasets for risk pipeline...\n")
    process_split(FILTERED_TRAIN, DPO_CAUSE_TRAIN_OUT, DPO_ASSESSMENT_TRAIN_OUT, "Train")
    print()
    process_split(FILTERED_EVAL,  DPO_CAUSE_EVAL_OUT,  DPO_ASSESSMENT_EVAL_OUT,  "Eval")


if __name__ == "__main__":
    main()

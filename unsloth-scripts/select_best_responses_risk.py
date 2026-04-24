#!/usr/bin/env python3
"""
Select the highest-ranked model response per incident and build SFT-ready conversation records
for both cause analysis (Task A) and risk assessment (Task B).

Inputs (from unsloth-scripts/):
  risk_filtered_train.json
  risk_filtered_eval.json

Outputs (written to unsloth-scripts/):
  risk_cause_train_dataset.json        — Task A train split
  risk_cause_eval_dataset.json         — Task A eval split
  risk_assessment_train_dataset.json   — Task B train split
  risk_assessment_eval_dataset.json    — Task B eval split
  risk_combined_train_dataset.json     — Task A + B combined (used for training)
  risk_combined_eval_dataset.json      — Task A + B combined (used for eval)

Conversation format (no system message — matches original LLM call format):
  Task A: [{"role": "user", "content": "<cause prompt>"}, {"role": "assistant", "content": "<cause_analysis>"}]
  Task B: [{"role": "user", "content": "<risk prompt>"},  {"role": "assistant", "content": "<risk_assessment>"}]

The combined datasets interleave cause and risk records (cause_0, risk_0, cause_1, risk_1, ...)
so the model sees both task types throughout training rather than all of one then all of the other.

The user turn is built by inlining the prompt templates from alert_cause_risk_analyzer.py,
substituting dag_analysis as the evidence text.

NOTE: dag_analysis is used as evidence text (known mismatch with original grouped-events prompt,
see https://github.com/stratosphereips/Slips-tools/issues/24).
"""

import argparse
import json
import os

FILTERED_TRAIN = os.path.join(os.path.dirname(__file__), "risk_filtered_train.json")
FILTERED_EVAL  = os.path.join(os.path.dirname(__file__), "risk_filtered_eval.json")

CAUSE_TRAIN_OUT      = os.path.join(os.path.dirname(__file__), "risk_cause_train_dataset.json")
CAUSE_EVAL_OUT       = os.path.join(os.path.dirname(__file__), "risk_cause_eval_dataset.json")
ASSESSMENT_TRAIN_OUT = os.path.join(os.path.dirname(__file__), "risk_assessment_train_dataset.json")
ASSESSMENT_EVAL_OUT  = os.path.join(os.path.dirname(__file__), "risk_assessment_eval_dataset.json")
COMBINED_TRAIN_OUT   = os.path.join(os.path.dirname(__file__), "risk_combined_train_dataset.json")
COMBINED_EVAL_OUT    = os.path.join(os.path.dirname(__file__), "risk_combined_eval_dataset.json")

DEFAULT_MAX_DAG_TOKENS = 3500  # ~4096 max_seq_length - 183 prompt overhead - ~400 response tokens
                               # Set to 0 to disable truncation (not recommended: inputs up to 39k tokens exist)


def build_cause_prompt(incident: dict, evidence_text: str) -> str:
    """Inline of alert_cause_risk_analyzer._build_cause_prompt() using dag_analysis as evidence."""
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
    """Inline of alert_cause_risk_analyzer._build_risk_prompt() using dag_analysis as evidence."""
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


def build_conversations(incident: dict, max_dag_tokens: int = 0) -> tuple[dict | None, dict | None]:
    """Build cause and risk conversation records for one incident."""
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
        "cause_score":   incident.get("cause_scores", {}).get(winner_name, {}).get("total"),
        "dag_truncated": truncated,
    }

    risk_record = {
        "messages": [
            {"role": "user",      "content": build_risk_prompt(incident, dag_analysis)},
            {"role": "assistant", "content": risk_text},
        ],
        "incident_id":   incident.get("incident_id"),
        "winner_model":  winner_name,
        "risk_score":    incident.get("risk_scores", {}).get(winner_name, {}).get("total"),
        "dag_truncated": truncated,
    }

    return cause_record, risk_record


def interleave(cause_records: list, risk_records: list) -> list:
    """Interleave cause and risk records so both task types appear throughout training."""
    combined = []
    for c, r in zip(cause_records, risk_records):
        combined.append(c)
        combined.append(r)
    return combined


def process_split(input_path: str, cause_out: str, assessment_out: str, split_name: str,
                  max_dag_tokens: int = 0) -> tuple[list, list]:
    with open(input_path) as f:
        incidents = json.load(f)

    cause_records, risk_records = [], []
    skipped = 0
    truncated_count = 0
    model_counts: dict[str, int] = {}

    for incident in incidents:
        cause_rec, risk_rec = build_conversations(incident, max_dag_tokens=max_dag_tokens)
        if cause_rec is None:
            skipped += 1
            continue
        cause_records.append(cause_rec)
        risk_records.append(risk_rec)
        model_counts[cause_rec["winner_model"]] = model_counts.get(cause_rec["winner_model"], 0) + 1
        if cause_rec["dag_truncated"]:
            truncated_count += 1

    with open(cause_out, "w") as f:
        json.dump(cause_records, f, indent=2)
    with open(assessment_out, "w") as f:
        json.dump(risk_records, f, indent=2)

    print(f"{split_name}: {len(cause_records)} records ({skipped} skipped, {truncated_count} DAGs truncated)")
    print(f"  → cause:      {cause_out}")
    print(f"  → assessment: {assessment_out}")
    print(f"  Winner model distribution:")
    for model, count in sorted(model_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(cause_records) if cause_records else 0
        print(f"    {model}: {count} ({pct:.1f}%)")

    return cause_records, risk_records


def parse_args():
    parser = argparse.ArgumentParser(description="Select best model response per incident and build SFT risk datasets.")
    parser.add_argument("--max-dag-tokens", type=int, default=DEFAULT_MAX_DAG_TOKENS,
                        help="Truncate DAG input at this many tokens at a clean line boundary, "
                             "appending a truncation marker. Default: 3500 (~4096 seq_len minus "
                             "183 prompt overhead minus ~400 response tokens). Set to 0 to disable "
                             "— not recommended, inputs up to 39k tokens exist in this dataset.")
    return parser.parse_args()


def main():
    args = parse_args()
    print("Input datasets:")
    print(f"  train: {os.path.abspath(FILTERED_TRAIN)}")
    print(f"  eval:  {os.path.abspath(FILTERED_EVAL)}")
    print("Output datasets:")
    print(f"  cause train:      {os.path.abspath(CAUSE_TRAIN_OUT)}")
    print(f"  cause eval:       {os.path.abspath(CAUSE_EVAL_OUT)}")
    print(f"  assessment train: {os.path.abspath(ASSESSMENT_TRAIN_OUT)}")
    print(f"  assessment eval:  {os.path.abspath(ASSESSMENT_EVAL_OUT)}")
    print(f"  combined train:   {os.path.abspath(COMBINED_TRAIN_OUT)}")
    print(f"  combined eval:    {os.path.abspath(COMBINED_EVAL_OUT)}")
    print()
    if args.max_dag_tokens:
        print(f"DAG truncation enabled: max {args.max_dag_tokens} tokens per input\n")
    print("Building SFT risk conversation datasets from best-of-N selection...\n")

    cause_train, risk_train = process_split(
        FILTERED_TRAIN, CAUSE_TRAIN_OUT, ASSESSMENT_TRAIN_OUT, "Train", max_dag_tokens=args.max_dag_tokens)
    print()
    cause_eval, risk_eval = process_split(
        FILTERED_EVAL, CAUSE_EVAL_OUT, ASSESSMENT_EVAL_OUT, "Eval", max_dag_tokens=args.max_dag_tokens)

    # Combined interleaved datasets for single-adapter training
    combined_train = interleave(cause_train, risk_train)
    combined_eval  = interleave(cause_eval,  risk_eval)

    with open(COMBINED_TRAIN_OUT, "w") as f:
        json.dump(combined_train, f, indent=2)
    with open(COMBINED_EVAL_OUT, "w") as f:
        json.dump(combined_eval, f, indent=2)

    print()
    print(f"Combined (interleaved cause+risk):")
    print(f"  Train: {len(combined_train)} records → {COMBINED_TRAIN_OUT}")
    print(f"  Eval:  {len(combined_eval)} records → {COMBINED_EVAL_OUT}")


if __name__ == "__main__":
    main()

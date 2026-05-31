#!/usr/bin/env python3
"""
Step 4: Select the highest-scoring model response per incident per task and
build SFT-ready conversation records for all three tasks:
  - Task S: summarization
  - Task A: cause analysis
  - Task B: risk assessment

Best model selection:
  - Summary  → highest score in summary_scores  (flat 1-10)
  - Cause    → highest total in risk_cause_scores (subscored, max 30)
  - Risk     → highest total in risk_risk_scores  (subscored, max 30)
  Note: cause and risk share the same response field, so the same winner is
  used for both tasks (the model with the highest combined cause+risk score
  wins the risk record and the cause record separately is scored on cause alone).

Inputs:
  alert_summary/datasets/unified_filtered_train.json
  alert_summary/datasets/unified_filtered_eval.json

Outputs (in unsloth-scripts/):
  unified_train_dataset.json   — all three tasks interleaved (S, A, B, S, A, B, ...)
  unified_eval_dataset.json

Conversation formats:
  Task S: [system, user(dag), assistant(summary)]       — matches select_best_responses.py
  Task A: [user(cause_prompt+dag), assistant(cause)]    — matches select_best_responses_risk.py
  Task B: [user(risk_prompt+dag),  assistant(risk)]     — matches select_best_responses_risk.py
"""

import argparse
import json
import os

DATASETS_DIR  = os.path.join(os.path.dirname(__file__), "datasets")
UNSLOTH_DIR   = os.path.join(os.path.dirname(__file__), "..", "unsloth-scripts")

FILTERED_TRAIN = os.path.join(DATASETS_DIR, "unified_filtered_train.json")
FILTERED_EVAL  = os.path.join(DATASETS_DIR, "unified_filtered_eval.json")
TRAIN_OUT      = os.path.join(UNSLOTH_DIR, "unified_train_dataset.json")
EVAL_OUT       = os.path.join(UNSLOTH_DIR, "unified_eval_dataset.json")

DEFAULT_MAX_DAG_TOKENS = 3500

# ── Field name mappings ───────────────────────────────────────────────────────
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

# ── System / user prompts (copied verbatim from separate scripts) ─────────────
SUMMARY_SYSTEM_PROMPT = """You are a security analyst. Your task is to translate technical security events into clear, concise, human-readable summaries and assess their severity.

YOUR TASK:
1. Transform the technical event descriptions into clear, readable summaries using plain language
2. Group identical or very similar events (e.g., 24 identical connections → one summary line)
3. Assess the severity of each event/group based on security impact:
   - CRITICAL: Active exploitation, data exfiltration, confirmed malware C2
   - HIGH: Scanning, suspicious connections, potential threats
   - MEDIUM: Anomalous but potentially benign behavior
   - LOW: Minor issues, likely false positives
   - INFO: Informational events, normal network behavior
4. Calculate the overall severity breakdown based on your assessments

OUTPUT FORMAT (match this structure exactly):

============================================================
Incident: <incident_id>
Source IP: <source_ip> | Timewindow: <timewindow>
Timeline: <start> to <end>
Threat Level: <threat_level> | Events: <count>

• HH:MM-HH:MM - [Your clear grouped summary] [YOUR_ASSESSED_SEVERITY]
• HH:MM - [Your clear summary] [YOUR_ASSESSED_SEVERITY]

Total Evidence: <count> events
Severity breakdown: [Your calculated breakdown, e.g., "High: 5, Medium: 3, Info: 2"]

EXAMPLES OF GOOD SUMMARIZATION WITH SEVERITY ASSESSMENT:
- "Connection on port 0 from 0.0.0.0:0 to 224.0.0.1:0" → "IGMP multicast traffic to group address [INFO]"
- "Detected a horizontal port scan to port 443/TCP. 50 unique dst IPs" → "Port scanning 50 hosts on HTTPS port [HIGH]"
- "Connection to known C2 server 185.29.135.234:443" → "Direct connection to command & control server [CRITICAL]"
- "Connection without DNS resolution to CDN IP" → "Direct IP connection (likely CDN/API) [LOW]"

RULES:
- Group identical events into ONE line (don't list the same event 24 times)
- Use time ranges (HH:MM-HH:MM) when showing grouped events
- Assess severity based on security impact, not just event type
- Use severity levels: CRITICAL, HIGH, MEDIUM, LOW, INFO
- Keep descriptions clear and concise
- Just output the structured summary - no explanations or meta-commentary
- Do not include token counts or performance statistics"""


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


# ── Helpers ───────────────────────────────────────────────────────────────────
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


def best_summary_model(incident: dict) -> tuple[str, int] | tuple[None, None]:
    scores = incident.get("summary_scores", {})
    if not scores:
        return None, None
    key = max(scores, key=lambda k: scores[k])
    return key, scores[key]


def best_risk_model(incident: dict) -> tuple[str, int] | tuple[None, None]:
    """Pick the model with highest cause total (cause and risk share the same response field)."""
    cause_scores = incident.get("risk_cause_scores", {})
    if not cause_scores:
        return None, None
    key = max(cause_scores, key=lambda k: cause_scores[k].get("total", 0))
    return key, cause_scores[key].get("total", 0)


def build_records(incident: dict, max_dag_tokens: int = 0) -> tuple[dict | None, dict | None, dict | None]:
    """Return (summary_record, cause_record, risk_record) or None per task on failure."""
    dag_raw = incident.get("dag_analysis", "")
    dag, truncated = truncate_dag(dag_raw, max_dag_tokens)

    # ── Task S: summary ───────────────────────────────────────────────────────
    sum_key, sum_score = best_summary_model(incident)
    sum_field = SUMMARY_KEY_TO_FIELD.get(sum_key) if sum_key else None
    sum_resp  = incident.get(sum_field, {}) if sum_field else {}
    sum_text  = sum_resp.get("summary", "") if isinstance(sum_resp, dict) else ""

    sum_record = None
    if sum_text:
        sum_record = {
            "messages": [
                {"role": "system",    "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user",      "content": dag},
                {"role": "assistant", "content": sum_text},
            ],
            "incident_id":   incident.get("incident_id"),
            "task":          "summary",
            "best_model":    sum_key,
            "best_score":    sum_score,
            "dag_truncated": truncated,
        }

    # ── Tasks A & B: cause + risk (same winning model) ────────────────────────
    risk_key, cause_total = best_risk_model(incident)
    risk_field = RISK_KEY_TO_FIELD.get(risk_key) if risk_key else None
    risk_resp  = incident.get(risk_field, {}) if risk_field else {}
    cause_text = risk_resp.get("cause_analysis", "") if isinstance(risk_resp, dict) else ""
    risk_text  = risk_resp.get("risk_assessment", "") if isinstance(risk_resp, dict) else ""

    cause_record = None
    if cause_text:
        risk_cause_total = incident.get("risk_cause_scores", {}).get(risk_key, {}).get("total") if risk_key else None
        cause_record = {
            "messages": [
                {"role": "user",      "content": build_cause_prompt(incident, dag)},
                {"role": "assistant", "content": cause_text},
            ],
            "incident_id":   incident.get("incident_id"),
            "task":          "cause",
            "best_model":    risk_key,
            "best_score":    risk_cause_total,
            "dag_truncated": truncated,
        }

    risk_record = None
    if risk_text:
        risk_risk_total = incident.get("risk_risk_scores", {}).get(risk_key, {}).get("total") if risk_key else None
        risk_record = {
            "messages": [
                {"role": "user",      "content": build_risk_prompt(incident, dag)},
                {"role": "assistant", "content": risk_text},
            ],
            "incident_id":   incident.get("incident_id"),
            "task":          "risk",
            "best_model":    risk_key,
            "best_score":    risk_risk_total,
            "dag_truncated": truncated,
        }

    return sum_record, cause_record, risk_record


def interleave(s_recs, a_recs, b_recs) -> list:
    """Interleave all three task types: S, A, B, S, A, B, ..."""
    combined = []
    for s, a, b in zip(s_recs, a_recs, b_recs):
        combined.append(s)
        combined.append(a)
        combined.append(b)
    return combined


def process_split(input_path: str, output_path: str, split_name: str, max_dag_tokens: int = 0):
    with open(input_path) as f:
        incidents = json.load(f)

    s_recs, a_recs, b_recs = [], [], []
    skipped = 0
    truncated_count = 0
    sum_model_counts: dict[str, int] = {}
    risk_model_counts: dict[str, int] = {}

    for incident in incidents:
        s, a, b = build_records(incident, max_dag_tokens=max_dag_tokens)
        if s is None or a is None or b is None:
            skipped += 1
            continue
        s_recs.append(s)
        a_recs.append(a)
        b_recs.append(b)
        sum_model_counts[s["best_model"]] = sum_model_counts.get(s["best_model"], 0) + 1
        risk_model_counts[a["best_model"]] = risk_model_counts.get(a["best_model"], 0) + 1
        if s["dag_truncated"]:
            truncated_count += 1

    combined = interleave(s_recs, a_recs, b_recs)

    with open(output_path, "w") as f:
        json.dump(combined, f, indent=2)

    n = len(s_recs)
    print(f"{split_name}: {n} incidents → {n * 3} records ({skipped} skipped, {truncated_count} DAGs truncated)")
    print(f"  → {output_path}")
    print(f"  Summary winner distribution:")
    for model, count in sorted(sum_model_counts.items(), key=lambda x: -x[1]):
        print(f"    {model}: {count} ({100*count/n:.1f}%)")
    print(f"  Cause/Risk winner distribution:")
    for model, count in sorted(risk_model_counts.items(), key=lambda x: -x[1]):
        print(f"    {model}: {count} ({100*count/n:.1f}%)")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Select best responses and build unified 3-task SFT dataset.")
    parser.add_argument("--max-dag-tokens", type=int, default=DEFAULT_MAX_DAG_TOKENS,
                        help="Truncate DAG at this many tokens (default: 3500). 0 = no limit.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.max_dag_tokens:
        print(f"DAG truncation: max {args.max_dag_tokens} tokens\n")
    print("Building unified 3-task SFT datasets...\n")
    process_split(FILTERED_TRAIN, TRAIN_OUT, "Train", max_dag_tokens=args.max_dag_tokens)
    print()
    process_split(FILTERED_EVAL,  EVAL_OUT,  "Eval",  max_dag_tokens=args.max_dag_tokens)


if __name__ == "__main__":
    main()

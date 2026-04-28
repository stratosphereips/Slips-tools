#!/usr/bin/env python3
"""
Select the highest-scoring model response per incident and build SFT-ready conversation records.

Inputs (from unsloth-scripts/):
  filtered_train.json
  filtered_eval.json

Outputs (written to unsloth-scripts/):
  train_dataset.json   — 90% split in conversation format for SFTTrainer
  eval_dataset.json    — 10% split

Conversation format:
  [
    {"role": "system",    "content": "<security analyst prompt>"},
    {"role": "user",      "content": "<dag_analysis text>"},
    {"role": "assistant", "content": "<best_response summary text>"}
  ]
"""

import argparse
import json
import os

FILTERED_TRAIN = os.path.join(os.path.dirname(__file__), "filtered_train.json")
FILTERED_EVAL  = os.path.join(os.path.dirname(__file__), "filtered_eval.json")
TRAIN_OUT      = os.path.join(os.path.dirname(__file__), "train_dataset.json")
EVAL_OUT       = os.path.join(os.path.dirname(__file__), "eval_dataset.json")

DEFAULT_MAX_DAG_TOKENS = 0  # 0 = no limit

MODEL_NAME_TO_FIELD = {
    "GPT-4o-mini": "llm_gpt4o_mini_analysis",
    "GPT-4o":      "llm_gpt_4o_analysis",
    "Qwen2.5 3b":  "llm_qwen2_5:3b_analysis",
    "Qwen2.5":     "llm_qwen2_5_analysis",
}

SYSTEM_PROMPT = """You are a security analyst. Your task is to translate technical security events into clear, concise, human-readable summaries and assess their severity.

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


def get_best_model(scores: dict) -> str:
    return max(scores.items(), key=lambda x: x[1])[0]


def truncate_dag(dag: str, max_tokens: int) -> tuple[str, bool]:
    """Truncate DAG text at a clean line boundary.

    Returns (truncated_text, was_truncated).
    Splits on newlines so events are never cut mid-sentence.
    """
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


def build_conversation(incident: dict, max_dag_tokens: int = 0) -> dict | None:
    scores = incident.get("scores", {})
    if not scores:
        return None

    best_model = get_best_model(scores)
    field = MODEL_NAME_TO_FIELD.get(best_model)
    if field is None:
        return None

    response = incident.get(field, {})
    summary = response.get("summary", "") if isinstance(response, dict) else ""
    if not summary:
        return None

    dag_analysis = incident.get("dag_analysis", "")
    dag_analysis, truncated = truncate_dag(dag_analysis, max_dag_tokens)

    record = {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": dag_analysis},
            {"role": "assistant", "content": summary},
        ],
        "incident_id":    incident.get("incident_id"),
        "best_model":     best_model,
        "best_score":     scores[best_model],
        "dag_truncated":  truncated,
    }
    return record


def process_split(input_path: str, output_path: str, split_name: str, max_dag_tokens: int = 0):
    with open(input_path) as f:
        incidents = json.load(f)

    records = []
    skipped = 0
    truncated_count = 0
    model_counts: dict[str, int] = {}

    for incident in incidents:
        record = build_conversation(incident, max_dag_tokens=max_dag_tokens)
        if record is None:
            skipped += 1
            continue
        records.append(record)
        model_counts[record["best_model"]] = model_counts.get(record["best_model"], 0) + 1
        if record["dag_truncated"]:
            truncated_count += 1

    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"{split_name}: {len(records)} records ({skipped} skipped, {truncated_count} DAGs truncated) → {output_path}")
    for model, count in sorted(model_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(records) if records else 0
        print(f"  {model}: {count} ({pct:.1f}%)")


def parse_args():
    parser = argparse.ArgumentParser(description="Select best model response per incident and build SFT conversation dataset.")
    parser.add_argument("--max-dag-tokens", type=int, default=DEFAULT_MAX_DAG_TOKENS,
                        help="Truncate DAG input at this many tokens at a clean line boundary, "
                             "appending a truncation marker. 0 = no limit (default).")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.max_dag_tokens:
        print(f"DAG truncation enabled: max {args.max_dag_tokens} tokens per input\n")
    print("Building SFT conversation datasets from best-of-N selection...\n")
    process_split(FILTERED_TRAIN, TRAIN_OUT, "Train", max_dag_tokens=args.max_dag_tokens)
    print()
    process_split(FILTERED_EVAL,  EVAL_OUT,  "Eval",  max_dag_tokens=args.max_dag_tokens)


if __name__ == "__main__":
    main()

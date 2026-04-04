#!/usr/bin/env python3
"""
Run inference on filtered_eval.json using the finetuned model via OpenAI-compatible API.
Produces finetuned_eval_results.json ready for evaluate_summaries.py.

Usage:
    # Start the model server first:
    #   python3 serve_model.py /path/to/model --device cuda
    #
    python3 run_finetuned_inference.py
    python3 run_finetuned_inference.py --input filtered_eval.json --output finetuned_eval_results.json
    python3 run_finetuned_inference.py --url http://localhost:8000/v1 --n 5
"""

import argparse
import json
from openai import OpenAI

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


def run_inference(dataset: list, client: OpenAI, model: str, max_tokens: int, temperature: float, output_path: str) -> list:
    results = []
    total = len(dataset)

    for i, entry in enumerate(dataset):
        incident_id = entry.get("incident_id", f"entry-{i}")
        print(f"[{i+1}/{total}] {incident_id} ... ", end="", flush=True)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": entry["dag_analysis"]},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            summary = response.choices[0].message.content.strip()
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            summary = f"ERROR: {e}"

        result = dict(entry)
        result["llm_finetuned_analysis"] = {
            "summary": summary,
            "behavior_analysis": "",
        }
        results.append(result)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run finetuned model inference on filtered_eval.json"
    )
    parser.add_argument("--input", default="filtered_eval.json")
    parser.add_argument("--output", default="finetuned_eval_results.json")
    parser.add_argument("--url", default="http://localhost:8000/v1")
    parser.add_argument("--model-name", default="finetuned")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature (0 = greedy/deterministic)")
    parser.add_argument("--n", type=int, default=0, help="Limit to first N entries (0 = all)")
    parser.add_argument("--max-input-tokens", type=int, default=2048, help="Skip entries with estimated input tokens above this limit (0 = no limit)")
    args = parser.parse_args()

    client = OpenAI(api_key="not-needed", base_url=args.url, timeout=300.0)

    print(f"Loading {args.input} ...")
    with open(args.input) as f:
        dataset = json.load(f)

    if args.n:
        dataset = dataset[:args.n]

    if args.max_input_tokens:
        before = len(dataset)
        dataset = [e for e in dataset if len(e["dag_analysis"].split()) * 1.3 <= args.max_input_tokens]
        print(f"Skipped {before - len(dataset)} entries exceeding {args.max_input_tokens} token limit")

    print(f"Running inference on {len(dataset)} entries via {args.url}\n")
    results = run_inference(dataset, client, args.model_name, args.max_tokens, args.temperature, args.output)

    print(f"\nSaved {len(results)} results to {args.output}")
    print(f"Next: python3 ../alert_summary/evaluate_summaries.py --input {args.output}")


if __name__ == "__main__":
    main()

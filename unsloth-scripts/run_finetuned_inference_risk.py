#!/usr/bin/env python3
"""
Run cause + risk inference on risk_filtered_eval.json using the finetuned model.
Produces risk_finetuned_eval_results.json ready for evaluate_risk.py.

Each incident gets two model calls:
  1. Cause analysis prompt  → cause_analysis
  2. Risk assessment prompt → risk_assessment

The output merges the finetuned responses into the original risk_dataset_v2.json
fields alongside the existing 4 model responses, adding a new field
'cause_risk_finetuned' so evaluate_risk.py can include it in the ranking.

Usage:
    python3 run_finetuned_inference_risk.py
    python3 run_finetuned_inference_risk.py --input risk_filtered_eval.json --output risk_finetuned_eval_results.json
    python3 run_finetuned_inference_risk.py --n 5   # test on first 5 entries
"""

import argparse
import json
import os
from openai import OpenAI

DEFAULT_INPUT  = os.path.join(os.path.dirname(__file__), "risk_filtered_eval.json")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "risk_finetuned_eval_results.json")
DEFAULT_URL    = "http://localhost:8000/v1"
DEFAULT_MODEL  = "finetuned"
DEFAULT_MAX_COMPLETION_TOKENS = 512
DEFAULT_MAX_INPUT_TOKENS = 4096


def build_cause_prompt(incident: dict) -> str:
    return f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured analysis of possible causes.

INCIDENT METADATA:
- Incident ID: {incident['incident_id']}
- Source IP: {incident.get('source_ip', 'Unknown')}
- Timewindow: {incident.get('timewindow', 'Unknown')}
- Accumulated Threat Level: {incident.get('threat_level', 'Unknown')}
- Time Range: {incident.get('timeline', 'Unknown')}
- Total Events: {incident.get('event_count', 'Unknown')}

SECURITY EVIDENCE:
{incident.get('dag_analysis', '')}

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


def build_risk_prompt(incident: dict) -> str:
    return f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured risk assessment.

INCIDENT METADATA:
- Incident ID: {incident['incident_id']}
- Source IP: {incident.get('source_ip', 'Unknown')}
- Timewindow: {incident.get('timewindow', 'Unknown')}
- Accumulated Threat Level: {incident.get('threat_level', 'Unknown')}
- Time Range: {incident.get('timeline', 'Unknown')}
- Total Events: {incident.get('event_count', 'Unknown')}

SECURITY EVIDENCE:
{incident.get('dag_analysis', '')}

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


def call_model(client: OpenAI, model: str, prompt: str, max_completion_tokens: int,
               temperature: float, repeat_penalty: float) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
        extra_body={"repeat_penalty": repeat_penalty} if repeat_penalty != 1.0 else {},
    )
    return response.choices[0].message.content.strip()


def run_inference(dataset: list, client: OpenAI, model: str, max_completion_tokens: int,
                  temperature: float, repeat_penalty: float, output_path: str) -> list:
    results = []
    total = len(dataset)

    for i, entry in enumerate(dataset):
        incident_id = entry.get("incident_id", f"entry-{i}")
        print(f"[{i+1}/{total}] {incident_id}")

        result = dict(entry)

        # Call 1: cause analysis
        print(f"  cause ...  ", end="", flush=True)
        try:
            cause_text = call_model(client, model, build_cause_prompt(entry),
                                    max_completion_tokens, temperature, repeat_penalty)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            cause_text = f"ERROR: {e}"

        # Call 2: risk assessment
        print(f"  risk  ...  ", end="", flush=True)
        try:
            risk_text = call_model(client, model, build_risk_prompt(entry),
                                   max_completion_tokens, temperature, repeat_penalty)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            risk_text = f"ERROR: {e}"

        result["cause_risk_finetuned"] = {
            "cause_analysis":  cause_text,
            "risk_assessment": risk_text,
        }
        results.append(result)

        # Write incrementally so progress is not lost on interruption
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run cause+risk inference on risk_filtered_eval.json using the finetuned model."
    )
    parser.add_argument("--input",  default=DEFAULT_INPUT,
                        help=f"Input eval dataset (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"Output results JSON (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--url",    default=DEFAULT_URL,
                        help=f"Model server base URL (default: {DEFAULT_URL})")
    parser.add_argument("--model-name", default=DEFAULT_MODEL,
                        help=f"Model alias registered in the server (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-completion-tokens", type=int, default=DEFAULT_MAX_COMPLETION_TOKENS,
                        help=f"Max tokens per completion (default: {DEFAULT_MAX_COMPLETION_TOKENS})")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Sampling temperature (default: 0.0 = greedy)")
    parser.add_argument("--repeat-penalty", type=float, default=1.0,
                        help="Repeat penalty for Ollama (1.0 = disabled)")
    parser.add_argument("--max-input-tokens", type=int, default=DEFAULT_MAX_INPUT_TOKENS,
                        help=f"Skip entries whose dag_analysis exceeds this token estimate (default: {DEFAULT_MAX_INPUT_TOKENS}, 0 = no limit)")
    parser.add_argument("--n", type=int, default=0,
                        help="Limit to first N entries for testing (0 = all)")
    args = parser.parse_args()

    print(f"Input:  {os.path.abspath(args.input)}")
    print(f"Output: {os.path.abspath(args.output)}")
    print(f"Server: {args.url}  model={args.model_name}")
    print()

    client = OpenAI(api_key="not-needed", base_url=args.url, timeout=300.0)

    with open(args.input) as f:
        dataset = json.load(f)

    if args.n:
        dataset = dataset[:args.n]

    if args.max_input_tokens:
        before = len(dataset)
        dataset = [e for e in dataset if len(e.get("dag_analysis", "").split()) * 1.3 <= args.max_input_tokens]
        skipped = before - len(dataset)
        if skipped:
            print(f"Skipped {skipped} entries exceeding {args.max_input_tokens} input token limit")

    print(f"Running inference on {len(dataset)} entries (2 calls each = {len(dataset)*2} total LLM calls)\n")
    results = run_inference(dataset, client, args.model_name, args.max_completion_tokens,
                            args.temperature, args.repeat_penalty, args.output)

    print(f"\nSaved {len(results)} results to {args.output}")
    print(f"Next: python3 ../alert_summary/evaluate_risk.py --input {args.output} --output ../alert_summary/results/risk_finetuned_results.json")


if __name__ == "__main__":
    main()

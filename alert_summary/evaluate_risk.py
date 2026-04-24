#!/usr/bin/env python3
"""
LLM-as-Judge Evaluation Script for Security Incident Risk Analysis
Uses GPT-4o as a cybersecurity risk analyst to rank different LLM outputs.
"""

import json
import os
import random
import time
from typing import List, Dict, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Model labels mapping (for randomization)
# 'cause_risk_finetuned' is only present when run_finetuned_inference_risk.py has been executed
MODEL_LABELS = {
    'cause_risk_gpt_4o': 'GPT-4o',
    'cause_risk_gpt_4o_mini': 'GPT-4o-mini',
    'cause_risk_qwen2_5': 'Qwen2.5 1.5B',
    'cause_risk_qwen2_5:3b': 'Qwen2.5 3B',
    'cause_risk_finetuned': 'Finetuned',
}

def load_evaluation_sample(filepath: str) -> List[Dict]:
    """Load the evaluation sample from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def truncate_dag(dag_analysis: str, max_chars: int = 6000) -> str:
    """Truncate DAG analysis to max_chars, cutting at a newline boundary."""
    if len(dag_analysis) <= max_chars:
        return dag_analysis
    truncated = dag_analysis[:max_chars].rsplit('\n', 1)[0]
    return truncated + f"\n... [truncated — showing first {max_chars} chars of {len(dag_analysis)} total]"


def _build_judge_prompt(
    dag_analysis: str,
    category: str,
    randomized_analyses: List[Tuple[str, str, str]],
    field: str,
) -> str:
    """Build a judge prompt for either 'cause' or 'risk' field."""
    n = len(randomized_analyses)
    label_str = ', '.join(s[0] for s in randomized_analyses)

    if field == 'cause':
        task_desc = "cause analyses"
        field_label = "Cause Analysis"
        criteria = """
- **Evidence Grounding**: Does it cite specific events from the DAG (IPs, ports, counts, timestamps)?
  - 1-3 = pure generalities, no specific data referenced
  - 4-6 = some specifics but incomplete or cherry-picked
  - 7-9 = systematically references key evidence (scan targets, blacklisted IPs, event counts)
  - 10 = covers all significant evidence with precise detail

- **Cause Specificity**: Does it name the specific attack behavior or stay vague?
  - 1-3 = "possible malicious activity" — could apply to any incident
  - 4-6 = names the attack class but not the specific behavior
  - 7-9 = identifies specific TTP (e.g. horizontal scan pattern, C2 callback behavior)
  - 10 = precise TTP with supporting evidence chain

- **Alternative Hypotheses**: Does it meaningfully consider legitimate/misconfiguration causes?
  - 1-3 = ignores or dismisses alternatives without reasoning
  - 4-6 = mentions alternatives but without supporting logic
  - 7-9 = evaluates alternatives against the evidence
  - 10 = well-reasoned evaluation of all plausible hypotheses"""
        dim_scores_example = {"evidence_grounding": "N", "cause_specificity": "N", "alternative_hypotheses": "N"}
        justification_guide = "- Evidence Grounding: which best uses specific DAG data?\\n- Cause Specificity: which identifies the most precise attack behavior?\\n- Alternative Hypotheses: which best evaluates legitimate/misconfiguration causes?"
    else:
        task_desc = "risk assessments"
        field_label = "Risk Assessment"
        criteria = """
- **Risk Calibration**: Is the risk level proportionate to the actual evidence weight?
  - 1-3 = flat assessment ignoring evidence distribution (e.g. always "High")
  - 4-6 = correct level but reasoning not tied to evidence
  - 7-9 = risk level explicitly derived from evidence severity and volume
  - 10 = nuanced calibration distinguishing between event types and their relative weight

- **Actionability**: Are recommended actions concrete and scoped to this incident?
  - 1-3 = generic boilerplate ("investigate the IP", "update firewall rules")
  - 4-6 = incident-specific but vague or unprioritized
  - 7-9 = concrete actions with priority order tied to specific findings
  - 10 = scoped response plan with clear sequencing and ownership

- **Business Impact Relevance**: Is the impact assessment realistic and specific?
  - 1-3 = generic ("data breach risk") — could apply to any incident
  - 4-6 = relevant but not tied to the specific evidence
  - 7-9 = impact explicitly derived from the observed behavior
  - 10 = precise impact with scope and affected assets identified"""
        dim_scores_example = {"risk_calibration": "N", "actionability": "N", "business_impact": "N"}
        justification_guide = "- Risk Calibration: which is best proportioned to the evidence?\\n- Actionability: which recommendations are most concrete and incident-specific?\\n- Business Impact: which best identifies the realistic impact?"

    rankings_example = {str(i+1): chr(ord('A')+i) for i in range(n)}
    scores_example = {chr(ord('A')+i): dict(dim_scores_example) for i in range(n)}

    prompt = f"""You are an experienced cybersecurity risk analyst. Evaluate {n} AI-generated {task_desc} of a security incident.

You will be shown:
1. The raw security event data (DAG analysis)
2. {n} different {task_desc} (labeled {label_str})
3. The incident category for context (Malware/Normal)

**Evaluation Criteria (score each 1-10):**
{criteria}

**Incident Category (for context):** "{category}"

---

## RAW SECURITY EVENT DATA (DAG Analysis)

{dag_analysis}

---

## {task_desc.upper()} TO EVALUATE

"""

    for label, model_name, content in randomized_analyses:
        text = content.get('cause_analysis' if field == 'cause' else 'risk_assessment', 'N/A')
        prompt += f"""
### {field_label} {label}

{text}

---
"""

    prompt += f"""

## YOUR EVALUATION TASK

Please provide your evaluation in the following JSON format:

```json
{{
  "rankings": {json.dumps(rankings_example)},
  "scores": {json.dumps(scores_example)},
  "justification": "For each dimension explain:\\n{justification_guide}"
}}
```

**Rankings**: Assign positions 1 (best) through {n} (worst) to {label_str}. Derive from total scores.
**Scores**: Rate each on each dimension using the 1-10 anchors above. Replace each "N" with an integer.
**Justification**: Explain the key differentiators per dimension.

Respond ONLY with valid JSON. No additional text before or after.
"""
    return prompt


def create_cause_prompt(incident: Dict, randomized_analyses: List[Tuple[str, str, str]], max_dag_chars: int = 6000) -> str:
    dag_analysis = truncate_dag(incident['dag_analysis'], max_dag_chars)
    return _build_judge_prompt(dag_analysis, incident['category'], randomized_analyses, 'cause')


def create_risk_prompt(incident: Dict, randomized_analyses: List[Tuple[str, str, str]], max_dag_chars: int = 6000) -> str:
    dag_analysis = truncate_dag(incident['dag_analysis'], max_dag_chars)
    return _build_judge_prompt(dag_analysis, incident['category'], randomized_analyses, 'risk')

def randomize_analyses(incident: Dict) -> Tuple[List[Tuple[str, str, str]], Dict[str, str]]:
    """
    Randomize the order of model outputs to avoid position bias.
    Only includes models that are present in the incident data.

    Args:
        incident: The incident data

    Returns:
        Tuple of (randomized analyses list, label_to_model mapping)
    """
    models = [k for k in MODEL_LABELS.keys() if k in incident]
    random.shuffle(models)

    labels = [chr(ord('A') + i) for i in range(len(models))]
    randomized = []
    label_to_model = {}

    for label, model_key in zip(labels, models):
        model_name = MODEL_LABELS[model_key]
        content = incident[model_key]
        randomized.append((label, model_name, content))
        label_to_model[label] = model_key

    return randomized, label_to_model

def call_judge_llm(prompt: str, client: OpenAI, model: str = "gpt-4o", max_retries: int = 3, timeout: int = 120) -> Dict:
    """
    Call the judge LLM to evaluate risk analyses, with retry on failure.

    Args:
        prompt: The evaluation prompt
        client: OpenAI client
        model: Model to use (default gpt-4o)
        max_retries: Number of retries on API or parse failure

    Returns:
        Parsed JSON response from judge
    """
    messages = [
        {
            "role": "system",
            "content": "You are an experienced cybersecurity risk analyst. Respond only with valid JSON."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    for attempt in range(1, max_retries + 1):
        try:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"},
                    timeout=timeout
                )
            except Exception:
                # Fall back for endpoints that don't support json_object response format
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    timeout=timeout
                )

            content = response.choices[0].message.content
            # Strip markdown code fences if present
            if content.strip().startswith("```"):
                content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(content)

            # Treat empty rankings/scores as a failure worth retrying
            if not result.get('rankings') or not result.get('scores'):
                raise ValueError(f"Judge returned empty rankings/scores")

            return result

        except Exception as e:
            print(f"  Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  All {max_retries} attempts failed, giving up.")
                raise

def evaluate_incident(
    incident: Dict,
    client: OpenAI,
    incident_num: int,
    total_incidents: int,
    judge_model: str = "gpt-4o",
    max_dag_chars: int = 6000
) -> Dict:
    """
    Evaluate a single incident with all model outputs.

    Args:
        incident: Incident data
        client: OpenAI client
        incident_num: Current incident number (for progress)
        total_incidents: Total incidents to evaluate
        judge_model: Model to use as judge

    Returns:
        Evaluation result dictionary
    """
    incident_id = incident['incident_id']
    category = incident['category']

    if 'dag_analysis' not in incident:
        raise ValueError(f"incident {incident_id[:8]} is missing 'dag_analysis' field — skipping")

    print(f"\n[{incident_num}/{total_incidents}] Evaluating incident {incident_id[:8]}... (Category: {category})")

    # Randomize analysis order to avoid bias (same order for both calls)
    randomized_analyses, label_to_model = randomize_analyses(incident)

    # --- Cause evaluation ---
    print(f"  Calling judge LLM (cause)...")
    cause_prompt = create_cause_prompt(incident, randomized_analyses, max_dag_chars=max_dag_chars)
    cause_response = call_judge_llm(cause_prompt, client, model=judge_model)

    # --- Risk evaluation ---
    print(f"  Calling judge LLM (risk)...")
    risk_prompt = create_risk_prompt(incident, randomized_analyses, max_dag_chars=max_dag_chars)
    risk_response = call_judge_llm(risk_prompt, client, model=judge_model)

    def parse_scores(response: Dict, label_to_model: Dict) -> Dict:
        """Convert label-based scores to model-name-based scores with totals."""
        model_scores = {}
        for label, dim_scores in response.get('scores', {}).items():
            model_key = label_to_model.get(label, 'unknown')
            model_name = MODEL_LABELS.get(model_key, 'unknown')
            if isinstance(dim_scores, dict):
                total = sum(v for v in dim_scores.values() if isinstance(v, (int, float)))
                model_scores[model_name] = {**dim_scores, 'total': total}
            elif isinstance(dim_scores, (int, float)):
                model_scores[model_name] = {'total': dim_scores}
            else:
                model_scores[model_name] = {'total': 0}
        return model_scores

    cause_scores = parse_scores(cause_response, label_to_model)
    risk_scores = parse_scores(risk_response, label_to_model)

    # Combine scores and derive final ranking
    combined = {}
    all_models = set(cause_scores) | set(risk_scores)
    for model_name in all_models:
        c_total = cause_scores.get(model_name, {}).get('total', 0)
        r_total = risk_scores.get(model_name, {}).get('total', 0)
        combined[model_name] = c_total + r_total

    sorted_models = sorted(combined, key=lambda m: combined[m], reverse=True)
    model_rankings = {str(i+1): m for i, m in enumerate(sorted_models)}

    result = {
        'incident_id': incident_id,
        'category': category,
        'event_count': incident['event_count'],
        'threat_level': incident['threat_level'],
        'randomization': label_to_model,
        'rankings': model_rankings,
        'cause_scores': cause_scores,
        'risk_scores': risk_scores,
        'cause_justification': cause_response.get('justification', ''),
        'risk_justification': risk_response.get('justification', ''),
    }

    print(f"  Rankings: 1st={model_rankings.get('1', 'N/A')}, 2nd={model_rankings.get('2', 'N/A')}")

    return result

def save_results(results: List[Dict], output_path: str):
    """Save evaluation results to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n{'='*60}")
    print(f"Saved evaluation results to: {output_path}")

def main():
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Evaluate LLM risk analyses using an LLM-as-judge (OpenAI-compatible API)')
    parser.add_argument('--input', '-i', default='datasets/risk_dataset.json',
                        help='Path to evaluation dataset JSON file (default: datasets/risk_dataset.json)')
    parser.add_argument('--output', '-o', default='results/risk_results.json',
                        help='Path to output results JSON file (default: results/risk_results.json)')
    parser.add_argument('--judge', '-j', default='gpt-4o',
                        help='Judge model to use (default: gpt-4o)')
    parser.add_argument('--base-url', default=None,
                        help='Base URL for OpenAI-compatible API (e.g. http://localhost:3000/api). '
                             'Defaults to official OpenAI endpoint.')
    parser.add_argument('--api-key', default=None,
                        help='API key for the endpoint. Falls back to OPENAI_API_KEY env var.')
    parser.add_argument('--limit', type=int, default=None,
                        help='Evaluate only the first N incidents (for testing).')
    parser.add_argument('--max-dag-chars', type=int, default=6000,
                        help='Truncate DAG analysis to this many characters in the prompt (default: 6000).')
    parser.add_argument('--entry', default=None,
                        help='Evaluate only the incident matching this incident_id (prefix match). '
                             'The output file is updated in-place: the existing result for this '
                             'entry is replaced, all others are kept unchanged.')

    args = parser.parse_args()

    # Configuration from arguments
    input_file = args.input
    output_file = args.output
    judge_model = args.judge
    api_key = args.api_key or os.getenv("OPENAI_API_KEY") or "no-key"
    base_url = args.base_url

    print(f"Input:    {input_file}")
    print(f"Output:   {output_file}")
    print(f"Judge:    {judge_model}")
    print(f"Base URL: {base_url or 'OpenAI default'}")

    # Create results directory if needed
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else "results", exist_ok=True)

    # Initialize OpenAI-compatible client
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    # Load evaluation dataset
    print("\nLoading evaluation dataset...")
    incidents = load_evaluation_sample(input_file)
    print(f"Loaded {len(incidents)} incidents")

    # Single-entry mode: evaluate one incident and patch the output file
    if args.entry:
        entry_id = args.entry
        matched = [inc for inc in incidents if inc['incident_id'].startswith(entry_id)]
        if not matched:
            print(f"ERROR: No incident found with id starting with '{entry_id}'")
            return
        if len(matched) > 1:
            print(f"ERROR: Ambiguous prefix '{entry_id}' matches {len(matched)} incidents. Use a longer prefix.")
            return
        incident = matched[0]

        # Load existing results if output file exists
        existing_results = []
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                existing_results = json.load(f)

        new_result = evaluate_incident(incident, client, 1, 1, judge_model=judge_model, max_dag_chars=args.max_dag_chars)

        # Replace existing entry or append
        replaced = False
        for idx, r in enumerate(existing_results):
            if r['incident_id'] == incident['incident_id']:
                existing_results[idx] = new_result
                replaced = True
                break
        if not replaced:
            existing_results.append(new_result)

        save_results(existing_results, output_file)
        print(f"  {'Replaced' if replaced else 'Appended'} entry for incident {incident['incident_id'][:8]}")
        return

    # Evaluate each incident
    if args.limit:
        incidents = incidents[:args.limit]
        print(f"Limiting to first {args.limit} incidents")

    print(f"\nStarting evaluation with {judge_model} as judge...")
    print("="*60)

    results = []
    for i, incident in enumerate(incidents, 1):
        try:
            result = evaluate_incident(incident, client, i, len(incidents), judge_model=judge_model, max_dag_chars=args.max_dag_chars)
            results.append(result)
            save_results(results, output_file)
            print(f"  Saved partial results ({len(results)}/{len(incidents)})")
        except Exception as e:
            print(f"  ERROR: Failed to evaluate incident: {e}")
            continue

    # Print summary
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print(f"Successfully evaluated: {len(results)}/{len(incidents)} incidents")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()

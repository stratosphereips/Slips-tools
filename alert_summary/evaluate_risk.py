#!/usr/bin/env python3
"""
LLM-as-Judge Evaluation Script for Security Incident Risk Analysis
Uses GPT-4o as a cybersecurity risk analyst to rank different LLM outputs.
"""

import json
import os
import random
from typing import List, Dict, Tuple
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Model labels mapping (for randomization)
MODEL_LABELS = {
    'cause_risk_gpt_4o': 'GPT-4o',
    'cause_risk_gpt_4o_mini': 'GPT-4o-mini',
    'cause_risk_qwen2_5': 'Qwen2.5',
    'cause_risk_qwen2_5:3b': 'Qwen2.5 3B'
}

def load_evaluation_sample(filepath: str) -> List[Dict]:
    """Load the evaluation sample from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def create_judge_prompt(
    incident: Dict,
    randomized_analyses: List[Tuple[str, str, str]]
) -> str:
    """
    Create the judge prompt for evaluation.

    Args:
        incident: The incident data including DAG analysis
        randomized_analyses: List of (label, model_name, cause+risk analysis) tuples

    Returns:
        Formatted prompt string
    """
    dag_analysis = incident['dag_analysis']
    category = incident['category']
    incident_id = incident['incident_id']

    n = len(randomized_analyses)
    label_str = ', '.join(s[0] for s in randomized_analyses)
    rank_str = ', '.join(str(i) for i in range(1, n + 1))

    prompt = f"""You are an experienced cybersecurity risk analyst. Your task is to evaluate {n} AI-generated risk analyses of security incidents based on your professional expertise.

You will be shown:
1. The raw security event data (DAG analysis)
2. {n} different AI-generated risk analyses (labeled {label_str})
3. The incident category for context (Malware/Normal)

Your job is to rank these analyses from best (1) to worst ({n}) based on which would be most useful for risk management and incident prioritization.

**Evaluation Criteria (score each 1-10):**

- **Evidence Grounding**: Does the analysis cite specific events from the DAG (IPs, ports, counts, timestamps)?
  - 1-3 = pure generalities, no specific data referenced
  - 4-6 = some specifics but incomplete or cherry-picked
  - 7-9 = systematically references key evidence (scan targets, blacklisted IPs, event counts)
  - 10 = covers all significant evidence with precise detail

- **Cause Specificity**: Does it name the specific attack behavior or stay vague?
  - 1-3 = "possible malicious activity" — could apply to any incident
  - 4-6 = names the attack class but not the specific behavior
  - 7-9 = identifies specific TTP (e.g. horizontal scan pattern, C2 callback behavior)
  - 10 = precise TTP with supporting evidence chain

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

**Incident Category (for context):** "{category}"

---

## RAW SECURITY EVENT DATA (DAG Analysis)

{dag_analysis}

---

## AI-GENERATED RISK ANALYSES TO EVALUATE

"""

    # Add each randomized analysis
    for label, model_name, content in randomized_analyses:
        # Split cause and risk analysis
        cause_text = content.get('cause_analysis', 'N/A')
        risk_text = content.get('risk_assessment', 'N/A')

        prompt += f"""
### Analysis {label}

**Cause Analysis:**
{cause_text}

**Risk Assessment:**
{risk_text}

---
"""

    rankings_example = {str(i+1): chr(ord('A')+i) for i in range(n)}
    dim_scores_example = {"evidence_grounding": "N", "cause_specificity": "N", "risk_calibration": "N", "actionability": "N"}
    scores_example = {chr(ord('A')+i): dim_scores_example for i in range(n)}
    prompt += f"""

## YOUR EVALUATION TASK

Please provide your evaluation in the following JSON format:

```json
{{
  "rankings": {json.dumps(rankings_example)},
  "scores": {json.dumps(scores_example)},
  "justification": "Your detailed explanation as a risk analyst. For each dimension explain:\\n- Evidence Grounding: which analysis best uses the specific DAG data?\\n- Cause Specificity: which identifies the most precise attack behavior?\\n- Risk Calibration: which risk assessment is best proportioned to the evidence?\\n- Actionability: which recommendations are most concrete and incident-specific?"
}}
```

**Rankings**: Assign positions 1 (best) through {n} (worst) to analyses {label_str}. Derive rankings from the total score across all dimensions.
**Scores**: Rate each analysis on each dimension using the 1-10 anchors above. Replace each "N" with an integer.
**Justification**: Explain the key differentiators per dimension across analyses.

Respond ONLY with valid JSON. No additional text before or after.
"""

    return prompt

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

    labels = ['A', 'B', 'C', 'D']
    randomized = []
    label_to_model = {}

    for label, model_key in zip(labels, models):
        model_name = MODEL_LABELS[model_key]
        content = incident[model_key]
        randomized.append((label, model_name, content))
        label_to_model[label] = model_key

    return randomized, label_to_model

def call_judge_llm(prompt: str, client: OpenAI, model: str = "gpt-4o") -> Dict:
    """
    Call the judge LLM to evaluate risk analyses.

    Args:
        prompt: The evaluation prompt
        client: OpenAI client
        model: Model to use (default gpt-4o)

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

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
    except Exception:
        # Fall back for endpoints that don't support json_object response format
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
        )

    content = response.choices[0].message.content
    # Strip markdown code fences if present
    if content.strip().startswith("```"):
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(content)
    except Exception as e:
        print(f"Error parsing judge response: {e}")
        raise

def evaluate_incident(
    incident: Dict,
    client: OpenAI,
    incident_num: int,
    total_incidents: int,
    judge_model: str = "gpt-4o"
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

    print(f"\n[{incident_num}/{total_incidents}] Evaluating incident {incident_id[:8]}... (Category: {category})")

    # Randomize analysis order to avoid bias
    randomized_analyses, label_to_model = randomize_analyses(incident)

    # Create judge prompt
    prompt = create_judge_prompt(incident, randomized_analyses)

    # Call judge LLM
    print(f"  Calling judge LLM...")
    judge_response = call_judge_llm(prompt, client, model=judge_model)

    # Map labels back to model names
    rankings = judge_response.get('rankings', {})
    scores = judge_response.get('scores', {})
    justification = judge_response.get('justification', '')

    # Convert label-based results to model-based results
    model_rankings = {}
    model_scores = {}

    for position, label in rankings.items():
        model_key = label_to_model.get(label, 'unknown')
        model_name = MODEL_LABELS.get(model_key, 'unknown')
        model_rankings[position] = model_name

    for label, dim_scores in scores.items():
        model_key = label_to_model.get(label, 'unknown')
        model_name = MODEL_LABELS.get(model_key, 'unknown')
        if isinstance(dim_scores, dict):
            total = sum(v for v in dim_scores.values() if isinstance(v, (int, float)))
            model_scores[model_name] = {**dim_scores, 'total': total}
        else:
            model_scores[model_name] = dim_scores

    result = {
        'incident_id': incident_id,
        'category': category,
        'event_count': incident['event_count'],
        'threat_level': incident['threat_level'],
        'randomization': label_to_model,  # Record which label mapped to which model
        'rankings': model_rankings,  # Position -> Model name
        'scores': model_scores,      # Model name -> Score
        'justification': justification
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

        new_result = evaluate_incident(incident, client, 1, 1, judge_model=judge_model)

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
    print(f"\nStarting evaluation with {judge_model} as judge...")
    print("="*60)

    results = []
    for i, incident in enumerate(incidents, 1):
        try:
            result = evaluate_incident(incident, client, i, len(incidents), judge_model=judge_model)
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

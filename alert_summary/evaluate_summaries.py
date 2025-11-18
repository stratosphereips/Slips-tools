#!/usr/bin/env python3
"""
LLM-as-Judge Evaluation Script for Security Incident Summaries
Uses GPT-4o as a network security analyst to rank different LLM outputs.
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
    'llm_gpt_4o_analysis': 'GPT-4o',
    'llm_gpt4o_mini_analysis': 'GPT-4o-mini',
    'llm_qwen2_5:15b_analysis': 'Qwen2.5 15B',
    'llm_qwen2_5_analysis': 'Qwen2.5'
}

def load_evaluation_sample(filepath: str) -> List[Dict]:
    """Load the evaluation sample from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def create_judge_prompt(
    incident: Dict,
    randomized_summaries: List[Tuple[str, str, str]]
) -> str:
    """
    Create the judge prompt for evaluation.

    Args:
        incident: The incident data including DAG analysis
        randomized_summaries: List of (label, model_name, summary+behavior) tuples

    Returns:
        Formatted prompt string
    """
    dag_analysis = incident['dag_analysis']
    category = incident['category']
    incident_id = incident['incident_id']

    prompt = f"""You are an experienced network security analyst conducting incident response. Your task is to evaluate 4 AI-generated security incident summaries based on your professional expertise.

You will be shown:
1. The raw security event data (DAG analysis)
2. Four different AI-generated summaries (labeled A, B, C, D)
3. The ground truth category (Malware/Normal)

Your job is to rank these summaries from best (1) to worst (4) based on which would be most useful for your incident response work.

**Evaluation Criteria:**
- **Accuracy**: Does it correctly identify threats from the evidence?
- **Completeness**: Are critical security events (HIGH/MEDIUM severity) covered?
- **Clarity**: Can you quickly understand what happened?
- **Actionability**: Does it help you decide on next steps?
- **Professional Quality**: Would you trust this in a security operations center?
- **Proper Severity Assessment**: Are threat levels appropriately categorized?

**Ground Truth:** This incident is categorized as "{category}"

---

## RAW SECURITY EVENT DATA (DAG Analysis)

{dag_analysis}

---

## AI-GENERATED SUMMARIES TO EVALUATE

"""

    # Add each randomized summary
    for label, model_name, content in randomized_summaries:
        # Split summary and behavior analysis
        summary_text = content.get('summary', 'N/A')
        behavior_text = content.get('behavior_analysis', 'N/A')

        prompt += f"""
### Summary {label}

**Summary:**
{summary_text}

**Behavior Analysis:**
{behavior_text}

---
"""

    prompt += """

## YOUR EVALUATION TASK

Please provide your evaluation in the following JSON format:

```json
{
  "rankings": {
    "1": "X",
    "2": "Y",
    "3": "Z",
    "4": "W"
  },
  "scores": {
    "A": N,
    "B": N,
    "C": N,
    "D": N
  },
  "justification": "Your detailed explanation as a security analyst. Explain:\n- Which summary best identifies the key threats?\n- Which provides the most actionable intelligence?\n- What critical details were missed or incorrect in lower-ranked summaries?\n- How well does each align with the ground truth category?"
}
```

**Rankings**: Assign positions 1 (best) through 4 (worst) to summaries A, B, C, D
**Scores**: Rate each summary on a 1-10 scale (10 = excellent, 1 = poor)
**Justification**: Provide your professional analysis explaining the rankings

Respond ONLY with valid JSON. No additional text before or after.
"""

    return prompt

def randomize_summaries(incident: Dict) -> Tuple[List[Tuple[str, str, str]], Dict[str, str]]:
    """
    Randomize the order of model outputs to avoid position bias.

    Args:
        incident: The incident data

    Returns:
        Tuple of (randomized summaries list, label_to_model mapping)
    """
    models = list(MODEL_LABELS.keys())
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
    Call the judge LLM (GPT-4o) to evaluate summaries.

    Args:
        prompt: The evaluation prompt
        client: OpenAI client
        model: Model to use (default gpt-4o)

    Returns:
        Parsed JSON response from judge
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an experienced network security analyst. Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent evaluation
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"Error calling judge LLM: {e}")
        raise

def evaluate_incident(
    incident: Dict,
    client: OpenAI,
    incident_num: int,
    total_incidents: int
) -> Dict:
    """
    Evaluate a single incident with all model outputs.

    Args:
        incident: Incident data
        client: OpenAI client
        incident_num: Current incident number (for progress)
        total_incidents: Total incidents to evaluate

    Returns:
        Evaluation result dictionary
    """
    incident_id = incident['incident_id']
    category = incident['category']

    print(f"\n[{incident_num}/{total_incidents}] Evaluating incident {incident_id[:8]}... (Category: {category})")

    # Randomize summary order to avoid bias
    randomized_summaries, label_to_model = randomize_summaries(incident)

    # Create judge prompt
    prompt = create_judge_prompt(incident, randomized_summaries)

    # Call judge LLM
    print(f"  Calling GPT-4o judge...")
    judge_response = call_judge_llm(prompt, client)

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

    for label, score in scores.items():
        model_key = label_to_model.get(label, 'unknown')
        model_name = MODEL_LABELS.get(model_key, 'unknown')
        model_scores[model_name] = score

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
    parser = argparse.ArgumentParser(description='Evaluate LLM summaries using GPT-4o as judge (network analyst)')
    parser.add_argument('--input', '-i', default='datasets/evaluation_sample.json',
                        help='Path to evaluation sample JSON file (default: datasets/evaluation_sample.json)')
    parser.add_argument('--output', '-o', default='results/evaluation_results.json',
                        help='Path to output results JSON file (default: results/evaluation_results.json)')
    parser.add_argument('--judge', '-j', default='gpt-4o',
                        help='Judge model to use (default: gpt-4o)')

    args = parser.parse_args()

    # Configuration from arguments
    input_file = args.input
    output_file = args.output
    judge_model = args.judge

    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print(f"Judge:  {judge_model}")

    # Create results directory if needed
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else "results", exist_ok=True)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY not found in environment")
        print("Please set it in .env file or export it")
        return

    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Load evaluation sample
    print("\nLoading evaluation sample...")
    incidents = load_evaluation_sample(input_file)
    print(f"Loaded {len(incidents)} incidents")

    # Evaluate each incident
    print(f"\nStarting evaluation with {judge_model} as judge...")
    print("="*60)

    results = []
    for i, incident in enumerate(incidents, 1):
        try:
            result = evaluate_incident(incident, client, i, len(incidents))
            results.append(result)
        except Exception as e:
            print(f"  ERROR: Failed to evaluate incident: {e}")
            # Continue with next incident
            continue

    # Save results
    save_results(results, output_file)

    # Print summary
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print(f"Successfully evaluated: {len(results)}/{len(incidents)} incidents")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()

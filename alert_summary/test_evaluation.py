#!/usr/bin/env python3
"""
Quick test of evaluation framework with a single incident.
Tests judge LLM integration without running full 50-sample evaluation.
"""

import json
import os
from evaluate_summaries import (
    load_evaluation_sample,
    randomize_summaries,
    create_judge_prompt,
    call_judge_llm
)
from openai import OpenAI
from dotenv import load_dotenv

def main():
    load_dotenv()

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found")
        print("Please set it in .env file or export it")
        return

    print("="*60)
    print("Testing Evaluation Framework")
    print("="*60)

    # Load sample
    print("\n1. Loading evaluation sample...")
    sample = load_evaluation_sample("datasets/evaluation_sample.json")
    print(f"   Loaded {len(sample)} incidents")

    # Select first incident
    incident = sample[0]
    print(f"\n2. Testing with incident: {incident['incident_id'][:8]}...")
    print(f"   Category: {incident['category']}")
    print(f"   Events: {incident['event_count']}")

    # Randomize summaries
    print("\n3. Randomizing summary order...")
    randomized, label_to_model = randomize_summaries(incident)
    print(f"   Order: {label_to_model}")

    # Create prompt
    print("\n4. Creating judge prompt...")
    prompt = create_judge_prompt(incident, randomized)
    print(f"   Prompt length: {len(prompt)} characters")

    # Call judge
    print("\n5. Calling GPT-4o judge...")
    print("   (This will cost ~$0.10)")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        result = call_judge_llm(prompt, client)
        print("\n6. Judge Response:")
        print("   " + "="*56)

        # Display rankings
        rankings = result.get('rankings', {})
        print("\n   Rankings:")
        for pos in ['1', '2', '3', '4']:
            label = rankings.get(pos, 'N/A')
            model = label_to_model.get(label, 'unknown')
            print(f"     {pos}. {label} -> {model}")

        # Display scores
        scores = result.get('scores', {})
        print("\n   Scores:")
        for label in ['A', 'B', 'C', 'D']:
            score = scores.get(label, 'N/A')
            model = label_to_model.get(label, 'unknown')
            print(f"     {label} ({model}): {score}/10")

        # Display justification
        justification = result.get('justification', '')
        print("\n   Justification:")
        print("   " + "-"*56)
        for line in justification.split('\n'):
            print(f"   {line}")

        print("\n" + "="*60)
        print("TEST SUCCESSFUL")
        print("="*60)
        print("\nThe evaluation framework is working correctly.")
        print("You can now run the full evaluation with:")
        print("  python3 evaluate_summaries.py")

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nTest failed. Please check:")
        print("  - API key is valid")
        print("  - OpenAI API is accessible")
        print("  - Network connection is working")
        return

if __name__ == "__main__":
    main()

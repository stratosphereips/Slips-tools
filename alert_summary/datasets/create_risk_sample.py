#!/usr/bin/env python3
"""
Create evaluation sample from risk analysis dataset.
Includes all Normal samples (maximum possible) and stratified Malware samples.
"""

import json
import random
from typing import List, Dict

def load_dataset(filepath: str) -> List[Dict]:
    """Load the full dataset from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def create_evaluation_sample(
    dataset: List[Dict],
    target_size: int = 50,
    random_seed: int = 42
) -> List[Dict]:
    """
    Create evaluation sample with maximum Normal samples and stratified Malware samples.

    Args:
        dataset: Full dataset
        target_size: Total number of samples (default 50)
        random_seed: Random seed for reproducibility

    Returns:
        List of sampled incidents
    """
    random.seed(random_seed)

    # Separate by category
    normal_samples = [item for item in dataset if item['category'] == 'Normal']
    malware_samples = [item for item in dataset if item['category'] == 'Malware']

    print(f"Total dataset size: {len(dataset)}")
    print(f"Normal samples available: {len(normal_samples)}")
    print(f"Malware samples available: {len(malware_samples)}")

    # Include ALL Normal samples
    selected_normal = normal_samples
    num_normal = len(selected_normal)

    # Calculate how many Malware samples we need
    num_malware_needed = target_size - num_normal

    if num_malware_needed <= 0:
        print(f"\nWarning: Target size ({target_size}) is less than available Normal samples ({num_normal})")
        return selected_normal[:target_size]

    print(f"\nSampling strategy:")
    print(f"  - Normal samples: {num_normal} (ALL available)")
    print(f"  - Malware samples: {num_malware_needed}")

    # Stratify Malware samples by event complexity
    # Define complexity tiers based on event_count
    malware_with_complexity = []
    for item in malware_samples:
        event_count = item['event_count']
        if event_count < 500:
            complexity = 'simple'
        elif event_count < 2000:
            complexity = 'medium'
        else:
            complexity = 'complex'
        malware_with_complexity.append((item, complexity))

    # Group by complexity
    complexity_groups = {
        'simple': [item for item, c in malware_with_complexity if c == 'simple'],
        'medium': [item for item, c in malware_with_complexity if c == 'medium'],
        'complex': [item for item, c in malware_with_complexity if c == 'complex']
    }

    print(f"\nMalware complexity distribution:")
    for complexity, items in complexity_groups.items():
        print(f"  - {complexity}: {len(items)} samples")

    # Stratified sampling from Malware
    # Try to maintain proportional representation across complexity levels
    selected_malware = []
    samples_per_tier = num_malware_needed // 3
    remainder = num_malware_needed % 3

    for i, (complexity, items) in enumerate(complexity_groups.items()):
        # Distribute remainder to first tiers
        tier_count = samples_per_tier + (1 if i < remainder else 0)

        if len(items) >= tier_count:
            selected = random.sample(items, tier_count)
        else:
            # If not enough in this tier, take all
            selected = items

        selected_malware.extend(selected)
        print(f"  - Selected {len(selected)} {complexity} samples")

    # If we still don't have enough (due to small tiers), randomly sample from all
    if len(selected_malware) < num_malware_needed:
        remaining_needed = num_malware_needed - len(selected_malware)
        remaining_pool = [m for m in malware_samples if m not in selected_malware]
        additional = random.sample(remaining_pool, min(remaining_needed, len(remaining_pool)))
        selected_malware.extend(additional)
        print(f"  - Added {len(additional)} additional samples from remaining pool")

    # Combine and shuffle
    evaluation_sample = selected_normal + selected_malware
    random.shuffle(evaluation_sample)

    print(f"\nFinal sample composition:")
    print(f"  - Total: {len(evaluation_sample)} samples")
    print(f"  - Normal: {len([s for s in evaluation_sample if s['category'] == 'Normal'])} ({len([s for s in evaluation_sample if s['category'] == 'Normal'])/len(evaluation_sample)*100:.1f}%)")
    print(f"  - Malware: {len([s for s in evaluation_sample if s['category'] == 'Malware'])} ({len([s for s in evaluation_sample if s['category'] == 'Malware'])/len(evaluation_sample)*100:.1f}%)")

    return evaluation_sample

def save_sample(sample: List[Dict], output_path: str):
    """Save evaluation sample to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(sample, f, indent=2)
    print(f"\nSaved evaluation sample to: {output_path}")

def main():
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Create evaluation sample from risk analysis dataset')
    parser.add_argument('--input', '-i', default='datasets/risk_dataset.json',
                        help='Path to input dataset JSON file (default: datasets/risk_dataset.json)')
    parser.add_argument('--output', '-o', default='datasets/risk_sample.json',
                        help='Path to output sample JSON file (default: datasets/risk_sample.json)')
    parser.add_argument('--size', '-n', type=int, default=50,
                        help='Target sample size (default: 50)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')

    args = parser.parse_args()

    # Configuration from arguments
    input_file = args.input
    output_file = args.output
    target_size = args.size

    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print(f"Size:   {target_size}")
    print(f"Seed:   {args.seed}")

    # Load dataset
    print("\nLoading dataset...")
    dataset = load_dataset(input_file)

    # Create sample
    print("\nCreating evaluation sample...")
    sample = create_evaluation_sample(dataset, target_size=target_size, random_seed=args.seed)

    # Save sample
    save_sample(sample, output_file)

    # Print sample statistics
    print("\n" + "="*60)
    print("Sample Statistics:")
    print("="*60)

    event_counts = [s['event_count'] for s in sample]
    threat_levels = [s['threat_level'] for s in sample]

    print(f"Event count range: {min(event_counts)} - {max(event_counts)}")
    print(f"Average event count: {sum(event_counts)/len(event_counts):.1f}")
    print(f"Threat level range: {min(threat_levels):.2f} - {max(threat_levels):.2f}")
    print(f"Average threat level: {sum(threat_levels)/len(threat_levels):.2f}")

    # Show incident IDs for reference
    print(f"\nSample includes {len(sample)} incidents")
    print(f"First 5 incident IDs: {[s['incident_id'][:8] for s in sample[:5]]}")

if __name__ == "__main__":
    main()

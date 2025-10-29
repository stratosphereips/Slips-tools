#!/usr/bin/env python3
"""
Merge multiple correlated incident dataset JSON files into a single unified dataset.

This script combines JSON arrays from multiple correlated dataset files, removing
duplicates based on incident_id and preserving all analysis fields.

Usage:
    python3 merge_datasets.py dataset1.json dataset2.json -o merged_dataset.json
    python3 merge_datasets.py *.json -o final_merged.json
"""

import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_json_file(filepath: str) -> List[Dict[str, Any]]:
    """Load and parse a JSON file containing an array of incidents."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"Warning: {filepath} does not contain a JSON array, skipping", file=sys.stderr)
            return []

        return data
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {filepath} as JSON: {e}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return []


def merge_datasets(input_files: List[str]) -> List[Dict[str, Any]]:
    """
    Merge multiple dataset files, removing duplicates by incident_id.

    Args:
        input_files: List of JSON file paths to merge

    Returns:
        List of merged incident dictionaries (deduplicated)
    """
    incidents_by_id = {}

    for filepath in input_files:
        print(f"Loading {filepath}...")
        incidents = load_json_file(filepath)

        for incident in incidents:
            incident_id = incident.get('incident_id')

            if not incident_id:
                print(f"Warning: Incident without incident_id found in {filepath}, skipping", file=sys.stderr)
                continue

            if incident_id in incidents_by_id:
                print(f"Warning: Duplicate incident_id {incident_id} found, keeping first occurrence", file=sys.stderr)
                continue

            incidents_by_id[incident_id] = incident

    print(f"\nMerged {len(incidents_by_id)} unique incidents from {len(input_files)} files")

    # Return as sorted list for consistent output
    return sorted(incidents_by_id.values(), key=lambda x: x.get('incident_id', ''))


def save_json_file(data: List[Dict[str, Any]], filepath: str, pretty: bool = True):
    """Save data as JSON file."""
    try:
        with open(filepath, 'w') as f:
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)
        print(f"Saved merged dataset to {filepath}")
    except Exception as e:
        print(f"Error: Failed to save {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Merge multiple correlated incident dataset JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge two datasets
  python3 merge_datasets.py dataset1.json dataset2.json -o merged.json

  # Merge all correlated JSON files
  python3 merge_datasets.py final_dataset.json extension_dataset.json -o combined.json

  # Merge with compact output
  python3 merge_datasets.py *.json -o merged.json --compact
        """
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        help='Input JSON files to merge (must contain arrays of incidents)'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output file path for merged dataset'
    )

    parser.add_argument(
        '--compact',
        action='store_true',
        help='Save output in compact format (no indentation)'
    )

    args = parser.parse_args()

    # Validate input files exist
    for filepath in args.input_files:
        if not Path(filepath).exists():
            print(f"Error: Input file does not exist: {filepath}", file=sys.stderr)
            sys.exit(1)

    # Check for duplicate input files
    if len(args.input_files) != len(set(args.input_files)):
        print("Warning: Duplicate input files specified", file=sys.stderr)

    # Merge datasets
    merged_data = merge_datasets(args.input_files)

    if not merged_data:
        print("Warning: No incidents found in input files", file=sys.stderr)

    # Save merged dataset
    save_json_file(merged_data, args.output, pretty=not args.compact)

    print(f"\nMerge complete: {len(merged_data)} incidents in output")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Verify Dataset Merge Operation

This script verifies that merge_datasets.py completed successfully by checking:
- File validity and format
- Count validation (duplicates removed correctly)
- Deduplication (no duplicate incident_ids in output)
- Completeness (all unique inputs present in output)
- Data integrity (required fields present)
- Sorting (output sorted by incident_id)

Usage:
    python3 verify_merge.py
    python3 verify_merge.py --verbose
    python3 verify_merge.py --inputs file1.json file2.json --output merged.json
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Set, Any
from collections import defaultdict


def load_wrapped_json(filepath: str) -> List[Dict[str, Any]]:
    """Load JSON file with wrapped format: {"total_incidents": N, "incidents": [...]}"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        if not isinstance(data, dict) or "incidents" not in data:
            print(f"Error: {filepath} does not have wrapped format with 'incidents' field", file=sys.stderr)
            return None

        incidents = data["incidents"]
        if not isinstance(incidents, list):
            print(f"Error: {filepath} 'incidents' field is not an array", file=sys.stderr)
            return None

        return incidents
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {filepath}: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return None


def load_array_json(filepath: str) -> List[Dict[str, Any]]:
    """Load JSON file with array format: [{...}, {...}]"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"Error: {filepath} is not a JSON array", file=sys.stderr)
            return None

        return data
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {filepath}: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return None


def check_files(input_files: List[str], output_file: str) -> tuple:
    """Verify all files exist and are valid JSON. Returns (inputs_data, output_data, success)"""
    print("=" * 60)
    print("FILE VALIDATION")
    print("=" * 60)

    # Load input files (wrapped format)
    inputs_data = []
    for filepath in input_files:
        incidents = load_wrapped_json(filepath)
        if incidents is None:
            print(f"[FAIL] {filepath}")
            return None, None, False
        inputs_data.append((filepath, incidents))
        print(f"[PASS] {filepath} ({len(incidents)} incidents)")

    # Load output file (array format)
    output_data = load_array_json(output_file)
    if output_data is None:
        print(f"[FAIL] {output_file}")
        return None, None, False
    print(f"[PASS] {output_file} ({len(output_data)} incidents)")

    print()
    return inputs_data, output_data, True


def check_counts(inputs_data: List[tuple], output_data: List[Dict], verbose: bool) -> bool:
    """Verify count validation: total, unique, duplicates"""
    print("=" * 60)
    print("COUNT VALIDATION")
    print("=" * 60)

    # Count total and unique incidents from inputs
    total_count = sum(len(incidents) for _, incidents in inputs_data)
    all_ids = []
    id_to_files = defaultdict(list)

    for filepath, incidents in inputs_data:
        for incident in incidents:
            incident_id = incident.get('incident_id')
            if incident_id:
                all_ids.append(incident_id)
                id_to_files[incident_id].append(Path(filepath).name)

    unique_ids = set(all_ids)
    unique_count = len(unique_ids)
    duplicates_count = total_count - unique_count

    # Count output incidents
    output_count = len(output_data)

    print(f"Input total: {total_count} incidents")
    print(f"Unique IDs: {unique_count}")
    print(f"Output count: {output_count}")
    print(f"Duplicates removed: {duplicates_count}")

    success = True
    if output_count != unique_count:
        print(f"[FAIL] Output count ({output_count}) != unique count ({unique_count})")
        success = False
    else:
        print(f"[PASS] Output count matches unique count")

    # Show duplicate details in verbose mode
    if verbose and duplicates_count > 0:
        print(f"\nDuplicate incident IDs found in inputs:")
        duplicate_ids = [id for id, files in id_to_files.items() if len(files) > 1]
        for dup_id in sorted(duplicate_ids)[:10]:  # Show first 10
            files_str = ", ".join(id_to_files[dup_id])
            print(f"  - {dup_id}: appears in [{files_str}]")
        if len(duplicate_ids) > 10:
            print(f"  ... and {len(duplicate_ids) - 10} more duplicates")

    print()
    return success


def check_deduplication(output_data: List[Dict]) -> bool:
    """Verify no duplicate incident_ids in output"""
    print("=" * 60)
    print("DEDUPLICATION VERIFICATION")
    print("=" * 60)

    output_ids = [inc.get('incident_id') for inc in output_data if inc.get('incident_id')]
    unique_output_ids = set(output_ids)

    duplicates_in_output = len(output_ids) - len(unique_output_ids)

    if duplicates_in_output > 0:
        print(f"[FAIL] Found {duplicates_in_output} duplicate incident_ids in output")
        return False
    else:
        print(f"[PASS] No duplicate incident_ids in output")

    print()
    return True


def check_completeness(inputs_data: List[tuple], output_data: List[Dict]) -> bool:
    """Verify all unique input incidents are in output"""
    print("=" * 60)
    print("COMPLETENESS CHECK")
    print("=" * 60)

    # Collect all unique input IDs
    input_ids = set()
    for _, incidents in inputs_data:
        for incident in incidents:
            incident_id = incident.get('incident_id')
            if incident_id:
                input_ids.add(incident_id)

    # Collect all output IDs
    output_ids = set(inc.get('incident_id') for inc in output_data if inc.get('incident_id'))

    # Check for missing and extra
    missing = input_ids - output_ids
    extra = output_ids - input_ids

    success = True

    if missing:
        print(f"[FAIL] Missing {len(missing)} incident(s) from inputs")
        for miss_id in sorted(list(missing))[:5]:
            print(f"  - {miss_id}")
        success = False
    else:
        print(f"[PASS] All {len(input_ids)} unique incidents from inputs present in output")

    if extra:
        print(f"[FAIL] Found {len(extra)} unexpected incident(s) in output")
        for extra_id in sorted(list(extra))[:5]:
            print(f"  - {extra_id}")
        success = False
    else:
        print(f"[PASS] No unexpected incidents in output")

    print()
    return success


def check_data_integrity(output_data: List[Dict]) -> bool:
    """Verify data integrity: required fields, types"""
    print("=" * 60)
    print("DATA INTEGRITY")
    print("=" * 60)

    required_fields = ['incident_id', 'category', 'source_ip', 'timewindow',
                       'timeline', 'threat_level', 'event_count']

    missing_fields_count = 0
    null_ids_count = 0
    type_errors = 0

    for i, incident in enumerate(output_data):
        # Check required fields
        for field in required_fields:
            if field not in incident:
                missing_fields_count += 1
                if missing_fields_count <= 5:  # Report first 5
                    print(f"Warning: Incident {i} missing field '{field}'")

        # Check for null incident_id
        if not incident.get('incident_id'):
            null_ids_count += 1

        # Check field types
        if 'threat_level' in incident and not isinstance(incident['threat_level'], (int, float)):
            type_errors += 1
        if 'event_count' in incident and not isinstance(incident['event_count'], int):
            type_errors += 1

    success = True

    if missing_fields_count > 0:
        print(f"[FAIL] Found {missing_fields_count} missing required field(s)")
        success = False
    else:
        print(f"[PASS] All required fields present in all incidents")

    if null_ids_count > 0:
        print(f"[FAIL] Found {null_ids_count} incident(s) with null/empty incident_id")
        success = False
    else:
        print(f"[PASS] No null/empty incident_ids")

    if type_errors > 0:
        print(f"[FAIL] Found {type_errors} field type error(s)")
        success = False
    else:
        print(f"[PASS] Field types correct")

    print()
    return success


def check_sorting(output_data: List[Dict]) -> bool:
    """Verify output is sorted by incident_id"""
    print("=" * 60)
    print("SORTING VERIFICATION")
    print("=" * 60)

    output_ids = [inc.get('incident_id', '') for inc in output_data]
    sorted_ids = sorted(output_ids)

    if output_ids == sorted_ids:
        print(f"[PASS] Output correctly sorted by incident_id")
        success = True
    else:
        print(f"[FAIL] Output not sorted by incident_id")
        success = False

    print()
    return success


def main():
    parser = argparse.ArgumentParser(
        description='Verify dataset merge operation'
    )
    parser.add_argument('--inputs', nargs='+',
                       default=['final_dataset.json', 'final_dataset_02.json', 'final_dataset_03.json'],
                       help='Input dataset files (default: final_dataset*.json)')
    parser.add_argument('--output', default='summarization_dataset.json',
                       help='Output merged dataset file (default: summarization_dataset.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed information about duplicates')

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("DATASET MERGE VERIFICATION REPORT")
    print("=" * 60)
    print(f"Inputs: {', '.join(args.inputs)}")
    print(f"Output: {args.output}")
    print()

    # Run all checks
    inputs_data, output_data, files_ok = check_files(args.inputs, args.output)
    if not files_ok:
        print("=" * 60)
        print("OVERALL STATUS: FAIL - File validation failed")
        print("=" * 60)
        sys.exit(1)

    counts_ok = check_counts(inputs_data, output_data, args.verbose)
    dedup_ok = check_deduplication(output_data)
    complete_ok = check_completeness(inputs_data, output_data)
    integrity_ok = check_data_integrity(output_data)
    sorting_ok = check_sorting(output_data)

    # Overall result
    all_passed = all([counts_ok, dedup_ok, complete_ok, integrity_ok, sorting_ok])

    print("=" * 60)
    if all_passed:
        print("OVERALL STATUS: PASS ✓")
        print("All verification checks completed successfully.")
        print("Merge operation verified correct.")
    else:
        print("OVERALL STATUS: FAIL ✗")
        print("Some verification checks failed.")
        print("Please review the failures above.")
    print("=" * 60)
    print()

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()

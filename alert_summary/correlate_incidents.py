#!/usr/bin/env python3
"""
Correlate incidents across DAG and LLM analysis JSON files.

Reads multiple JSON analysis files and creates a consolidated JSON dataset with each incident
showing how it was analyzed across different sources (DAG, GPT-4o-mini, Qwen, etc.)
"""

import json
import argparse
from typing import Dict, List
from pathlib import Path


class IncidentCorrelator:
    """Correlates incidents across multiple JSON analysis files."""

    def __init__(self):
        self.incidents = {}  # incident_id -> merged_data

    def load_json_file(self, filepath: str, analysis_type: str):
        """Load a JSON analysis file and merge incidents."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle both list format and dict format
        if isinstance(data, list):
            incidents = data
        elif isinstance(data, dict) and 'incidents' in data:
            incidents = data['incidents']
        else:
            print(f"Warning: Unexpected JSON structure in {filepath}")
            return

        # Merge each incident
        for incident in incidents:
            incident_id = incident.get('incident_id')
            if not incident_id:
                continue

            # Initialize if first time seeing this incident
            if incident_id not in self.incidents:
                self.incidents[incident_id] = {
                    'incident_id': incident_id,
                    'category': incident.get('category', 'Unknown'),
                    'source_ip': incident.get('source_ip', 'Unknown'),
                    'timewindow': incident.get('timewindow', 'Unknown'),
                    'timeline': incident.get('timeline', 'Unknown'),
                    'threat_level': incident.get('threat_level', 0),
                    'event_count': incident.get('event_count', 0),
                }

            # Add analysis from this file
            # Handle both old format (single 'analysis' field) and new format ('summary' + 'behavior_analysis')
            if 'analysis' in incident:
                # DAG format: single analysis field
                self.incidents[incident_id][f'{analysis_type}_analysis'] = incident['analysis']
            elif 'summary' in incident or 'behavior_analysis' in incident:
                # LLM format: structured with summary and optional behavior_analysis
                analysis_data = {}
                if 'summary' in incident:
                    analysis_data['summary'] = incident['summary']
                if 'behavior_analysis' in incident:
                    analysis_data['behavior_analysis'] = incident['behavior_analysis']
                self.incidents[incident_id][f'{analysis_type}_analysis'] = analysis_data
            else:
                # Fallback: empty
                self.incidents[incident_id][f'{analysis_type}_analysis'] = ''

    def generate_dataset(self, output_path: str = None):
        """Generate consolidated JSON dataset."""
        # Convert to list and sort by incident_id
        incidents_list = [data for data in sorted(self.incidents.values(),
                                                  key=lambda x: x['incident_id'])]

        output = {
            'total_incidents': len(incidents_list),
            'incidents': incidents_list
        }

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"Dataset written to: {output_path}")

        return output


def detect_file_type(filename: str) -> str:
    """Detect analysis type from filename."""
    name = Path(filename).name

    if '.dag.' in name:
        return 'dag'
    elif '.llm.gpt-4o-mini.' in name or '.llm.gpt4o' in name:
        return 'llm_gpt4o_mini'
    elif '.llm.qwen2.5.1.5b.' in name:
        return 'llm_qwen2_5_1_5b'
    elif '.llm.qwen2.5.' in name or '.llm.qwen2_5.' in name:
        return 'llm_qwen2_5'
    elif '.llm.qwen.' in name:
        return 'llm_qwen'
    elif '.llm.llama' in name:
        return 'llm_llama'
    elif '.llm.' in name:
        # Generic LLM - extract model name
        parts = name.split('.llm.')
        if len(parts) > 1:
            model = parts[1].replace('.json', '').replace('.', '_').replace('-', '_')
            return f'llm_{model}'
        return 'llm_unknown'
    else:
        # Generic type based on filename
        return name.replace('.json', '').replace('.', '_')


def main():
    parser = argparse.ArgumentParser(
        description='Correlate incidents across JSON analysis files'
    )
    parser.add_argument(
        'files',
        nargs='+',
        help='Input JSON files to correlate (e.g., *.dag.json *.llm.*.json)'
    )
    parser.add_argument(
        '-o', '--output',
        default='incidents_dataset.json',
        help='Output JSON file (default: incidents_dataset.json)'
    )
    parser.add_argument(
        '--pretty-print',
        action='store_true',
        help='Pretty print JSON to stdout'
    )

    args = parser.parse_args()

    # Initialize correlator
    correlator = IncidentCorrelator()

    # Process each file
    for filepath in args.files:
        path = Path(filepath)
        if not path.exists():
            print(f"Warning: File not found: {filepath}")
            continue

        # Detect file type from filename
        file_type = detect_file_type(filepath)

        print(f"Processing {filepath} as type: {file_type}")
        try:
            correlator.load_json_file(filepath, file_type)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    # Generate output
    result = correlator.generate_dataset(args.output)

    if args.pretty_print:
        print("\n" + "=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"\nProcessed {len(correlator.incidents)} unique incidents")
    print(f"JSON output: {args.output}")


if __name__ == '__main__':
    main()

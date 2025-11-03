#!/usr/bin/env python3
"""
Sample Dataset Generator for Slips Alerts

Samples INCIDENT alerts and their corresponding EVENT alerts from alerts.json files.
Each sampled incident includes all associated events (linked via CorrelID field).

The IDEA format distinguishes between:
- Status: "Incident" - Aggregated security incident with references to events
- Status: "Event" - Individual security events that make up an incident

This tool ensures that when sampling, incidents and their full event context are preserved.

Output Format: JSONL (JSON Lines)
- One JSON object per line
- Each incident followed by its associated events
- Compatible with alert_dag_parser.py and other JSONL processors
"""

import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import sys


class AlertSampler:
    """Handles discovery and sampling of Incident alerts with their associated Events."""

    def __init__(self, base_dir: str = "./sample_logs/alya_datasets", seed: Optional[int] = None):
        """
        Initialize the sampler.

        Args:
            base_dir: Base directory containing the dataset
            seed: Random seed for reproducibility
        """
        self.base_dir = Path(base_dir)
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def discover_files(self, category: Optional[str] = None) -> List[Path]:
        """
        Discover all alerts.json files in the dataset.

        Args:
            category: Filter by category ('normal', 'malware', or None for all)

        Returns:
            List of Path objects to alerts.json files
        """
        files = []

        # Determine which directories to search
        search_dirs = []
        if category is None:
            search_dirs = [self.base_dir / "Normal", self.base_dir / "Malware"]
        elif category.lower() == "normal":
            search_dirs = [self.base_dir / "Normal"]
        elif category.lower() == "malware":
            search_dirs = [self.base_dir / "Malware"]
        else:
            raise ValueError(f"Invalid category: {category}. Must be 'normal', 'malware', or None")

        # Find all alerts.json files
        for search_dir in search_dirs:
            if search_dir.exists():
                files.extend(search_dir.rglob("alerts.json"))

        return sorted(files)

    def load_alerts_indexed(self, file_path: Path) -> tuple[List[Dict], Dict[str, Dict]]:
        """
        Load alerts from a JSON file and build an index.

        Args:
            file_path: Path to the alerts.json file

        Returns:
            Tuple of (incidents_list, events_by_id_dict)
        """
        incidents = []
        events_by_id = {}

        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        alert = json.loads(line)
                        alert_id = alert.get('ID')
                        status = alert.get('Status', '')

                        if status == 'Incident':
                            incidents.append(alert)
                        elif status == 'Event' and alert_id:
                            events_by_id[alert_id] = alert

                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse line {line_num} in {file_path}: {e}",
                              file=sys.stderr)
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)

        return incidents, events_by_id

    def extract_metadata(self, file_path: Path) -> Dict[str, str]:
        """
        Extract metadata from file path.

        Args:
            file_path: Path to the alerts.json file

        Returns:
            Dictionary with metadata (category, dataset, capture, timewindow)
        """
        parts = file_path.parts

        # Find indices of key directories
        try:
            alya_idx = parts.index("alya_datasets")
        except ValueError:
            return {"category": "unknown", "dataset": "unknown", "capture": "unknown",
                    "timewindow": "unknown", "source_file": str(file_path)}

        metadata = {
            "category": parts[alya_idx + 1] if alya_idx + 1 < len(parts) else "unknown",
            "dataset": parts[alya_idx + 2] if alya_idx + 2 < len(parts) else "unknown",
            "capture": parts[alya_idx + 3] if alya_idx + 3 < len(parts) else "unknown",
            "timewindow": parts[alya_idx + 4] if alya_idx + 4 < len(parts) else "unknown",
            "source_file": str(file_path)
        }

        return metadata

    def sample_incidents(
        self,
        num_incidents: Optional[int] = None,
        num_files: Optional[int] = None,
        incidents_per_file: Optional[int] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Sample incidents from the dataset, including all associated events.

        Args:
            num_incidents: Total number of incidents to sample across all files
            num_files: Number of random files to sample from
            incidents_per_file: Number of incidents to sample from each file
            category: Filter by category ('normal', 'malware', or None)
            severity: Filter by severity ('low', 'medium', 'high', or None)

        Returns:
            List of sampled incidents with their events and metadata
        """
        # Discover files
        files = self.discover_files(category)

        if not files:
            print("No alerts.json files found!", file=sys.stderr)
            return []

        print(f"Found {len(files)} alerts.json files", file=sys.stderr)

        # Optionally select random subset of files
        if num_files is not None and num_files < len(files):
            files = random.sample(files, num_files)
            print(f"Randomly selected {num_files} files", file=sys.stderr)

        # Collect incidents with their events
        all_sampled = []

        for file_path in files:
            # Load and index alerts
            incidents, events_by_id = self.load_alerts_indexed(file_path)

            if not incidents:
                print(f"No incidents found in {file_path}", file=sys.stderr)
                continue

            # Filter by severity if specified
            if severity is not None:
                severity_lower = severity.lower()
                incidents = [inc for inc in incidents
                            if inc.get("Severity", "").lower() == severity_lower]

            if not incidents:
                continue

            # Sample from this file
            if incidents_per_file is not None:
                n_sample = min(incidents_per_file, len(incidents))
                sampled_incidents = random.sample(incidents, n_sample)
            else:
                sampled_incidents = incidents

            # For each incident, collect its events
            metadata = self.extract_metadata(file_path)

            for incident in sampled_incidents:
                # Get associated event IDs from CorrelID field
                event_ids = incident.get('CorrelID', [])

                # Collect the actual events
                associated_events = []
                missing_events = []

                for event_id in event_ids:
                    if event_id in events_by_id:
                        associated_events.append(events_by_id[event_id])
                    else:
                        missing_events.append(event_id)

                # Create the sample entry
                sample_entry = {
                    "incident": incident,
                    "events": associated_events,
                    "metadata": {
                        **metadata,
                        "num_events": len(associated_events),
                        "missing_events": len(missing_events),
                        "total_event_ids": len(event_ids)
                    }
                }

                if missing_events:
                    print(f"Warning: {len(missing_events)}/{len(event_ids)} events missing for incident {incident.get('ID')[:8]}... in {file_path.name}",
                          file=sys.stderr)

                all_sampled.append(sample_entry)

        # If total number of incidents specified, sample from combined pool
        if num_incidents is not None and num_incidents < len(all_sampled):
            all_sampled = random.sample(all_sampled, num_incidents)

        print(f"\nSampled {len(all_sampled)} total incidents", file=sys.stderr)

        # Calculate total events
        total_events = sum(len(s['events']) for s in all_sampled)
        print(f"Total events included: {total_events}", file=sys.stderr)

        return all_sampled

    def get_statistics(self, sampled_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics about the sampled data.

        Args:
            sampled_data: List of sampled incidents with events

        Returns:
            Statistics dictionary
        """
        stats = {
            "total_incidents": len(sampled_data),
            "total_events": sum(len(s['events']) for s in sampled_data),
            "by_category": defaultdict(int),
            "by_severity": defaultdict(int),
            "by_dataset": defaultdict(int),
            "events_per_incident": {
                "min": float('inf'),
                "max": 0,
                "avg": 0
            }
        }

        event_counts = []

        for item in sampled_data:
            incident = item["incident"]
            metadata = item["metadata"]
            num_events = len(item["events"])

            stats["by_category"][metadata["category"]] += 1
            stats["by_severity"][incident.get("Severity", "Unknown")] += 1
            stats["by_dataset"][metadata["dataset"]] += 1

            event_counts.append(num_events)

        if event_counts:
            stats["events_per_incident"]["min"] = min(event_counts)
            stats["events_per_incident"]["max"] = max(event_counts)
            stats["events_per_incident"]["avg"] = sum(event_counts) / len(event_counts)

        # Convert defaultdicts to regular dicts for JSON serialization
        stats["by_category"] = dict(stats["by_category"])
        stats["by_severity"] = dict(stats["by_severity"])
        stats["by_dataset"] = dict(stats["by_dataset"])

        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Sample incident alerts with their associated events from Slips dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sample 10 random incidents with all their events
  %(prog)s --num-incidents 10 --output sample.jsonl

  # Sample 5 incidents from 3 random files
  %(prog)s --num-files 3 --incidents-per-file 5 --output sample.jsonl

  # Sample only malware incidents
  %(prog)s --category malware --num-incidents 20 --output malware_sample.jsonl

  # Sample with reproducible seed and statistics
  %(prog)s --num-incidents 15 --seed 42 --include-stats --output reproducible.jsonl

  # Sample high-severity incidents only
  %(prog)s --severity high --num-incidents 10 --output high_severity.jsonl

  # Use with alert_dag_parser.py
  %(prog)s --num-incidents 5 --output sample.jsonl
  python3 alert_dag_parser.py sample.jsonl

Output Format:
  JSONL (JSON Lines) - one JSON object per line, compatible with alert_dag_parser.py
  Each incident is followed by its associated events.

  With --include-stats, statistics are written to a separate .stats.json file.

Note: This tool samples INCIDENT alerts (Status: "Incident") and automatically includes
all associated EVENT alerts (Status: "Event") linked via the CorrelID field.
        """
    )

    parser.add_argument(
        "--base-dir",
        default="./sample_logs/alya_datasets",
        help="Base directory containing the dataset (default: ./sample_logs/alya_datasets)"
    )

    parser.add_argument(
        "--num-incidents",
        type=int,
        help="Total number of incidents to sample across all files"
    )

    parser.add_argument(
        "--num-files",
        type=int,
        help="Number of random files to sample from"
    )

    parser.add_argument(
        "--incidents-per-file",
        type=int,
        help="Number of incidents to sample from each selected file"
    )

    parser.add_argument(
        "--category",
        choices=["normal", "malware"],
        help="Filter by category (normal or malware)"
    )

    parser.add_argument(
        "--severity",
        choices=["low", "medium", "high"],
        help="Filter by incident severity level"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility"
    )

    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output JSON file path"
    )

    parser.add_argument(
        "--include-stats",
        action="store_true",
        help="Include statistics in the output file"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.num_incidents is None and args.incidents_per_file is None:
        parser.error("Must specify either --num-incidents or --incidents-per-file")

    # Create sampler
    sampler = AlertSampler(base_dir=args.base_dir, seed=args.seed)

    # Sample incidents
    sampled = sampler.sample_incidents(
        num_incidents=args.num_incidents,
        num_files=args.num_files,
        incidents_per_file=args.incidents_per_file,
        category=args.category,
        severity=args.severity
    )

    # Write output in JSONL format (one JSON object per line)
    output_path = Path(args.output)

    with open(output_path, 'w') as f:
        for sample_entry in sampled:
            incident = sample_entry['incident']
            events = sample_entry['events']
            metadata = sample_entry['metadata']

            # Inject category field from metadata into incident JSON
            incident['category'] = metadata.get('category', 'Unknown')

            # Write incident as one line
            f.write(json.dumps(incident) + '\n')

            # Write each associated event as one line
            for event in events:
                f.write(json.dumps(event) + '\n')

    print(f"\nSampled data written to: {output_path}", file=sys.stderr)
    print(f"Format: JSONL (compatible with alert_dag_parser.py)", file=sys.stderr)

    # Generate and display statistics
    if args.include_stats:
        stats = sampler.get_statistics(sampled)

        # Print statistics to stderr
        print("\n=== Sampling Statistics ===", file=sys.stderr)
        print(f"Total incidents: {stats['total_incidents']}", file=sys.stderr)
        print(f"Total events: {stats['total_events']}", file=sys.stderr)
        print(f"\nEvents per incident:", file=sys.stderr)
        print(f"  Min: {stats['events_per_incident']['min']}", file=sys.stderr)
        print(f"  Max: {stats['events_per_incident']['max']}", file=sys.stderr)
        print(f"  Avg: {stats['events_per_incident']['avg']:.1f}", file=sys.stderr)
        print(f"\nBy category:", file=sys.stderr)
        for cat, count in stats['by_category'].items():
            print(f"  {cat}: {count}", file=sys.stderr)
        print(f"\nBy severity:", file=sys.stderr)
        for sev, count in stats['by_severity'].items():
            print(f"  {sev}: {count}", file=sys.stderr)

        # Write statistics to separate file
        stats_path = output_path.with_suffix('.stats.json')
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"\nStatistics written to: {stats_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

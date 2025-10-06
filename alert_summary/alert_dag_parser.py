#!/usr/bin/env python3
"""
Alya Alert DAG Parser

This script parses JSONL files containing Slips Incidents and Events in IDEA format.
For each Incident, it displays all associated Events in a comprehensive format.

Key Design: Uses structured JSON fields (Severity, Source, Target) rather than
text parsing to ensure compatibility with future unknown alert types.

Usage:
    python alert_dag_parser.py alerts.json
    python alert_dag_parser.py alerts.json --incident-id <UUID>
    python alert_dag_parser.py alerts.json -o output.txt
"""

import json
import argparse
import sys
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime


@dataclass
class JSONEvent:
    """Represents a single Event from the JSONL file."""
    id: str
    severity: str
    start_time: str
    confidence: float
    description: str
    source_ips: List[str]
    source_ports: List[int]
    target_ips: List[str]
    target_ports: List[int]
    note: Dict[str, Any]
    raw_json: Dict[str, Any]

    @classmethod
    def from_json(cls, json_obj: Dict[str, Any]) -> 'JSONEvent':
        """Create JSONEvent from parsed JSON object."""
        # Parse Note field (it's a JSON string)
        note = {}
        if 'Note' in json_obj and json_obj['Note']:
            try:
                note = json.loads(json_obj['Note'])
            except:
                note = {'raw': json_obj['Note']}

        # Extract Source IPs and Ports
        source_ips = []
        source_ports = []
        for src in json_obj.get('Source', []):
            if 'IP' in src:
                source_ips.append(src['IP'])
            if 'Port' in src:
                source_ports.extend(src['Port'])

        # Extract Target IPs and Ports
        target_ips = []
        target_ports = []
        for tgt in json_obj.get('Target', []):
            if 'IP' in tgt:
                target_ips.append(tgt['IP'])
            if 'Port' in tgt:
                target_ports.extend(tgt['Port'])

        return cls(
            id=json_obj.get('ID', ''),
            severity=json_obj.get('Severity', 'Unknown'),
            start_time=json_obj.get('StartTime', ''),
            confidence=json_obj.get('Confidence', 0.0),
            description=json_obj.get('Description', ''),
            source_ips=source_ips,
            source_ports=source_ports,
            target_ips=target_ips,
            target_ports=target_ports,
            note=note,
            raw_json=json_obj
        )


@dataclass
class JSONIncident:
    """Represents a single Incident from the JSONL file."""
    id: str
    source_ips: List[str]
    start_time: str
    create_time: str
    correl_ids: List[str]
    note: Dict[str, Any]
    raw_json: Dict[str, Any]

    @classmethod
    def from_json(cls, json_obj: Dict[str, Any]) -> 'JSONIncident':
        """Create JSONIncident from parsed JSON object."""
        # Parse Note field
        note = {}
        if 'Note' in json_obj and json_obj['Note']:
            try:
                note = json.loads(json_obj['Note'])
            except:
                note = {'raw': json_obj['Note']}

        # Extract Source IPs
        source_ips = []
        for src in json_obj.get('Source', []):
            if 'IP' in src:
                source_ips.append(src['IP'])

        return cls(
            id=json_obj.get('ID', ''),
            source_ips=source_ips,
            start_time=json_obj.get('StartTime', ''),
            create_time=json_obj.get('CreateTime', ''),
            correl_ids=json_obj.get('CorrelID', []),
            note=note,
            raw_json=json_obj
        )


class AlertJSONParser:
    """Parser for JSONL alert files."""

    def __init__(self):
        self.incidents: List[JSONIncident] = []
        self.events: Dict[str, JSONEvent] = {}  # event_id -> event

    def parse_file(self, filepath: str) -> None:
        """Parse JSONL file and separate Incidents from Events."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        json_obj = json.loads(line)
                        status = json_obj.get('Status', '')

                        if status == 'Incident':
                            incident = JSONIncident.from_json(json_obj)
                            self.incidents.append(incident)
                        elif status == 'Event':
                            event = JSONEvent.from_json(json_obj)
                            self.events[event.id] = event
                        else:
                            print(f"Warning: Unknown status '{status}' at line {line_num}", file=sys.stderr)

                    except json.JSONDecodeError as e:
                        print(f"Warning: JSON parse error at line {line_num}: {e}", file=sys.stderr)
                    except Exception as e:
                        print(f"Warning: Error processing line {line_num}: {e}", file=sys.stderr)

        except FileNotFoundError:
            print(f"Error: File '{filepath}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    def get_incident_events(self, incident: JSONIncident) -> List[JSONEvent]:
        """Get all Events associated with an Incident via CorrelID."""
        events = []
        for event_id in incident.correl_ids:
            if event_id in self.events:
                events.append(self.events[event_id])
            else:
                print(f"Warning: Event {event_id} not found for Incident {incident.id}", file=sys.stderr)
        return events


class AlertDAGGenerator:
    """Generates comprehensive DAG output for Incidents using field-based analysis."""

    def __init__(self):
        self.severity_priority = {
            'Critical': 4,
            'High': 3,
            'Medium': 2,
            'Low': 1,
            'Info': 0,
            'Unknown': -1
        }

    def generate_comprehensive_analysis(self, incident: JSONIncident, events: List[JSONEvent]) -> str:
        """Generate comprehensive analysis for a single incident."""
        if not events:
            return f"Incident {incident.id}: No associated events found"

        lines = []
        lines.append("=" * 60)
        lines.append(f"Incident: {incident.id}")

        # Incident metadata
        source_ip = incident.source_ips[0] if incident.source_ips else "Unknown"
        timewindow = incident.note.get('timewindow', 'Unknown')
        threat_level = incident.note.get('accumulated_threat_level', 'Unknown')

        lines.append(f"Source IP: {source_ip} | Timewindow: {timewindow}")

        # Timeline
        start_time = self._format_time(incident.start_time)
        end_time = self._format_time(incident.note.get('EndTime', ''))
        if end_time:
            lines.append(f"Timeline: {start_time} to {end_time}")
        else:
            lines.append(f"Start Time: {start_time}")

        lines.append(f"Threat Level: {threat_level} | Events: {len(events)}")
        lines.append("")

        # Group events using field-based classification
        grouped_events = self._group_events_by_fields(events)

        # Display grouped events
        for group_key, group_events in sorted(grouped_events.items(),
                                             key=lambda x: self.severity_priority.get(x[0][0], -1),
                                             reverse=True):
            severity, target_summary = group_key
            time_str = self._get_time_range(group_events)

            # Create summary line
            summary = self._create_event_summary(group_events, target_summary)
            lines.append(f"• {time_str} - {summary} [{severity.upper()}]")

            # Show individual descriptions for this group (limit to 3 examples)
            unique_descs = list(set([e.description for e in group_events]))
            for desc in unique_descs[:3]:
                count = sum(1 for e in group_events if e.description == desc)
                if count > 1:
                    lines.append(f"  - {desc} (x{count})")
                else:
                    lines.append(f"  - {desc}")

            if len(unique_descs) > 3:
                lines.append(f"  - ... and {len(unique_descs) - 3} more variations")

        # Summary statistics
        lines.append("")
        lines.append(f"Total Evidence: {len(events)} events")

        # Severity breakdown
        severity_counts = defaultdict(int)
        for event in events:
            severity_counts[event.severity] += 1

        sev_parts = [f"{sev}: {count}" for sev, count in sorted(severity_counts.items(),
                                                                 key=lambda x: self.severity_priority.get(x[0], -1),
                                                                 reverse=True)]
        lines.append(f"Severity breakdown: {', '.join(sev_parts)}")

        return "\n".join(lines)

    def _group_events_by_fields(self, events: List[JSONEvent]) -> Dict[tuple, List[JSONEvent]]:
        """Group events by structured fields (Severity + Target characteristics)."""
        groups = defaultdict(list)

        for event in events:
            # Create group key based on structured fields
            severity = event.severity

            # Create target summary for grouping
            target_summary = self._create_target_summary(event)

            group_key = (severity, target_summary)
            groups[group_key].append(event)

        return groups

    def _create_target_summary(self, event: JSONEvent) -> str:
        """Create a summary of target characteristics for grouping."""
        if event.target_ips and event.target_ports:
            # Has both IP and port
            ip_summary = event.target_ips[0] if len(event.target_ips) == 1 else f"{len(event.target_ips)} IPs"
            port_summary = str(event.target_ports[0]) if len(event.target_ports) == 1 else f"{len(event.target_ports)} ports"
            return f"{ip_summary}:{port_summary}"
        elif event.target_ips:
            # Only IP
            return event.target_ips[0] if len(event.target_ips) == 1 else f"{len(event.target_ips)} IPs"
        elif event.target_ports:
            # Only port
            return f"port {event.target_ports[0]}" if len(event.target_ports) == 1 else f"{len(event.target_ports)} ports"
        else:
            # No target info - use description prefix
            desc_prefix = event.description.split()[0] if event.description else "Unknown"
            return desc_prefix

    def _create_event_summary(self, events: List[JSONEvent], target_summary: str) -> str:
        """Create human-readable summary for a group of events."""
        count = len(events)

        # Get common characteristics
        first_event = events[0]

        # Try to create meaningful summary
        if target_summary:
            if count == 1:
                return f"Event to {target_summary}"
            else:
                return f"{count} events to {target_summary}"
        else:
            # Fallback: use first few words of description
            desc_start = ' '.join(first_event.description.split()[:5])
            if count == 1:
                return desc_start
            else:
                return f"{count} similar events: {desc_start}..."

    def _get_time_range(self, events: List[JSONEvent]) -> str:
        """Get time range for events (HH:MM format)."""
        if not events:
            return "Unknown"

        times = [self._format_time(e.start_time, short=True) for e in events]
        times = [t for t in times if t]  # Filter out None

        if not times:
            return "Unknown"

        if len(set(times)) == 1:
            return times[0]
        else:
            return f"{min(times)}-{max(times)}"

    def _format_time(self, timestamp: str, short: bool = False) -> str:
        """Format ISO timestamp to readable format."""
        if not timestamp:
            return ""

        try:
            # Parse ISO format: 1970-01-01T00:00:13.676697+00:00
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if short:
                return dt.strftime("%H:%M")
            else:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp


def main():
    parser = argparse.ArgumentParser(
        description='Parse JSONL alert files and generate comprehensive incident analysis'
    )
    parser.add_argument('json_file', help='Path to the JSONL alerts file')
    parser.add_argument('--incident-id', '-i', help='Analyze specific incident by ID')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Parse the JSONL file
    if args.verbose:
        print(f"Parsing file: {args.json_file}", file=sys.stderr)

    alert_parser = AlertJSONParser()
    alert_parser.parse_file(args.json_file)

    if args.verbose:
        print(f"Found {len(alert_parser.incidents)} incidents and {len(alert_parser.events)} events", file=sys.stderr)

    # Filter incidents if specific ID requested
    incidents_to_process = alert_parser.incidents
    if args.incident_id:
        incidents_to_process = [inc for inc in alert_parser.incidents if inc.id == args.incident_id]
        if not incidents_to_process:
            print(f"Error: Incident {args.incident_id} not found", file=sys.stderr)
            sys.exit(1)

    # Generate analysis
    dag_generator = AlertDAGGenerator()
    output_lines = []

    for incident in incidents_to_process:
        events = alert_parser.get_incident_events(incident)
        analysis = dag_generator.generate_comprehensive_analysis(incident, events)
        output_lines.append(analysis)

    # Output
    output_text = "\n".join(output_lines)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            if args.verbose:
                print(f"Output written to: {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_text)


if __name__ == '__main__':
    main()

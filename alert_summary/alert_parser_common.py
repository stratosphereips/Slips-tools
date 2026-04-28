#!/usr/bin/env python3
"""
Shared parsing utilities for Slips IDEA-format JSONL alert files.

Provides JSONEvent, JSONIncident, AlertJSONParser, and helper functions
used by alert_dag_parser_llm.py, alert_cause_risk_analyzer.py, and inference.py.
"""

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


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
        note = {}
        if 'Note' in json_obj and json_obj['Note']:
            try:
                note = json.loads(json_obj['Note'])
            except Exception:
                note = {'raw': json_obj['Note']}

        source_ips, source_ports = [], []
        for src in json_obj.get('Source', []):
            if 'IP' in src:
                source_ips.append(src['IP'])
            if 'Port' in src:
                source_ports.extend(src['Port'])

        target_ips, target_ports = [], []
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
            raw_json=json_obj,
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
        note = {}
        if 'Note' in json_obj and json_obj['Note']:
            try:
                note = json.loads(json_obj['Note'])
            except Exception:
                note = {'raw': json_obj['Note']}

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
            raw_json=json_obj,
        )


class AlertJSONParser:
    """Parser for JSONL alert files in IDEA format."""

    def __init__(self):
        self.incidents: List[JSONIncident] = []
        self.events: Dict[str, JSONEvent] = {}

    def parse_file(self, filepath: str) -> None:
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
                            self.incidents.append(JSONIncident.from_json(json_obj))
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
        events = []
        for event_id in incident.correl_ids:
            if event_id in self.events:
                events.append(self.events[event_id])
            else:
                print(f"Warning: Event {event_id} not found for Incident {incident.id}", file=sys.stderr)
        return events


def format_time(timestamp: str, short: bool = False) -> str:
    """Format ISO timestamp to readable format."""
    if not timestamp:
        return ""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%H:%M") if short else dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp


def normalize_pattern(description: str) -> str:
    """Normalize variable parts of an event description for grouping."""
    pattern = description
    pattern = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', pattern)
    pattern = re.sub(r'\b\d+/TCP\b', '<PORT>/TCP', pattern, flags=re.IGNORECASE)
    pattern = re.sub(r'\b\d+/UDP\b', '<PORT>/UDP', pattern, flags=re.IGNORECASE)
    pattern = re.sub(r'port[s]?:?\s*\d+(-\d+)?', 'port <PORT>', pattern, flags=re.IGNORECASE)
    pattern = re.sub(r'\b\d+\b', '<NUM>', pattern)
    return pattern


def group_events_by_pattern(events: List[JSONEvent]) -> List[Dict[str, Any]]:
    """Group events by normalized description pattern. Returns list of group summaries."""
    groups: Dict[str, List[JSONEvent]] = defaultdict(list)
    for event in events:
        groups[normalize_pattern(event.description)].append(event)

    summaries = []
    for pattern, grp in groups.items():
        grp.sort(key=lambda e: e.start_time)
        first_t = format_time(grp[0].start_time, short=True)
        last_t = format_time(grp[-1].start_time, short=True)
        time_range = f"{first_t}-{last_t}" if first_t != last_t else first_t

        sample_values: List[str] = []
        for event in grp[:3]:
            ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', event.description)
            sample_values.extend(ips[:2])
            ports = re.findall(r'\b(\d+)/(TCP|UDP)\b', event.description, flags=re.IGNORECASE)
            sample_values.extend(f"{p[0]}/{p[1]}" for p in ports[:2])

        seen: set = set()
        unique_samples = [v for v in sample_values if not (v in seen or seen.add(v))]  # type: ignore[func-returns-value]

        summaries.append({
            'time_range': time_range,
            'pattern': pattern,
            'count': len(grp),
            'samples': unique_samples[:5],
            'original_desc': grp[0].description,
        })

    summaries.sort(key=lambda g: (-g['count'], g['time_range']))
    return summaries


def build_evidence_text(events: List[JSONEvent], group: bool = False) -> str:
    """Build formatted evidence text from events, optionally grouping similar ones."""
    if group:
        grouped = group_events_by_pattern(events)
        lines = []
        for g in grouped:
            samples_str = ', '.join(g['samples']) if g['samples'] else 'various'
            if g['count'] == 1:
                lines.append(f"{g['time_range']} | {g['original_desc']}")
            else:
                lines.append(f"{g['time_range']} | {g['original_desc']} ({g['count']}x similar, samples: {samples_str})")
        return "\n".join(lines)
    else:
        return "\n".join(
            f"{format_time(e.start_time, short=True)} | {e.description}"
            for e in events
        )

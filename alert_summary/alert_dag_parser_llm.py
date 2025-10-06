#!/usr/bin/env python3
"""
LLM-Enhanced Alert DAG Parser

This script parses JSONL files containing Slips Incidents and Events in IDEA format.
For each Incident, it uses an LLM to generate a concise, structured analysis.

Usage:
    python alert_dag_parser_llm.py alerts.json
    python alert_dag_parser_llm.py alerts.json --incident-id <UUID>
    python alert_dag_parser_llm.py alerts.json -o output.txt --model gpt-4o-mini

Dependencies:
    - openai
    - python-dotenv
    - tiktoken (optional, for token counting)

If tiktoken is installed, token counts will be displayed with --verbose flag.
"""

import json
import argparse
import sys
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import OpenAI for LLM integration
import openai
from dotenv import load_dotenv

# Import tiktoken for token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# Load environment variables
load_dotenv()


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


class LLMAlertGenerator:
    """Generates LLM-based analysis for Incidents."""

    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            timeout=1200000  # 20 minutes timeout
        )

        # Initialize token encoder if available
        self.encoding = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Try to get encoding for the specific model
                self.encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base (used by gpt-4, gpt-3.5-turbo)
                try:
                    self.encoding = tiktoken.get_encoding("cl100k_base")
                except:
                    pass

    def generate_analysis(self, incident: JSONIncident, events: List[JSONEvent], verbose: bool = False) -> str:
        """Generate LLM-based analysis for a single incident."""
        if not events:
            return f"Incident {incident.id}: No associated events found"

        # Build the prompt
        prompt = self._build_prompt(incident, events)

        # Count tokens
        token_count = self._count_tokens(prompt)

        if verbose:
            if token_count > 0:
                print(f"Querying LLM for incident {incident.id}... ({token_count} tokens)", file=sys.stderr)
            else:
                print(f"Querying LLM for incident {incident.id}...", file=sys.stderr)

        # Query the LLM
        try:
            response = self._query_llm(prompt)
            return response
        except Exception as e:
            print(f"Error querying LLM: {e}", file=sys.stderr)
            return f"Incident {incident.id}: LLM query failed - {str(e)}"

    def _build_prompt(self, incident: JSONIncident, events: List[JSONEvent]) -> str:
        """Build a concise prompt for LLM analysis."""
        # Extract incident metadata
        source_ip = incident.source_ips[0] if incident.source_ips else "Unknown"
        timewindow = incident.note.get('timewindow', 'Unknown')
        threat_level = incident.note.get('accumulated_threat_level', 'Unknown')
        start_time = self._format_time(incident.start_time)
        end_time = self._format_time(incident.note.get('EndTime', ''))

        # Build raw event list (without severity - LLM will assess it)
        event_lines = []
        for event in events:
            time_str = self._format_time(event.start_time, short=True)
            event_lines.append(f"{time_str} | {event.description}")

        events_text = "\n".join(event_lines)

        # Create prompt focused on clear summarization with LLM-assessed severity
        prompt = f"""You are a security analyst. Your task is to translate technical security events into clear, concise, human-readable summaries and assess their severity.

INCIDENT METADATA:
- Incident ID: {incident.id}
- Source IP: {source_ip}
- Timewindow: {timewindow}
- Accumulated Threat Level: {threat_level}
- Time Range: {start_time} to {end_time if end_time else 'ongoing'}
- Total Events: {len(events)}

RAW EVENTS (Time | Description):
{events_text}

YOUR TASK:
1. Transform the technical event descriptions into clear, readable summaries using plain language
2. Group identical or very similar events (e.g., 24 identical connections → one summary line)
3. Assess the severity of each event/group based on security impact:
   - CRITICAL: Active exploitation, data exfiltration, confirmed malware C2
   - HIGH: Scanning, suspicious connections, potential threats
   - MEDIUM: Anomalous but potentially benign behavior
   - LOW: Minor issues, likely false positives
   - INFO: Informational events, normal network behavior
4. Calculate the overall severity breakdown based on your assessments

OUTPUT FORMAT (match this structure exactly):

============================================================
Incident: {incident.id}
Source IP: {source_ip} | Timewindow: {timewindow}
Timeline: {start_time} to {end_time if end_time else 'ongoing'}
Threat Level: {threat_level} | Events: {len(events)}

• HH:MM-HH:MM - [Your clear grouped summary] [YOUR_ASSESSED_SEVERITY]
• HH:MM - [Your clear summary] [YOUR_ASSESSED_SEVERITY]

Total Evidence: {len(events)} events
Severity breakdown: [Your calculated breakdown, e.g., "High: 5, Medium: 3, Info: 2"]

EXAMPLES OF GOOD SUMMARIZATION WITH SEVERITY ASSESSMENT:
- "Connection on port 0 from 0.0.0.0:0 to 224.0.0.1:0" → "IGMP multicast traffic to group address [INFO]"
- "Detected a horizontal port scan to port 443/TCP. 50 unique dst IPs" → "Port scanning 50 hosts on HTTPS port [HIGH]"
- "Connection to known C2 server 185.29.135.234:443" → "Direct connection to command & control server [CRITICAL]"
- "Connection without DNS resolution to CDN IP" → "Direct IP connection (likely CDN/API) [LOW]"

RULES:
- Group identical events into ONE line (don't list the same event 24 times)
- Use time ranges (HH:MM-HH:MM) when showing grouped events
- Assess severity based on security impact, not just event type
- Use severity levels: CRITICAL, HIGH, MEDIUM, LOW, INFO
- Keep descriptions clear and concise
- Just output the structured summary - no explanations or meta-commentary
- Do not include token counts or performance statistics"""

        return prompt

    def _query_llm(self, prompt: str) -> str:
        """Query the LLM with the given prompt."""
        messages = [{"role": "user", "content": prompt}]
        full_reply = ""

        # Create streaming chat completion request
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True}
        )

        # Process the streaming response (collect only content, ignore stats)
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                part = chunk.choices[0].delta.content
                full_reply += part

        return full_reply.strip()

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in the text."""
        if not self.encoding:
            return 0

        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            # If token counting fails, return 0 to indicate unavailable
            return 0

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
        description='Parse JSONL alert files and generate LLM-based incident analysis'
    )
    parser.add_argument('json_file', help='Path to the JSONL alerts file')
    parser.add_argument('--incident-id', '-i', help='Analyze specific incident by ID')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--model', default='gpt-4o-mini', help='LLM model to use (default: gpt-4o-mini)')
    parser.add_argument('--base-url', default='https://api.openai.com/v1',
                       help='LLM API base URL (default: https://api.openai.com/v1)')
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
    llm_generator = LLMAlertGenerator(args.model, args.base_url)
    output_lines = []

    for incident in incidents_to_process:
        events = alert_parser.get_incident_events(incident)
        analysis = llm_generator.generate_analysis(incident, events, args.verbose)
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

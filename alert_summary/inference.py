#!/usr/bin/env python3
"""
Unified Inference Script for Slips Alert Analysis

Accepts a JSONL IDEA-format file and produces LLM-generated analysis.
Supports three task modes:
  summary  - generate summary + optional behavior_analysis
             (output compatible with correlate_incidents.py)
  risk     - generate cause_analysis + risk_assessment
             (output compatible with correlate_risks.py)
  both     - all four analyses in a single pass

Usage:
    python3 inference.py <input.jsonl> --task summary [options]
    python3 inference.py <input.jsonl> --task risk [options]
    python3 inference.py <input.jsonl> --task both [options]

Dependencies:
    openai, python-dotenv
    tiktoken (optional, for token counting)
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

import openai
from dotenv import load_dotenv

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from alert_parser_common import (
    AlertJSONParser,
    JSONEvent,
    JSONIncident,
    build_evidence_text,
    format_time,
    group_events_by_pattern,
)

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


class InferenceEngine:
    """Runs LLM inference for summary and/or risk tasks on IDEA-format incidents."""

    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            timeout=1200,  # 20 minutes in seconds
        )
        self.encoding = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                try:
                    self.encoding = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, incident: JSONIncident, events: List[JSONEvent],
            task: str, group_events: bool = False,
            behavior_analysis: bool = False,
            verbose: bool = False) -> Dict[str, Any]:
        """
        Run the requested task(s) for a single incident.

        Returns a dict with the fields appropriate to the task:
          summary  -> summary, behavior_analysis
          risk     -> cause_analysis, risk_assessment
          both     -> all four
        """
        if not events:
            msg = f"Incident {incident.id}: No associated events found"
            result: Dict[str, Any] = {}
            if task in ('summary', 'both'):
                result['summary'] = msg
                result['behavior_analysis'] = None
            if task in ('risk', 'both'):
                result['cause_analysis'] = msg
                result['risk_assessment'] = msg
            return result

        result = {}

        if task in ('summary', 'both'):
            result.update(self._run_summary(incident, events, group_events, behavior_analysis, verbose))

        if task in ('risk', 'both'):
            result.update(self._run_risk(incident, events, group_events, verbose))

        return result

    # ------------------------------------------------------------------
    # Summary task
    # ------------------------------------------------------------------

    def _run_summary(self, incident: JSONIncident, events: List[JSONEvent],
                     group_events: bool, behavior_analysis: bool,
                     verbose: bool) -> Dict[str, Any]:
        prompt = self._build_summary_prompt(incident, events, group_events)
        self._log_query("summary", incident.id, prompt, group_events, len(events), verbose)

        try:
            summary = self._query_llm(prompt)
        except Exception as e:
            print(f"Error querying LLM for summary: {e}", file=sys.stderr)
            summary = f"Summary failed: {e}"

        behavior = None
        if behavior_analysis:
            bprompt = self._build_behavior_prompt(incident, events, group_events)
            self._log_query("behavior analysis", incident.id, bprompt, group_events, len(events), verbose)
            try:
                behavior = self._query_llm(bprompt).replace('AI: ', '').strip()
            except Exception as e:
                print(f"Error querying LLM for behavior analysis: {e}", file=sys.stderr)
                behavior = f"Behavior analysis failed: {e}"

        return {'summary': summary, 'behavior_analysis': behavior}

    def _build_summary_prompt(self, incident: JSONIncident, events: List[JSONEvent],
                              group_events: bool = False) -> str:
        source_ip = incident.source_ips[0] if incident.source_ips else "Unknown"
        timewindow = incident.note.get('timewindow', 'Unknown')
        threat_level = incident.note.get('accumulated_threat_level', 'Unknown')
        start_time = format_time(incident.start_time)
        end_time = format_time(incident.note.get('EndTime', ''))

        if group_events:
            grouped = group_events_by_pattern(events)
            event_lines = []
            for g in grouped:
                samples_str = ', '.join(g['samples']) if g['samples'] else 'various'
                if g['count'] == 1:
                    event_lines.append(f"{g['time_range']} | {g['original_desc']}")
                else:
                    event_lines.append(f"{g['time_range']} | {g['original_desc']} ({g['count']}x similar, samples: {samples_str})")
            events_text = "\n".join(event_lines)
            event_description = f"GROUPED EVENTS ({len(grouped)} unique patterns from {len(events)} total events)"
        else:
            events_text = "\n".join(
                f"{format_time(e.start_time, short=True)} | {e.description}" for e in events
            )
            event_description = "RAW EVENTS (Time | Description)"

        return f"""You are a security analyst. Your task is to translate technical security events into clear, concise, human-readable summaries and assess their severity.

INCIDENT METADATA:
- Incident ID: {incident.id}
- Source IP: {source_ip}
- Timewindow: {timewindow}
- Accumulated Threat Level: {threat_level}
- Time Range: {start_time} to {end_time if end_time else 'ongoing'}
- Total Events: {len(events)}

{event_description}:
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

    def _build_behavior_prompt(self, incident: JSONIncident, events: List[JSONEvent],
                               group_events: bool = False) -> str:
        source_ip = incident.source_ips[0] if incident.source_ips else "Unknown"
        timewindow = incident.note.get('timewindow', 'Unknown')
        threat_level = incident.note.get('accumulated_threat_level', 'Unknown')
        start_time = format_time(incident.start_time)
        end_time = format_time(incident.note.get('EndTime', ''))
        evidence_text = build_evidence_text(events, group=group_events)

        return f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a concise, structured technical explanation of the observed network behavior.

INCIDENT METADATA:
- Incident ID: {incident.id}
- Source IP: {source_ip}
- Timewindow: {timewindow}
- Accumulated Threat Level: {threat_level}
- Time Range: {start_time} to {end_time if end_time else 'ongoing'}
- Total Events: {len(events)}

SECURITY EVIDENCE:
{evidence_text}

Output Requirements:
- Respond with ONLY the analysis content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:

**Source:** {source_ip}
**Activity:** [Brief activity type]
**Detected Flows:**
• [flow description using format: src_ip:port/proto → dest_targets (service)]
• [additional flows as needed]

**Summary:** [1-2 sentence technical summary of the behavior]

Guidelines:
- Be succinct (fewer words than raw evidence)
- Focus only on actual network activity observed
- Use consistent port/protocol notation (e.g., 80/TCP, 443/TCP)
- Express flows in compact format when possible
- Avoid high-level definitions or irrelevant metadata
- Keep technical depth consistent across all analyses
- Use bullet points for flows, structured format for sections"""

    # ------------------------------------------------------------------
    # Risk task
    # ------------------------------------------------------------------

    def _run_risk(self, incident: JSONIncident, events: List[JSONEvent],
                  group_events: bool, verbose: bool) -> Dict[str, Any]:
        cause_prompt = self._build_cause_prompt(incident, events, group_events)
        self._log_query("cause analysis", incident.id, cause_prompt, group_events, len(events), verbose)

        try:
            cause_analysis = self._query_llm(cause_prompt).replace('AI: ', '').strip()
            if '🧠 Stats:' in cause_analysis:
                cause_analysis = cause_analysis.split('🧠 Stats:')[0].strip()
        except Exception as e:
            print(f"Error querying LLM for cause analysis: {e}", file=sys.stderr)
            cause_analysis = f"Cause analysis failed: {e}"

        risk_prompt = self._build_risk_prompt(incident, events, group_events)
        self._log_query("risk assessment", incident.id, risk_prompt, group_events, len(events), verbose)

        try:
            risk_assessment = self._query_llm(risk_prompt).replace('AI: ', '').strip()
            if '🧠 Stats:' in risk_assessment:
                risk_assessment = risk_assessment.split('🧠 Stats:')[0].strip()
        except Exception as e:
            print(f"Error querying LLM for risk assessment: {e}", file=sys.stderr)
            risk_assessment = f"Risk assessment failed: {e}"

        return {'cause_analysis': cause_analysis, 'risk_assessment': risk_assessment}

    def _build_cause_prompt(self, incident: JSONIncident, events: List[JSONEvent],
                            group_events: bool = False) -> str:
        source_ip = incident.source_ips[0] if incident.source_ips else "Unknown"
        timewindow = incident.note.get('timewindow', 'Unknown')
        threat_level = incident.note.get('accumulated_threat_level', 'Unknown')
        start_time = format_time(incident.start_time)
        end_time = format_time(incident.note.get('EndTime', ''))
        evidence_text = build_evidence_text(events, group=group_events)

        return f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured analysis of possible causes.

INCIDENT METADATA:
- Incident ID: {incident.id}
- Source IP: {source_ip}
- Timewindow: {timewindow}
- Accumulated Threat Level: {threat_level}
- Time Range: {start_time} to {end_time if end_time else 'ongoing'}
- Total Events: {len(events)}

SECURITY EVIDENCE:
{evidence_text}

Output Requirements:
- Respond with ONLY the analysis content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:

**Possible Causes:**

**1. Malicious Activity:**
• [Specific attack technique or malicious cause]
• [Additional malicious possibilities if relevant]

**2. Legitimate Activity:**
• [Benign operational cause]
• [Additional legitimate possibilities if relevant]

**3. Misconfigurations:**
• [Technical misconfigurations that could cause this behavior]

**Conclusion:** [1-2 sentence assessment of most likely cause category with recommendation for further investigation]

Guidelines:
- Be succinct (fewer words than raw evidence)
- Focus on relevant causes only (attack techniques, misconfigurations, legitimate operations)
- Use precise analyst-level language
- Maintain consistent structure and depth across all analyses
- Avoid generic definitions or unnecessary context"""

    def _build_risk_prompt(self, incident: JSONIncident, events: List[JSONEvent],
                           group_events: bool = False) -> str:
        source_ip = incident.source_ips[0] if incident.source_ips else "Unknown"
        timewindow = incident.note.get('timewindow', 'Unknown')
        threat_level = incident.note.get('accumulated_threat_level', 'Unknown')
        start_time = format_time(incident.start_time)
        end_time = format_time(incident.note.get('EndTime', ''))
        evidence_text = build_evidence_text(events, group=group_events)

        return f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured risk assessment.

INCIDENT METADATA:
- Incident ID: {incident.id}
- Source IP: {source_ip}
- Timewindow: {timewindow}
- Accumulated Threat Level: {threat_level}
- Time Range: {start_time} to {end_time if end_time else 'ongoing'}
- Total Events: {len(events)}

SECURITY EVIDENCE:
{evidence_text}

Output Requirements:
- Respond with ONLY the assessment content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:

**Risk Level:** [Critical/High/Medium/Low]

**Justification:** [1-2 sentence technical justification for the risk level]

**Business Impact:** [Single clear sentence describing the most relevant business effect]

**Likelihood of Malicious Activity:** [High/Medium/Low] - [Brief rationale]

**Investigation Priority:** [Immediate/High/Medium/Low] - [Brief justification]

Guidelines:
- Use only the four risk levels: Critical, High, Medium, Low
- Keep justifications concise and technical
- Focus business impact on most relevant effect (data access, service disruption, etc.)
- Use consistent language for likelihood assessments
- Maintain uniform structure and depth across all assessments
- Avoid verbose or generic text"""

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def _query_llm(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        full_reply = ""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                full_reply += chunk.choices[0].delta.content
        return full_reply.strip()

    def _count_tokens(self, text: str) -> int:
        if not self.encoding:
            return 0
        try:
            return len(self.encoding.encode(text))
        except Exception:
            return 0

    def _log_query(self, label: str, incident_id: str, prompt: str,
                   group_events: bool, event_count: int, verbose: bool) -> None:
        if not verbose:
            return
        token_count = self._count_tokens(prompt)
        if token_count > 0:
            suffix = f", grouped from {event_count} events" if group_events else ""
            print(f"Querying LLM for {label} of incident {incident_id}... ({token_count} tokens{suffix})",
                  file=sys.stderr)
        else:
            print(f"Querying LLM for {label} of incident {incident_id}...", file=sys.stderr)


# ------------------------------------------------------------------
# Output filename helpers
# ------------------------------------------------------------------

def _model_name_for_filename(model: str) -> str:
    return re.sub(r'/.*$', '', model).replace('/', '_')


def _default_output(input_file: str, task: str, model: str) -> str:
    base = input_file.removesuffix('.jsonl') if input_file.endswith('.jsonl') else input_file
    model_name = _model_name_for_filename(model)
    if task == 'summary':
        return f"{base}.llm.{model_name}.json"
    elif task == 'risk':
        return f"{base}.cause_risk.{model_name}.json"
    else:
        return f"{base}.inference.{model_name}.json"


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Unified LLM inference for Slips IDEA-format JSONL alert files'
    )
    parser.add_argument('json_file', help='Input JSONL file (IDEA format)')
    parser.add_argument('--task', choices=['summary', 'risk', 'both'], default='summary',
                        help='Analysis task to run (default: summary)')
    parser.add_argument('--model', default=DEFAULT_MODEL,
                        help=f'LLM model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL,
                        help=f'LLM API base URL (default: {DEFAULT_BASE_URL})')
    parser.add_argument('--output', '-o', help='Output file (default: auto-named based on task and model)')
    parser.add_argument('--incident-id', '-i', help='Analyze specific incident by ID')
    parser.add_argument('--group-events', action='store_true',
                        help='Group similar events to reduce token count')
    parser.add_argument('--behavior-analysis', action='store_true',
                        help='Generate behavior analysis (summary/both tasks only)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    output_file = args.output or _default_output(args.json_file, args.task, args.model)

    if args.verbose:
        print(f"Input:    {args.json_file}", file=sys.stderr)
        print(f"Task:     {args.task}", file=sys.stderr)
        print(f"Model:    {args.model}", file=sys.stderr)
        print(f"Base URL: {args.base_url}", file=sys.stderr)
        print(f"Output:   {output_file}", file=sys.stderr)

    alert_parser = AlertJSONParser()
    alert_parser.parse_file(args.json_file)

    if args.verbose:
        print(f"Found {len(alert_parser.incidents)} incidents and {len(alert_parser.events)} events",
              file=sys.stderr)

    incidents_to_process = alert_parser.incidents
    if args.incident_id:
        incidents_to_process = [i for i in alert_parser.incidents if i.id == args.incident_id]
        if not incidents_to_process:
            print(f"Error: Incident {args.incident_id} not found", file=sys.stderr)
            sys.exit(1)

    engine = InferenceEngine(args.model, args.base_url)
    output_data = []

    for incident in incidents_to_process:
        events = alert_parser.get_incident_events(incident)
        analysis = engine.run(
            incident, events,
            task=args.task,
            group_events=args.group_events,
            behavior_analysis=args.behavior_analysis,
            verbose=args.verbose,
        )

        source_ip = incident.source_ips[0] if incident.source_ips else "Unknown"
        timewindow = incident.note.get('timewindow', 'Unknown')
        threat_level = incident.note.get('accumulated_threat_level', 0)
        start_time = format_time(incident.start_time)
        end_time = format_time(incident.note.get('EndTime', ''))
        timeline = f"{start_time} to {end_time}" if end_time else start_time

        record: Dict[str, Any] = {
            "incident_id": incident.id,
            "source_ip": source_ip,
            "timewindow": str(timewindow),
            "timeline": timeline,
            "threat_level": threat_level,
            "event_count": len(events),
        }
        record.update(analysis)
        output_data.append(record)

    output_json = json.dumps(output_data, indent=2, ensure_ascii=False)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_json)
        if args.verbose:
            print(f"Output written to: {output_file}", file=sys.stderr)
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

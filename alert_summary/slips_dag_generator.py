#!/usr/bin/env python3
"""
Slips Evidence Log DAG Generator

This script parses Slips evidence logs and generates a textual DAG (Directed Acyclic Graph)
showing the chronological sequence of security events for a specific IP address.

Usage:
    python slips_dag_generator.py <log_file> <target_ip> [--output <output_file>]

Example:
    python slips_dag_generator.py slips-evidence.log 192.168.1.113
    python slips_dag_generator.py slips-evidence.log 192.168.1.113 --output dag_output.txt
"""

import re
import argparse
import sys
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json


@dataclass
class EvidenceEvent:
    """Represents a single evidence event from the Slips log."""
    timestamp: str
    ip_address: str
    event_type: str
    description: str
    threat_level: str
    confidence: float
    raw_details: Dict[str, Any]
    
    def __str__(self) -> str:
        return f"{self.timestamp} -> {self.event_type}: {self.description}"


@dataclass
class Alert:
    """Represents a Slips alert/analysis with associated evidence events."""
    alert_timestamp: str
    ip_address: str
    timewindow_id: str
    timewindow_start: str
    timewindow_end: str
    evidence_events: List[EvidenceEvent]
    
    def __str__(self) -> str:
        return f"Alert for {self.ip_address} in timewindow {self.timewindow_id} ({len(self.evidence_events)} events)"


class SlipsLogParser:
    """Parser for Slips evidence logs."""
    
    def __init__(self):
        # Regex patterns for different evidence types
        self.patterns = {
            'timestamp': r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+)',
            'profile': r'profile_([^\s]+)',
            'threat_level': r'threat level (\w+)',
            'confidence': r'confidence ([\d.]+)',
            'port_scan': r'horizontal port scan to port\s+(\d+/\w+).*?(\d+) unique dst IPs.*?(\d+) packets',
            'cc_channel': r'C&C channel.*?destination IP: ([\d.]+).*?port:.*?(\d+).*?score: ([\d.]+)',
            'blacklisted_ip': r'connection to blacklisted IP ([\d.]+).*?AS: ([^,]*)',
            'private_ip': r'Connecting to private IP: ([\d.]+).*?port: (\d+)',
            'non_http': r'non-HTTP established connection to port (\d+).*?destination IP: ([\d.]+)',
            'non_ssl': r'non-SSL established connection to port (\d+).*?destination IP: ([\d.]+)',
            'no_dns': r'connection without DNS resolution to IP: ([\d.]+)',
            'unencrypted_http': r'Unencrypted HTTP traffic.*?to ([\d.]+)',
            'malicious_detection': r'IP ([\d.]+)\s+detected as malicious'
        }
    
    def parse_log(self, log_file: str, target_ip: str) -> List[EvidenceEvent]:
        """Parse the Slips log file and extract events for the target IP."""
        events = []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"Error: Log file '{log_file}' not found.")
            return []
        except Exception as e:
            print(f"Error reading log file: {e}")
            return []
        
        # Detect log format by looking for characteristic patterns
        log_format = self._detect_log_format(lines)
        
        if log_format == "grouped_alerts":
            events = self._parse_grouped_alerts_format(lines, target_ip)
        else:
            # Original format
            for line_num, line in enumerate(lines, 1):
                try:
                    event = self._parse_line(line, target_ip)
                    if event:
                        events.append(event)
                except Exception as e:
                    print(f"Warning: Error parsing line {line_num}: {e}")
                    continue
        
        # Sort events by timestamp
        events.sort(key=lambda x: x.timestamp)
        return events
    
    def _parse_line(self, line: str, target_ip: str) -> Optional[EvidenceEvent]:
        """Parse a single line and extract evidence event if relevant."""
        # Check if it's an evidence line - look for [Evidence] marker
        if '[Evidence]' not in line:
            return None
        
        content = line.strip()
        
        # Extract timestamp
        timestamp_match = re.search(self.patterns['timestamp'], content)
        if not timestamp_match:
            return None
        timestamp = timestamp_match.group(1)
        
        # Check if this line is about our target IP
        profile_match = re.search(self.patterns['profile'], content)
        if not profile_match:
            return None
        
        ip_in_profile = profile_match.group(1)
        
        # Also check for malicious detection lines
        malicious_match = re.search(self.patterns['malicious_detection'], content)
        if malicious_match:
            detected_ip = malicious_match.group(1)
            if detected_ip == target_ip:
                return EvidenceEvent(
                    timestamp=timestamp,
                    ip_address=target_ip,
                    event_type="Malicious Detection",
                    description=f"IP {target_ip} detected as malicious",
                    threat_level="critical",
                    confidence=1.0,
                    raw_details={"detection_type": "malicious_ip"}
                )
        
        # Skip if not our target IP
        if ip_in_profile != target_ip:
            return None
        
        # Extract threat level and confidence
        threat_level = "unknown"
        confidence = 0.0
        
        threat_match = re.search(self.patterns['threat_level'], content)
        if threat_match:
            threat_level = threat_match.group(1)
        
        confidence_match = re.search(self.patterns['confidence'], content)
        if confidence_match:
            confidence = float(confidence_match.group(1))
        
        # Determine event type and extract details
        event_type, description, details = self._classify_event(content)
        
        return EvidenceEvent(
            timestamp=timestamp,
            ip_address=target_ip,
            event_type=event_type,
            description=description,
            threat_level=threat_level,
            confidence=confidence,
            raw_details=details
        )
    
    def _classify_event(self, content: str) -> tuple:
        """Classify the event type and extract relevant details."""
        # Port scan detection
        port_scan_match = re.search(self.patterns['port_scan'], content)
        if port_scan_match:
            port = port_scan_match.group(1)
            targets = port_scan_match.group(2)
            packets = port_scan_match.group(3)
            return (
                "Port Scan",
                f"Horizontal scan to port {port} (Targets: {targets} IPs, Packets: {packets})",
                {"port": port, "targets": targets, "packets": packets}
            )
        
        # Check for other port scan patterns (Zeek-based)
        if "horizontal port scan" in content and "unique dst IPs" in content:
            # Extract details manually for the more complex patterns
            port_info = "unknown"
            targets_info = "unknown"
            packets_info = "unknown"
            
            if " to port " in content:
                port_part = content.split(" to port ")[1].split()[0]
                port_info = port_part.replace("/TCP", "").replace("/UDP", "")
            
            if " unique dst IPs" in content:
                parts = content.split(" unique dst IPs")
                before = parts[0].split()
                for i, part in enumerate(before):
                    if part.isdigit():
                        targets_info = part
                        break
            
            if "packets sent:" in content:
                packets_part = content.split("packets sent:")[1].split()[0].replace(".", "")
                if packets_part.isdigit():
                    packets_info = packets_part
            
            return (
                "Port Scan",
                f"Horizontal scan to port {port_info} (Targets: {targets_info} IPs, Packets: {packets_info})",
                {"port": port_info, "targets": targets_info, "packets": packets_info}
            )
        
        # C&C channel detection
        cc_match = re.search(self.patterns['cc_channel'], content)
        if cc_match:
            dest_ip = cc_match.group(1)
            port = cc_match.group(2)
            score = cc_match.group(3)
            return (
                "C&C Channel",
                f"Connection to {dest_ip}:{port} (Score: {score})",
                {"destination": dest_ip, "port": port, "score": score}
            )
        
        # Blacklisted IP connection
        blacklist_match = re.search(self.patterns['blacklisted_ip'], content)
        if blacklist_match:
            dest_ip = blacklist_match.group(1)
            as_info = blacklist_match.group(2) if len(blacklist_match.groups()) > 1 else "Unknown"
            return (
                "Blacklisted IP",
                f"Connection to blacklisted {dest_ip} (AS: {as_info})",
                {"destination": dest_ip, "as_info": as_info}
            )
        
        # Private IP connection
        private_match = re.search(self.patterns['private_ip'], content)
        if private_match:
            dest_ip = private_match.group(1)
            port = private_match.group(2)
            return (
                "Private IP Connection",
                f"Connection to private IP {dest_ip}:{port}",
                {"destination": dest_ip, "port": port}
            )
        
        # Non-HTTP connection
        non_http_match = re.search(self.patterns['non_http'], content)
        if non_http_match:
            port = non_http_match.group(1)
            dest_ip = non_http_match.group(2)
            return (
                "Suspicious Connection",
                f"Non-HTTP connection to {dest_ip}:{port}",
                {"destination": dest_ip, "port": port, "type": "non_http"}
            )
        
        # Non-SSL connection
        non_ssl_match = re.search(self.patterns['non_ssl'], content)
        if non_ssl_match:
            port = non_ssl_match.group(1)
            dest_ip = non_ssl_match.group(2)
            return (
                "Suspicious Connection",
                f"Non-SSL connection to {dest_ip}:{port}",
                {"destination": dest_ip, "port": port, "type": "non_ssl"}
            )
        
        # No DNS resolution
        no_dns_match = re.search(self.patterns['no_dns'], content)
        if no_dns_match:
            dest_ip = no_dns_match.group(1)
            return (
                "DNS Issue",
                f"Connection without DNS resolution to {dest_ip}",
                {"destination": dest_ip, "type": "no_dns"}
            )
        
        # Unencrypted HTTP
        unencrypted_match = re.search(self.patterns['unencrypted_http'], content)
        if unencrypted_match:
            dest_ip = unencrypted_match.group(1)
            return (
                "Unencrypted Traffic",
                f"Unencrypted HTTP traffic to {dest_ip}",
                {"destination": dest_ip, "type": "unencrypted_http"}
            )
        
        # Generic evidence (fallback)
        return (
            "Generic Evidence",
            content.split("last evidence found was:")[-1].strip() if "last evidence found was:" in content else "Unknown evidence",
            {"raw_content": content}
        )
    
    def discover_all_ips(self, log_file: str) -> List[str]:
        """Discover all IP addresses with evidence in the log file."""
        ips = set()
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"Error: Log file '{log_file}' not found.")
            return []
        except Exception as e:
            print(f"Error reading log file: {e}")
            return []
        
        # Detect log format
        log_format = self._detect_log_format(lines)
        
        if log_format == "grouped_alerts":
            # Parse grouped alerts format
            for line in lines:
                clean_line = self._strip_ansi_codes(line)
                if "detected as malicious in timewindow" in clean_line:
                    ip_match = re.search(r'IP ([\d.]+)\s+detected as malicious', clean_line)
                    if ip_match:
                        ips.add(ip_match.group(1))
        else:
            # Original format
            for line in lines:
                # Check if it's an evidence line
                if '[Evidence]' not in line:
                    continue
                
                # Extract profile IP
                profile_match = re.search(self.patterns['profile'], line)
                if profile_match:
                    ip = profile_match.group(1)
                    ips.add(ip)
        
        # Sort IPs for consistent output
        return sorted(list(ips))
    
    def parse_alerts(self, log_file: str, target_ip: Optional[str] = None) -> List[Alert]:
        """Parse the Slips log file and extract alerts with their evidence."""
        alerts = []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"Error: Log file '{log_file}' not found.")
            return []
        except Exception as e:
            print(f"Error reading log file: {e}")
            return []
        
        # Detect log format
        log_format = self._detect_log_format(lines)
        
        if log_format == "grouped_alerts":
            alerts = self._parse_alerts_from_grouped_format(lines, target_ip)
        else:
            # For original format, convert to legacy evidence-based approach
            print("Warning: Alert-based parsing not supported for original format. Use IP-based mode instead.")
            return []
        
        # Sort alerts by timestamp
        alerts.sort(key=lambda x: x.alert_timestamp)
        return alerts
    
    def _detect_log_format(self, lines: List[str]) -> str:
        """Detect the format of the Slips log file."""
        # Look for grouped alerts format indicators
        for line in lines[:100]:  # Check first 100 lines
            if "detected as malicious in timewindow" in line and "given the following evidence:" in line:
                return "grouped_alerts"
            if "- Detected" in line:
                return "grouped_alerts"
        
        # Look for original format indicators
        for line in lines[:100]:
            if "accumulated_threat_level for profile_" in line:
                return "original"
        
        # Default to original format
        return "original"
    
    def _parse_grouped_alerts_format(self, lines: List[str], target_ip: str) -> List[EvidenceEvent]:
        """Parse the grouped alerts format where evidence is listed under detection alerts."""
        events = []
        current_timestamp = None
        current_ip = None
        in_evidence_block = False
        current_evidence_text = ""
        
        for line_num, line in enumerate(lines, 1):
            try:
                # Strip ANSI color codes
                clean_line = self._strip_ansi_codes(line.strip())
                
                # Check for detection alert header
                if "detected as malicious in timewindow" in clean_line:
                    # Extract timestamp and IP
                    timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
                    ip_match = re.search(r'IP ([\d.]+)\s+detected as malicious', clean_line)
                    
                    if timestamp_match and ip_match:
                        current_timestamp = timestamp_match.group(1)
                        current_ip = ip_match.group(1)
                        in_evidence_block = (current_ip == target_ip)
                    continue
                
                # Check for "given the following evidence:" line
                if in_evidence_block and "given the following evidence:" in clean_line:
                    continue
                
                # Check for evidence items
                if in_evidence_block and current_timestamp and current_ip == target_ip:
                    # Handle both "- Detected" and "\t- Detected" formats
                    if clean_line.startswith("- Detected ") or clean_line.startswith("\t- Detected "):
                        # If we have accumulated text from previous evidence, process it
                        if current_evidence_text:
                            event = self._parse_evidence_item(current_evidence_text, current_timestamp, current_ip)
                            if event:
                                events.append(event)
                        
                        # Start new evidence item - remove prefix
                        if clean_line.startswith("\t- Detected "):
                            current_evidence_text = clean_line[12:]  # Remove "\t- Detected "
                        else:
                            current_evidence_text = clean_line[11:]  # Remove "- Detected "
                        
                    elif current_evidence_text and clean_line and not clean_line.startswith("-") and not clean_line.startswith("\t-"):
                        # Continuation line (like "ps" or "lips")
                        current_evidence_text += " " + clean_line
                        
                    elif clean_line == "" or (clean_line and not clean_line.startswith("-") and not current_evidence_text):
                        # End of evidence block
                        if current_evidence_text:
                            event = self._parse_evidence_item(current_evidence_text, current_timestamp, current_ip)
                            if event:
                                events.append(event)
                            current_evidence_text = ""
                        
                        in_evidence_block = False
                        current_timestamp = None
                        current_ip = None
                        
            except Exception as e:
                print(f"Warning: Error parsing line {line_num}: {e}")
                continue
        
        # Process any remaining evidence text
        if current_evidence_text and current_timestamp and current_ip == target_ip:
            event = self._parse_evidence_item(current_evidence_text, current_timestamp, current_ip)
            if event:
                events.append(event)
        
        return events
    
    def _parse_alerts_from_grouped_format(self, lines: List[str], target_ip: Optional[str] = None) -> List[Alert]:
        """Parse alerts from grouped format, grouping evidence by alert/timewindow."""
        alerts = []
        current_alert = None
        
        for line_num, line in enumerate(lines, 1):
            try:
                # Strip ANSI color codes
                clean_line = self._strip_ansi_codes(line.strip())
                
                # Check for alert header
                if "detected as malicious in timewindow" in clean_line:
                    # Save previous alert if it exists
                    if current_alert and (not target_ip or current_alert.ip_address == target_ip):
                        alerts.append(current_alert)
                    
                    # Parse new alert header
                    alert_timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+)', line)
                    ip_match = re.search(r'IP ([\d.]+)\s+detected as malicious', clean_line)
                    timewindow_match = re.search(r'timewindow (\d+)', clean_line)
                    timewindow_period_match = re.search(r'\(start ([^,]+), stop ([^)]+)\)', clean_line)
                    
                    if alert_timestamp_match and ip_match and timewindow_match:
                        alert_timestamp = alert_timestamp_match.group(1)
                        ip_address = ip_match.group(1)
                        timewindow_id = timewindow_match.group(1)
                        
                        # Extract timewindow period if available
                        if timewindow_period_match:
                            timewindow_start = timewindow_period_match.group(1)
                            timewindow_end = timewindow_period_match.group(2)
                        else:
                            timewindow_start = "unknown"
                            timewindow_end = "unknown"
                        
                        # Create new alert
                        current_alert = Alert(
                            alert_timestamp=alert_timestamp,
                            ip_address=ip_address,
                            timewindow_id=timewindow_id,
                            timewindow_start=timewindow_start,
                            timewindow_end=timewindow_end,
                            evidence_events=[]
                        )
                    continue
                
                # Check for evidence items within an alert
                if current_alert and "given the following evidence:" in clean_line:
                    continue
                
                # Parse evidence items
                if current_alert and (clean_line.startswith("- Detected ") or clean_line.startswith("\t- Detected ")):
                    # Extract evidence text
                    if clean_line.startswith("\t- Detected "):
                        evidence_text = clean_line[12:]  # Remove "\t- Detected "
                    else:
                        evidence_text = clean_line[11:]  # Remove "- Detected "
                    
                    # Parse evidence into EvidenceEvent
                    evidence_event = self._parse_evidence_item(evidence_text, current_alert.alert_timestamp, current_alert.ip_address)
                    if evidence_event:
                        current_alert.evidence_events.append(evidence_event)
                
            except Exception as e:
                print(f"Warning: Error parsing line {line_num}: {e}")
                continue
        
        # Don't forget the last alert
        if current_alert and (not target_ip or current_alert.ip_address == target_ip):
            alerts.append(current_alert)
        
        return alerts
    
    def _strip_ansi_codes(self, text: str) -> str:
        """Strip ANSI color codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _parse_evidence_item(self, evidence_text: str, timestamp: str, ip: str) -> Optional[EvidenceEvent]:
        """Parse a single evidence item from the grouped format."""
        # Determine threat level and confidence from the text
        threat_level = "medium"  # Default
        confidence = 0.5  # Default
        
        # Extract threat level
        if "Threat Level:" in evidence_text:
            threat_match = re.search(r'Threat Level:\s*(\w+)', evidence_text)
            if threat_match:
                threat_level = threat_match.group(1).lower()
        elif "threat level:" in evidence_text:
            # Alternative format: "threat level: medium."
            threat_match = re.search(r'threat level:\s*(\w+)', evidence_text)
            if threat_match:
                threat_level = threat_match.group(1).lower().rstrip('.')
        
        # Extract confidence
        if "Confidence:" in evidence_text:
            conf_match = re.search(r'Confidence:\s*([\d.]+)', evidence_text)
            if conf_match:
                conf_str = conf_match.group(1).rstrip('.')  # Remove trailing period
                confidence = float(conf_str)
        else:
            # Some formats don't have confidence, use default based on threat level
            confidence_map = {'low': 0.3, 'medium': 0.6, 'high': 0.8, 'critical': 0.9}
            confidence = confidence_map.get(threat_level, 0.5)
        
        # Classify the evidence type and extract details
        event_type, description, details = self._classify_grouped_evidence(evidence_text)
        
        return EvidenceEvent(
            timestamp=timestamp,
            ip_address=ip,
            event_type=event_type,
            description=description,
            threat_level=threat_level,
            confidence=confidence,
            raw_details=details
        )
    
    def _classify_grouped_evidence(self, evidence_text: str) -> tuple:
        """Classify evidence from grouped format."""
        # Port scan detection
        if "horizontal port scan to port" in evidence_text:
            port_match = re.search(r'port\s+(\d+/\w+)', evidence_text)
            targets_match = re.search(r'to\s+(\d+)\s+unique dst IPs', evidence_text)
            packets_match = re.search(r'Total packets sent:\s+(\d+)', evidence_text)
            
            port = port_match.group(1) if port_match else "unknown"
            targets = targets_match.group(1) if targets_match else "unknown"
            packets = packets_match.group(1) if packets_match else "unknown"
            
            return (
                "Port Scan",
                f"Horizontal scan to port {port} (Targets: {targets} IPs, Packets: {packets})",
                {"port": port, "targets": targets, "packets": packets}
            )
        
        # Private IP connection
        elif "Connecting to private IP:" in evidence_text:
            ip_match = re.search(r'private IP:\s*([\d.]+)', evidence_text)
            port_match = re.search(r'destination port:\s*(\d+)', evidence_text)
            
            dest_ip = ip_match.group(1) if ip_match else "unknown"
            port = port_match.group(1) if port_match else "unknown"
            
            return (
                "Private IP Connection",
                f"Connection to private IP {dest_ip}:{port}",
                {"destination": dest_ip, "port": port}
            )
        
        # C&C channel detection
        elif "C&C channel" in evidence_text:
            ip_match = re.search(r'destination IP:\s*([\d.]+)', evidence_text)
            port_match = re.search(r'port:\s*.*?(\d+)', evidence_text)
            score_match = re.search(r'score:\s*([\d.]+)', evidence_text)
            
            dest_ip = ip_match.group(1) if ip_match else "unknown"
            port = port_match.group(1) if port_match else "unknown"
            score = score_match.group(1) if score_match else "unknown"
            
            return (
                "C&C Channel",
                f"Connection to {dest_ip}:{port} (Score: {score})",
                {"destination": dest_ip, "port": port, "score": score}
            )
        
        # Blacklisted IP
        elif "blacklisted IP" in evidence_text:
            ip_match = re.search(r'blacklisted IP\s*([\d.]+)', evidence_text)
            
            dest_ip = ip_match.group(1) if ip_match else "unknown"
            
            return (
                "Blacklisted IP",
                f"Connection to blacklisted {dest_ip}",
                {"destination": dest_ip}
            )
        
        # Non-SSL connection
        elif "non-SSL established connection" in evidence_text:
            port_match = re.search(r'port (\d+)', evidence_text)
            ip_match = re.search(r'destination IP:\s*([\d.]+)', evidence_text)
            
            port = port_match.group(1) if port_match else "unknown"
            dest_ip = ip_match.group(1) if ip_match else "unknown"
            
            return (
                "Suspicious Connection",
                f"Non-SSL connection to {dest_ip}:{port}",
                {"destination": dest_ip, "port": port, "type": "non_ssl"}
            )
        
        # Unencrypted HTTP traffic
        elif "Unencrypted HTTP traffic" in evidence_text:
            # Format: "Unencrypted HTTP traffic from 10.0.2.15 to 216.58.201.110"
            from_match = re.search(r'from ([\d.]+)', evidence_text)
            to_match = re.search(r'to ([\d.]+)', evidence_text)
            
            source_ip = from_match.group(1) if from_match else "unknown"
            dest_ip = to_match.group(1) if to_match else "unknown"
            
            return (
                "Unencrypted Traffic",
                f"Unencrypted HTTP from {source_ip} to {dest_ip}",
                {"source": source_ip, "destination": dest_ip, "type": "unencrypted_http"}
            )
        
        # Multiple user agents
        elif "Using multiple user-agents" in evidence_text:
            return (
                "Suspicious Behavior",
                "Using multiple user-agents",
                {"type": "multiple_user_agents", "raw_content": evidence_text}
            )
        
        # Generic evidence (fallback)
        return (
            "Generic Evidence",
            evidence_text[:100] + "..." if len(evidence_text) > 100 else evidence_text,
            {"raw_content": evidence_text}
        )


class DAGGenerator:
    """Generates textual DAG from parsed evidence events."""
    
    def __init__(self, compact=False, minimal=False, pattern=False, group_time=None, include_threat_level=False):
        self.compact = compact
        self.minimal = minimal
        self.pattern = pattern
        self.group_time = group_time
        self.include_threat_level = include_threat_level
        self.threat_level_priority = {
            'critical': 5,
            'high': 4,
            'medium': 3,
            'low': 2,
            'info': 1,
            'unknown': 0
        }
        self.threat_symbols = {
            'critical': '🔴',
            'high': '🟠', 
            'medium': '🟡',
            'low': '🔵',
            'info': '⚪',
            'unknown': '⚫'
        }
    
    def generate_dag(self, events: List[EvidenceEvent], target_ip: str) -> str:
        """Generate a textual DAG from the evidence events."""
        if not events:
            return f"No evidence found for IP: {target_ip}"
        
        if self.minimal:
            return self._generate_minimal_format(events, target_ip)
        elif self.pattern:
            return self._generate_pattern_format(events, target_ip)
        elif self.compact:
            return self._generate_compact_format(events, target_ip)
        else:
            return self._generate_verbose_format(events, target_ip)
    
    def generate_dag_for_alert(self, alert: Alert) -> str:
        """Generate a textual DAG for a single alert/analysis."""
        if not alert.evidence_events:
            return f"No evidence found for alert {alert.timewindow_id} of IP: {alert.ip_address}"
        
        # Create header with alert information
        header = f"{alert.ip_address} - Analysis {alert.timewindow_id} ({alert.alert_timestamp})"
        if alert.timewindow_start != "unknown":
            header += f"\nTimewindow: {alert.timewindow_start} to {alert.timewindow_end}"
        
        # Generate DAG using existing format logic
        if self.minimal:
            dag_content = self._generate_minimal_format_for_alert(alert)
        elif self.pattern:
            dag_content = self._generate_pattern_format_for_alert(alert)
        elif self.compact:
            dag_content = self._generate_compact_format_for_alert(alert)
        else:
            dag_content = self._generate_verbose_format_for_alert(alert)
        
        return f"{header}\n{dag_content}"
    
    def _generate_verbose_format(self, events: List[EvidenceEvent], target_ip: str) -> str:
        """Generate the original verbose DAG format."""
        # Group events by time proximity to reduce clutter
        grouped_events = self._group_events(events)
        
        # Generate the DAG structure
        dag_lines = [f"{target_ip}"]
        dag_lines.append("  |")
        
        for i, event_group in enumerate(grouped_events):
            is_last = (i == len(grouped_events) - 1)
            dag_lines.extend(self._format_event_group(event_group, is_last))
        
        return "\n".join(dag_lines)
    
    def _generate_compact_format(self, events: List[EvidenceEvent], target_ip: str) -> str:
        """Generate compact single-line format."""
        lines = [f"{target_ip}"]
        
        # Group similar events for better aggregation
        aggregated = self._aggregate_events(events)
        
        for i, event in enumerate(aggregated):
            is_last = (i == len(aggregated) - 1)
            symbol = "└─" if is_last else "├─"
            
            # Shorter timestamp (remove date and microseconds)
            time_short = event.timestamp.split()[1][:8]  # HH:MM:SS
            
            # Compact threat info
            if self.include_threat_level:
                threat_short = f"[{event.threat_level.upper()[:3]}/{event.confidence}]"
            else:
                threat_short = f"[{event.confidence}]"
            
            # Concise description
            desc = self._make_description_concise(event)
            
            lines.append(f"{symbol} {time_short} → {desc} {threat_short}")
        
        return "\n".join(lines)
    
    def _generate_minimal_format(self, events: List[EvidenceEvent], target_ip: str) -> str:
        """Generate minimal bullet-point format."""
        lines = [f"{target_ip} Attack Summary:"]
        
        # Aggregate by event type
        type_summary = self._summarize_by_type(events)
        
        # Get time range
        start_time = events[0].timestamp.split()[1][:5]  # HH:MM
        end_time = events[-1].timestamp.split()[1][:5]   # HH:MM
        
        high_priority_types = ['Port Scan', 'C&C Channel', 'DNS Issue']
        
        for event_type in high_priority_types:
            if event_type in type_summary:
                info = type_summary[event_type]
                if self.include_threat_level:
                    lines.append(f"• {start_time} - {info['summary']} [{info['max_threat'].upper()}]")
                else:
                    lines.append(f"• {start_time} - {info['summary']}")
        
        # Add other significant events
        other_types = [t for t in type_summary if t not in high_priority_types and type_summary[t]['count'] > 5]
        for event_type in other_types[:2]:  # Limit to 2 additional types
            info = type_summary[event_type]
            if self.include_threat_level:
                lines.append(f"• {start_time} - {info['summary']} [{info['max_threat'].upper()}]")
            else:
                lines.append(f"• {start_time} - {info['summary']}")
        
        # Add summary
        duration_hours = self._calculate_duration_hours(events)
        total_events = len(events)
        
        lines.append(f"• Duration: {duration_hours:.1f} hours, {total_events} events")
        
        # Only include risk analysis if threat levels are enabled
        if self.include_threat_level:
            risk_level, rationale = self._calculate_comprehensive_risk_level(events)
            lines.append(f"• Risk: {risk_level} - {rationale}")
        
        return "\n".join(lines)
    
    def _generate_pattern_format(self, events: List[EvidenceEvent], target_ip: str) -> str:
        """Generate attack pattern analysis format."""
        lines = [f"{target_ip} - Attack Pattern Analysis"]
        
        # Group events into phases based on time and behavior
        phases = self._identify_attack_phases(events)
        
        for i, phase in enumerate(phases, 1):
            phase_name = phase['name']
            time_range = phase['time_range']
            activities = phase['activities']
            
            lines.append(f"Phase {i} ({time_range}): {phase_name}")
            for activity in activities:
                lines.append(f"• {activity}")
            lines.append("")  # Empty line between phases
        
        return "\n".join(lines).rstrip()
    
    def _generate_compact_format_for_alert(self, alert: Alert) -> str:
        """Generate compact format for a single alert."""
        events = alert.evidence_events
        lines = []
        
        # Group similar events for better aggregation
        aggregated = self._aggregate_events(events)
        
        for i, event in enumerate(aggregated):
            is_last = (i == len(aggregated) - 1)
            symbol = "└─" if is_last else "├─"
            
            # Shorter timestamp (remove date and microseconds)
            time_short = event.timestamp.split()[1][:8]  # HH:MM:SS
            
            # Compact threat info
            if self.include_threat_level:
                threat_short = f"[{event.threat_level.upper()[:3]}/{event.confidence}]"
            else:
                threat_short = f"[{event.confidence}]"
            
            # Concise description
            desc = self._make_description_concise(event)
            
            lines.append(f"{symbol} {time_short} → {desc} {threat_short}")
        
        return "\n".join(lines)
    
    def _generate_minimal_format_for_alert(self, alert: Alert) -> str:
        """Generate minimal format for a single alert."""
        events = alert.evidence_events
        if not events:
            return "No evidence events"
        
        lines = []
        
        # Aggregate by event type
        type_summary = self._summarize_by_type(events)
        
        # Get time range
        start_time = events[0].timestamp.split()[1][:5]  # HH:MM
        
        high_priority_types = ['Port Scan', 'C&C Channel', 'DNS Issue']
        
        for event_type in high_priority_types:
            if event_type in type_summary:
                info = type_summary[event_type]
                if self.include_threat_level:
                    lines.append(f"• {start_time} - {info['summary']} [{info['max_threat'].upper()}]")
                else:
                    lines.append(f"• {start_time} - {info['summary']}")
        
        # Add other significant events
        other_types = [t for t in type_summary if t not in high_priority_types and type_summary[t]['count'] > 2]
        for event_type in other_types[:2]:  # Limit to 2 additional types
            info = type_summary[event_type]
            if self.include_threat_level:
                lines.append(f"• {start_time} - {info['summary']} [{info['max_threat'].upper()}]")
            else:
                lines.append(f"• {start_time} - {info['summary']}")
        
        # Add summary
        total_events = len(events)
        lines.append(f"• Evidence: {total_events} events in analysis")
        
        # Only include risk analysis if threat levels are enabled
        if self.include_threat_level:
            risk_level, rationale = self._calculate_comprehensive_risk_level(events)
            lines.append(f"• Risk: {risk_level} - {rationale}")
        
        return "\n".join(lines)
    
    def _generate_verbose_format_for_alert(self, alert: Alert) -> str:
        """Generate verbose format for a single alert."""
        events = alert.evidence_events
        # Group events by time proximity to reduce clutter
        grouped_events = self._group_events(events)
        
        # Generate the DAG structure
        dag_lines = []
        
        for i, event_group in enumerate(grouped_events):
            is_last = (i == len(grouped_events) - 1)
            dag_lines.extend(self._format_event_group(event_group, is_last))
        
        return "\n".join(dag_lines)
    
    def _generate_pattern_format_for_alert(self, alert: Alert) -> str:
        """Generate pattern analysis format for a single alert."""
        events = alert.evidence_events
        lines = []
        
        # Group events into phases based on time and behavior
        phases = self._identify_attack_phases(events)
        
        for i, phase in enumerate(phases, 1):
            phase_name = phase['name']
            time_range = phase['time_range']
            activities = phase['activities']
            
            lines.append(f"Phase {i} ({time_range}): {phase_name}")
            for activity in activities:
                lines.append(f"• {activity}")
            if i < len(phases):  # Don't add empty line after last phase
                lines.append("")
        
        return "\n".join(lines)
    
    def _group_events(self, events: List[EvidenceEvent]) -> List[List[EvidenceEvent]]:
        """Group events that occur within a short time window."""
        if not events:
            return []
        
        grouped = []
        current_group = [events[0]]
        
        for event in events[1:]:
            # Simple time-based grouping (events within same minute)
            if (event.timestamp[:16] == current_group[0].timestamp[:16] and 
                event.event_type == current_group[0].event_type):
                current_group.append(event)
            else:
                grouped.append(current_group)
                current_group = [event]
        
        if current_group:
            grouped.append(current_group)
        
        return grouped
    
    def _format_event_group(self, events: List[EvidenceEvent], is_last: bool) -> List[str]:
        """Format a group of events for the DAG."""
        lines = []
        
        if len(events) == 1:
            # Single event
            event = events[0]
            lines.append(f"  |-- {event.timestamp} ---> {event.event_type}: {event.description}")
            if self.include_threat_level:
                lines.append(f"  |                            Threat Level: {event.threat_level} | Confidence: {event.confidence}")
            else:
                lines.append(f"  |                            Confidence: {event.confidence}")
        else:
            # Multiple similar events
            event = events[0]
            lines.append(f"  |-- {event.timestamp} ---> {event.event_type}: {event.description}")
            if self.include_threat_level:
                lines.append(f"  |                            Threat Level: {event.threat_level} | Confidence: {event.confidence}")
            else:
                lines.append(f"  |                            Confidence: {event.confidence}")
            lines.append(f"  |                            (+ {len(events)-1} similar events)")
        
        if not is_last:
            lines.append("  |")
        
        return lines
    
    def generate_summary(self, events: List[EvidenceEvent]) -> str:
        """Generate a summary of the events."""
        if not events:
            return "No events to summarize."
        
        # Count event types
        event_counts = {}
        threat_levels = {}
        
        for event in events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            threat_levels[event.threat_level] = threat_levels.get(event.threat_level, 0) + 1
        
        summary = [
            f"Summary of {len(events)} evidence events:",
            "",
            "Event Types:",
        ]
        
        for event_type, count in sorted(event_counts.items()):
            summary.append(f"  - {event_type}: {count}")
        
        if self.include_threat_level:
            summary.extend([
                "",
                "Threat Levels:",
            ])
            
            for threat_level, count in sorted(threat_levels.items(), 
                                            key=lambda x: self.threat_level_priority.get(x[0], 0), 
                                            reverse=True):
                summary.append(f"  - {threat_level}: {count}")
        
        return "\n".join(summary)
    
    def _aggregate_events(self, events: List[EvidenceEvent]) -> List[EvidenceEvent]:
        """Aggregate similar events to reduce repetition."""
        if not events:
            return []
        
        aggregated = []
        current_group = []
        
        for event in events:
            if (current_group and 
                current_group[0].event_type == event.event_type and
                current_group[0].timestamp.split()[1][:8] == event.timestamp.split()[1][:8]):  # Same HH:MM:SS
                current_group.append(event)
            else:
                if current_group:
                    aggregated.append(self._merge_event_group(current_group))
                current_group = [event]
        
        if current_group:
            aggregated.append(self._merge_event_group(current_group))
        
        return aggregated
    
    def _merge_event_group(self, events: List[EvidenceEvent]) -> EvidenceEvent:
        """Merge a group of similar events into one representative event."""
        if len(events) == 1:
            return events[0]
        
        # Use the first event as base, but modify description to show aggregation
        base_event = events[0]
        if len(events) > 1:
            base_event.description += f" (+{len(events)-1} similar)"
        
        return base_event
    
    def _make_description_concise(self, event: EvidenceEvent) -> str:
        """Make event descriptions more concise."""
        desc = event.description
        event_type = event.event_type
        
        if event_type == "Port Scan":
            # Extract key info: port, targets, packets
            if "Targets:" in desc and "Packets:" in desc:
                port = desc.split("port ")[1].split()[0] if "port " in desc else "unknown"
                targets = desc.split("Targets: ")[1].split()[0] if "Targets: " in desc else "?"
                packets = desc.split("Packets: ")[1].split(")")[0] if "Packets: " in desc else "?"
                return f"Scan: {port} ({targets}t, {packets}p)"
        
        elif event_type == "C&C Channel":
            # Extract IP and score
            if "Connection to" in desc and "Score:" in desc:
                ip = desc.split("Connection to ")[1].split(":")[0] if "Connection to " in desc else "unknown"
                score = desc.split("Score: ")[1].split(")")[0] if "Score: " in desc else "?"
                return f"C&C: {ip} (s:{score})"
        
        elif event_type == "Blacklisted IP":
            # Extract IP and AS
            if "blacklisted " in desc:
                ip = desc.split("blacklisted ")[1].split()[0] if "blacklisted " in desc else "unknown"
                as_info = desc.split("(AS: ")[1].split(")")[0] if "(AS: " in desc else ""
                as_short = as_info.split()[0] if as_info else "unknown"
                return f"Blacklist: {ip} ({as_short})"
        
        elif event_type == "DNS Issue":
            # Extract IP
            if "resolution to " in desc:
                ip = desc.split("resolution to ")[1].split()[0] if "resolution to " in desc else "unknown"
                return f"No-DNS: {ip}"
        
        elif event_type == "Private IP Connection":
            # Extract IP and port
            if "private IP " in desc and ":" in desc:
                parts = desc.split("private IP ")[1].split(":")
                ip = parts[0] if parts else "unknown"
                port = parts[1] if len(parts) > 1 else "?"
                return f"Private: {ip}:{port}"
        
        elif event_type == "Suspicious Connection":
            # Extract connection type and destination
            if "Non-HTTP" in desc or "Non-SSL" in desc:
                conn_type = "Non-HTTP" if "Non-HTTP" in desc else "Non-SSL"
                ip = desc.split("to ")[1].split(":")[0] if " to " in desc else "unknown"
                port = desc.split(":")[-1] if ":" in desc else "?"
                return f"{conn_type}: {ip}:{port}"
        
        # Fallback: truncate long descriptions
        return desc[:50] + "..." if len(desc) > 50 else desc
    
    def _summarize_by_type(self, events: List[EvidenceEvent]) -> Dict[str, Any]:
        """Summarize events by type for minimal format."""
        summary = {}
        
        for event in events:
            event_type = event.event_type
            if event_type not in summary:
                summary[event_type] = {
                    'count': 0,
                    'max_threat': 'info',
                    'details': [],
                    'summary': ''
                }
            
            summary[event_type]['count'] += 1
            
            # Track highest threat level
            if (self.threat_level_priority.get(event.threat_level, 0) > 
                self.threat_level_priority.get(summary[event_type]['max_threat'], 0)):
                summary[event_type]['max_threat'] = event.threat_level
            
            # Collect key details
            if event_type == "Port Scan":
                if "port " in event.description:
                    port = event.description.split("port ")[1].split()[0]
                    targets = event.description.split("Targets: ")[1].split()[0] if "Targets: " in event.description else "?"
                    summary[event_type]['details'].append(f"{port}→{targets}")
            
            elif event_type == "Blacklisted IP":
                if "blacklisted " in event.description:
                    ip = event.description.split("blacklisted ")[1].split()[0]
                    summary[event_type]['details'].append(ip)
        
        # Generate summary text
        for event_type, info in summary.items():
            count = info['count']
            if event_type == "Port Scan":
                ports = list(set(info['details']))[:3]  # Top 3 unique ports
                max_targets = max([int(d.split('→')[1]) for d in info['details'] if '→' in d and d.split('→')[1].isdigit()], default=0)
                info['summary'] = f"Port scans: {', '.join(ports)} (max: {max_targets} hosts)"
            
            elif event_type == "Blacklisted IP":
                unique_ips = len(set(info['details']))
                info['summary'] = f"Blacklisted IPs: {unique_ips} unique destinations"
            
            elif event_type == "C&C Channel":
                info['summary'] = f"C&C channels: {count} connections"
            
            elif event_type == "DNS Issue":
                info['summary'] = f"DNS evasion: {count} connections"
            
            else:
                info['summary'] = f"{event_type}: {count} events"
        
        return summary
    
    def _calculate_duration_hours(self, events: List[EvidenceEvent]) -> float:
        """Calculate duration in hours between first and last event."""
        if len(events) < 2:
            return 0.0
        
        try:
            from datetime import datetime
            start_time = datetime.strptime(events[0].timestamp, "%Y/%m/%d %H:%M:%S.%f")
            end_time = datetime.strptime(events[-1].timestamp, "%Y/%m/%d %H:%M:%S.%f")
            duration = end_time - start_time
            return duration.total_seconds() / 3600
        except:
            # Fallback calculation
            return 8.0  # Default estimate
    
    def _identify_attack_phases(self, events: List[EvidenceEvent]) -> List[Dict[str, Any]]:
        """Identify distinct phases of the attack."""
        phases = []
        
        # Group events by time windows (1 hour each)
        time_groups = {}
        for event in events:
            hour = event.timestamp.split()[1][:2]  # Get hour
            if hour not in time_groups:
                time_groups[hour] = []
            time_groups[hour].append(event)
        
        # Analyze each time group
        for hour, hour_events in sorted(time_groups.items()):
            event_types = [e.event_type for e in hour_events]
            
            # Determine phase based on dominant activity
            if any("Port Scan" in t for t in event_types):
                phase_name = "Reconnaissance"
                activities = self._summarize_scan_activity(hour_events)
            elif any("C&C" in t for t in event_types):
                phase_name = "Command & Control"
                activities = self._summarize_cc_activity(hour_events)
            elif any("Blacklisted" in t for t in event_types):
                phase_name = "Data Exfiltration"
                activities = self._summarize_blacklist_activity(hour_events)
            else:
                phase_name = "Lateral Movement"
                activities = [f"{len(hour_events)} security events"]
            
            phases.append({
                'name': phase_name,
                'time_range': f"{hour}:00-{hour}:59",
                'activities': activities
            })
        
        return phases
    
    def _summarize_scan_activity(self, events: List[EvidenceEvent]) -> List[str]:
        """Summarize port scanning activities."""
        scans = [e for e in events if e.event_type == "Port Scan"]
        if not scans:
            return ["Port scanning activity"]
        
        ports = set()
        max_targets = 0
        for scan in scans:
            if "port " in scan.description:
                port = scan.description.split("port ")[1].split()[0].replace("/TCP", "")
                ports.add(port)
            if "Targets: " in scan.description:
                targets = scan.description.split("Targets: ")[1].split()[0]
                if targets.isdigit():
                    max_targets = max(max_targets, int(targets))
        
        activities = [f"Port scanning: {', '.join(sorted(ports))} → {max_targets}+ targets"]
        
        # Add other activities in this phase
        other_events = [e for e in events if e.event_type != "Port Scan"]
        if other_events:
            activities.append(f"Network discovery: {len(other_events)} additional probes")
        
        return activities
    
    def _summarize_cc_activity(self, events: List[EvidenceEvent]) -> List[str]:
        """Summarize C&C activities."""
        cc_events = [e for e in events if e.event_type == "C&C Channel"]
        activities = []
        
        if cc_events:
            ips = set()
            for event in cc_events:
                if "Connection to " in event.description:
                    ip = event.description.split("Connection to ")[1].split(":")[0]
                    ips.add(ip)
            activities.append(f"C&C servers: {len(ips)} contacted")
        
        # Add persistence indicators
        other_events = [e for e in events if e.event_type != "C&C Channel"]
        if other_events:
            activities.append(f"Persistence: {len(other_events)} related events")
        
        return activities
    
    def _summarize_blacklist_activity(self, events: List[EvidenceEvent]) -> List[str]:
        """Summarize blacklisted IP activities."""
        blacklist_events = [e for e in events if e.event_type == "Blacklisted IP"]
        activities = []
        
        if blacklist_events:
            countries = set()
            for event in blacklist_events:
                # Extract country from AS info if available
                if "(AS: " in event.description:
                    as_info = event.description.split("(AS: ")[1]
                    if ", " in as_info:
                        country = as_info.split(", ")[-1].split()[0][:2]
                        countries.add(country)
            
            activities.append(f"{len(blacklist_events)} blacklisted IP connections")
            if countries:
                activities.append(f"Geographic spread: {len(countries)} countries")
        
        # Add evasion techniques
        dns_events = [e for e in events if e.event_type == "DNS Issue"]
        if dns_events:
            activities.append(f"DNS evasion: {len(dns_events)} connections without resolution")
        
        return activities
    
    def _calculate_comprehensive_risk_level(self, events: List[EvidenceEvent]) -> tuple:
        """Calculate comprehensive risk level based on multiple factors."""
        if not events:
            return "LOW", "No security events detected"
        
        # Count events by threat level
        threat_counts = {}
        confidence_scores = []
        event_types = set()
        
        for event in events:
            threat_counts[event.threat_level] = threat_counts.get(event.threat_level, 0) + 1
            confidence_scores.append(event.confidence)
            event_types.add(event.event_type)
        
        # Calculate metrics
        total_events = len(events)
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        unique_attack_types = len(event_types)
        
        # High-severity event types
        critical_event_types = {'C&C Channel', 'Blacklisted IP', 'Malicious Detection'}
        high_severity_events = sum(1 for e in events if e.event_type in critical_event_types)
        
        # Risk assessment logic
        critical_threats = threat_counts.get('critical', 0)
        high_threats = threat_counts.get('high', 0)
        medium_threats = threat_counts.get('medium', 0)
        
        # Determine risk level and rationale
        if critical_threats > 0:
            risk_level = "CRITICAL"
            reasons = [f"{critical_threats} critical-level threats detected"]
            if high_threats > 0:
                reasons.append(f"{high_threats} additional high-level threats")
        elif high_threats >= 3:
            risk_level = "CRITICAL" 
            reasons = [f"Multiple high-severity threats ({high_threats} events)"]
        elif high_threats > 0 and high_severity_events >= 2:
            risk_level = "CRITICAL"
            reasons = [f"{high_threats} high-level threats with {high_severity_events} critical event types"]
        elif high_threats > 0:
            risk_level = "HIGH"
            reasons = [f"{high_threats} high-level security threats"]
        elif medium_threats >= 5 or (medium_threats >= 3 and unique_attack_types >= 3):
            risk_level = "HIGH"
            reasons = [f"{medium_threats} medium-level threats across {unique_attack_types} attack types"]
        elif medium_threats > 0 or high_severity_events > 0:
            risk_level = "MEDIUM"
            reasons = [f"{medium_threats} medium-level threats" if medium_threats > 0 else f"{high_severity_events} suspicious connections"]
        else:
            risk_level = "LOW"
            reasons = ["Low-severity events only"]
        
        # Add contextual factors
        if avg_confidence >= 0.8:
            reasons.append(f"high confidence (avg: {avg_confidence:.2f})")
        elif avg_confidence <= 0.3:
            reasons.append(f"low confidence (avg: {avg_confidence:.2f})")
            
        if total_events >= 10:
            reasons.append(f"high event volume ({total_events} events)")
            
        if unique_attack_types >= 4:
            reasons.append(f"diverse attack patterns ({unique_attack_types} types)")
        
        rationale = "; ".join(reasons)
        return risk_level, rationale


def apply_filtering(events: List[EvidenceEvent], args) -> List[EvidenceEvent]:
    """Apply filtering options to events."""
    filtered_events = events
    
    # Apply threat level filtering
    if args.min_threat:
        threat_levels = ['info', 'low', 'medium', 'high', 'critical']
        min_level_idx = threat_levels.index(args.min_threat)
        filtered_events = [e for e in filtered_events if threat_levels.index(e.threat_level) >= min_level_idx]
    
    # Apply max events limiting
    if args.max_events and len(filtered_events) > args.max_events:
        # Sort by threat level priority and keep top N
        dag_gen_temp = DAGGenerator()
        filtered_events.sort(key=lambda x: dag_gen_temp.threat_level_priority.get(x.threat_level, 0), reverse=True)
        filtered_events = filtered_events[:args.max_events]
    
    return filtered_events


def generate_output_for_ip(events: List[EvidenceEvent], target_ip: str, args) -> str:
    """Generate output for a single IP address."""
    if not events:
        return f"No evidence found for IP: {target_ip}"
    
    if args.json:
        # This shouldn't be called for JSON output in --all-ips mode
        events_dict = []
        for event in events:
            events_dict.append({
                'timestamp': event.timestamp,
                'ip_address': event.ip_address,
                'event_type': event.event_type,
                'description': event.description,
                'threat_level': event.threat_level,
                'confidence': event.confidence,
                'raw_details': event.raw_details
            })
        return json.dumps(events_dict, indent=2)
    else:
        # Determine format
        compact = args.compact
        minimal = args.minimal
        pattern = args.pattern
        group_time = args.group_time
        
        # Generate DAG
        dag_generator = DAGGenerator(
            compact=compact, 
            minimal=minimal, 
            pattern=pattern, 
            group_time=group_time,
            include_threat_level=args.include_threat_level
        )
        dag = dag_generator.generate_dag(events, target_ip)
        
        output_lines = [dag]
        
        if args.summary and not minimal:  # Don't show summary with minimal format
            output_lines.append("="*50)
            output_lines.append(dag_generator.generate_summary(events))
        
        return "\n".join(output_lines)


def main():
    parser = argparse.ArgumentParser(description='Generate textual DAG from Slips evidence logs')
    parser.add_argument('log_file', help='Path to the Slips evidence log file')
    parser.add_argument('target_ip', nargs='?', help='Target IP address to analyze (optional with --all-ips)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--summary', '-s', action='store_true', help='Include summary statistics')
    parser.add_argument('--json', '-j', action='store_true', help='Output raw events as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--all-ips', '-a', action='store_true', help='Process all IP addresses found in log file')
    
    # Compact output format options
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument('--compact', '-c', action='store_true', help='Compact single-line format (default)')
    format_group.add_argument('--minimal', '-m', action='store_true', help='Minimal bullet-point summary')
    format_group.add_argument('--pattern', '-p', action='store_true', help='Attack pattern analysis format')
    format_group.add_argument('--full', '-f', action='store_true', help='Full verbose format (original)')
    
    # Filtering options
    parser.add_argument('--min-threat', choices=['info', 'low', 'medium', 'high', 'critical'], 
                       help='Filter events by minimum threat level')
    parser.add_argument('--max-events', type=int, help='Limit to N most significant events')
    parser.add_argument('--group-time', type=int, metavar='MINUTES', 
                       help='Group events within N-minute windows')
    parser.add_argument('--include-threat-level', action='store_true',
                       help='Include threat level information in output (default: excluded)')
    parser.add_argument('--per-analysis', action='store_true',
                       help='Generate separate DAG for each alert/analysis instead of per IP')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.all_ips and not args.target_ip and not args.per_analysis:
        parser.error("target_ip is required unless --all-ips or --per-analysis is specified")
    
    # Set default format to compact if no format specified
    if not any([args.compact, args.minimal, args.pattern, args.full]):
        args.compact = True
    
    # Parse the log
    if args.verbose:
        print(f"Parsing log file: {args.log_file}")
        if args.all_ips:
            print("Processing all IP addresses in log file")
        else:
            print(f"Target IP: {args.target_ip}")
    
    parser_obj = SlipsLogParser()
    
    # Handle per-analysis mode
    if args.per_analysis:
        if args.verbose:
            print("Per-analysis mode: generating separate DAGs for each alert")
        
        # Parse alerts instead of events
        if args.all_ips:
            alerts = parser_obj.parse_alerts(args.log_file)
        else:
            alerts = parser_obj.parse_alerts(args.log_file, args.target_ip)
        
        if not alerts:
            print("No alerts found in log file")
            return
        
        if args.verbose:
            print(f"Found {len(alerts)} alerts")
        
        # Generate DAG for each alert
        dag_generator = DAGGenerator(
            compact=args.compact,
            minimal=args.minimal,
            pattern=args.pattern,
            group_time=args.group_time,
            include_threat_level=args.include_threat_level
        )
        
        output_lines = []
        for i, alert in enumerate(alerts):
            if i > 0:  # Add separator between alerts
                output_lines.append("=" * 60)
            
            dag_output = dag_generator.generate_dag_for_alert(alert)
            output_lines.append(dag_output)
            
            # Add summary if requested
            if args.summary and not args.minimal:
                output_lines.append("-" * 40)
                output_lines.append(dag_generator.generate_summary(alert.evidence_events))
        
        # Write output
        output_text = "\n".join(output_lines)
        
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                if args.verbose:
                    print(f"Output written to: {args.output}")
            except Exception as e:
                print(f"Error writing output file: {e}")
                sys.exit(1)
        else:
            print(output_text)
        
        return
    
    # Original IP-based mode
    if args.all_ips:
        # Discover all IPs in the log file
        all_ips = parser_obj.discover_all_ips(args.log_file)
        if args.verbose:
            print(f"Found {len(all_ips)} IP addresses with evidence: {', '.join(all_ips)}")
        
        # Process each IP
        all_outputs = []
        for ip in all_ips:
            if args.verbose:
                print(f"Processing IP: {ip}")
            
            events = parser_obj.parse_log(args.log_file, ip)
            if not events:
                continue
                
            # Apply filtering for this IP
            filtered_events = apply_filtering(events, args)
            
            if not filtered_events:
                continue
            
            # Generate output for this IP
            ip_output = generate_output_for_ip(filtered_events, ip, args)
            all_outputs.append(ip_output)
        
        # Combine all outputs
        if args.json:
            # For JSON, combine all events with IP identification
            combined_json = {}
            for ip in all_ips:
                events = parser_obj.parse_log(args.log_file, ip)
                filtered_events = apply_filtering(events, args)
                if filtered_events:
                    combined_json[ip] = [
                        {
                            'timestamp': event.timestamp,
                            'ip_address': event.ip_address,
                            'event_type': event.event_type,
                            'description': event.description,
                            'threat_level': event.threat_level,
                            'confidence': event.confidence,
                            'raw_details': event.raw_details
                        } for event in filtered_events
                    ]
            output_lines = [json.dumps(combined_json, indent=2)]
        else:
            # For regular output, separate each IP with dividers
            separator = "=" * 60
            output_lines = []
            for i, ip_output in enumerate(all_outputs):
                if i > 0:  # Add separator between IPs
                    output_lines.append(separator)
                output_lines.append(ip_output)
    else:
        # Process single IP (original behavior)
        events = parser_obj.parse_log(args.log_file, args.target_ip)
        filtered_events = apply_filtering(events, args)
        output_lines = [generate_output_for_ip(filtered_events, args.target_ip, args)]
    
    # Write output
    output_text = "\n".join(output_lines)
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            if args.verbose:
                print(f"Output written to: {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}")
            sys.exit(1)
    else:
        print(output_text)


if __name__ == '__main__':
    main()
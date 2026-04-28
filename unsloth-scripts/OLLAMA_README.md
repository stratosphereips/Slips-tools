# Qwen2.5-1.5B Slips IDS — Immune Summarization

A fine-tuned version of [Qwen2.5-1.5B-Instruct](https://ollama.com/library/qwen2.5:1.5b) specialized in generating concise, actionable security summaries from [Slips IDS](https://github.com/stratosphereips/StratosphereLinuxIPS) alert logs.

Trained at the [Stratosphere Research Laboratory](https://www.stratosphereips.org/), Czech Technical University in Prague.

## Overview

Slips is a machine-learning-based network intrusion detection system (IDS). It generates evidence logs that describe suspicious network behaviors per IP address. This model takes a compacted DAG of those alerts and produces a plain-language summary that a security analyst can act on immediately.

Optimized for edge deployment (Raspberry Pi 5 and similar devices) — fast inference at 1.5B parameters without sacrificing summary quality.

**Fine-tuning method:** SFT using [Unsloth](https://github.com/unslothai/unsloth) + LoRA on ~480 labeled Slips incidents.
**Training data:** Best-of-N responses selected from GPT-4o, GPT-4o-mini, and Qwen2.5 baseline outputs, scored by an LLM judge.

## Usage

```bash
ollama run stratosphere/qwen2.5-1.5b-slips-immune-summarization
```

### Example prompt

The model receives a compacted DAG entry from Slips, pre-processed for edge deployment:

```
============================================================
Incident: 795e8daa-a0d6-48ce-87b5-e0696cbe84bb
Source IP: 192.168.1.113 | Timewindow: 269
Timeline: 1970-01-12 04:00:17 to 1970-01-12 05:00:17
Threat Level: 15.35 | Events: 103

• 04:00-04:02 - 2 events to Horizontal [HIGH]
  - Horizontal port scan to port  443/TCP. From 192.168.1.113 to 5 unique destination IPs. Total packets sent: 34. Confidence: 1. by Slips threat level: high.
  - Horizontal port scan to port  449/TCP. From 192.168.1.113 to 5 unique destination IPs. Total packets sent: 39. Confidence: 1. by Slips threat level: high.
• 04:18 - Event to 82.146.48.241 [MEDIUM]
  - Multiple reconnection attempts to Destination IP: 82.146.48.241 from IP: 192.168.1.113 reconnections: 5 threat level: medium.
• 04:25 - Event to 82.202.226.189 [MEDIUM]
  - Multiple reconnection attempts to Destination IP: 82.202.226.189 from IP: 192.168.1.113 reconnections: 5 threat level: medium.
• 04:12-04:13 - 3 events to 200.111.97.235:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 200.111.97.235. threat level: medium. (x3)
• 04:45 - Event to 73.252.252.62:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 73.252.252.62. threat level: medium.
• 04:40 - 9 events to 209.205.188.238:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 209.205.188.238. threat level: medium. (x9)
• 04:21-04:22 - 3 events to 177.250.126.51:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 177.250.126.51. threat level: medium. (x3)
• 04:29-04:30 - 3 events to 177.251.27.6:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 177.251.27.6. threat level: medium. (x3)
• 04:26-04:27 - 3 events to 76.16.105.16:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 76.16.105.16. threat level: medium. (x3)
• 04:14 - Event to 92.53.66.60 [MEDIUM]
  - Multiple reconnection attempts to Destination IP: 92.53.66.60 from IP: 192.168.1.113 reconnections: 5 threat level: medium.
• 04:40 - Event to 209.205.188.238 [MEDIUM]
  - Multiple reconnection attempts to Destination IP: 209.205.188.238 from IP: 192.168.1.113 reconnections: 5 threat level: medium.
• 04:00-04:02 - 3 events to 67.209.219.92:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 67.209.219.92. threat level: medium. (x3)
• 04:11 - Event to 80.87.198.204 [MEDIUM]
  - Multiple reconnection attempts to Destination IP: 80.87.198.204 from IP: 192.168.1.113 reconnections: 5 threat level: medium.
• 04:00-04:29 - 71 events to A [INFO]
  - A connection without DNS resolution to IP: 82.202.226.189 threat level: info. (x9)
  - A connection without DNS resolution to IP: 194.87.239.201 threat level: info. (x3)
  - A connection without DNS resolution to IP: 194.87.93.30 threat level: info. (x3)
  - ... and 14 more variations

Total Evidence: 103 events
Severity breakdown: High: 2, Medium: 30, Info: 71
```

### Example output

```
============================================================
Incident: 795e8daa-a0d6-48ce-87b5-e0696cbe84bb
Source IP: 192.168.1.113 | Timewindow: 269
Timeline: 1970-01-12 04:00:17 to 1970-01-12 05:00:17
Threat Level: 15.35 | Events: 103

• 04:00-04:29 - Multiple connections made to the IP address 67.209.219.92 without DNS resolution [INFO]
• 04:00-04:45 - Connection to unknown port 449/TCP at IP 67.209.219.92 [MEDIUM]
• 04:11-04:40 - Five reconnection attempts to the IP address 80.87.198.204 from source IP 192.168.1.113 [MEDIUM]
• 04:00-04:02 - Horizontal port scan conducted on port 449/TCP targeting five unique IP addresses [HIGH]

Total Evidence: 103 events
Severity breakdown: High: 1, Medium: 2, Info: 1
```

## Quantization

This model is available in the following quantization levels:

| Quantization | Size | Use case |
|---|---|---|
| Q4_K_M (default) | ~1.0 GB | Recommended — best quality/size tradeoff |
| Q5_K_M | ~1.1 GB | Higher quality, slightly larger |

```bash
# Default (Q4_K_M)
ollama pull stratosphere/qwen2.5-1.5b-slips-immune-summarization

# Higher quality
ollama pull stratosphere/qwen2.5-1.5b-slips-immune-summarization:q5_k_m
```

## System Prompt

The model was trained with the following system prompt and works best when it is included:

```
You are a security analyst. Your task is to translate technical security events into clear, concise, human-readable summaries and assess their severity.

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
Incident: <incident_id>
Source IP: <source_ip> | Timewindow: <timewindow>
Timeline: <start> to <end>
Threat Level: <threat_level> | Events: <count>

• HH:MM-HH:MM - [Your clear grouped summary] [YOUR_ASSESSED_SEVERITY]
• HH:MM - [Your clear summary] [YOUR_ASSESSED_SEVERITY]

Total Evidence: <count> events
Severity breakdown: [Your calculated breakdown, e.g., "High: 5, Medium: 3, Info: 2"]

RULES:
- Group identical events into ONE line
- Use time ranges (HH:MM-HH:MM) when showing grouped events
- Assess severity based on security impact, not just event type
- Keep descriptions clear and concise
- Just output the structured summary - no explanations or meta-commentary
```

## Integration with Slips

This model is designed to work directly with the Slips IDS pipeline. See the [Slips integration guide](https://github.com/stratosphereips/Slips-tools/blob/main/unsloth-scripts/IMPLEMENTATION_INSIDE_SLIPS.md) for details on how to connect it to a live Slips instance.

## License

This fine-tuned model is released under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), consistent with the base Qwen2.5 model license.

## Links

- [Slips IDS](https://github.com/stratosphereips/StratosphereLinuxIPS)
- [Stratosphere Research Laboratory](https://www.stratosphereips.org/)
- [Training code (Slips-tools)](https://github.com/stratosphereips/Slips-tools/tree/main/unsloth-scripts)
- [Base model: Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)

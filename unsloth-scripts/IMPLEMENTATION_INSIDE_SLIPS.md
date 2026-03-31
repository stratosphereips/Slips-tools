# Implementing Qwen2.5-1.5B-Slips-Immune inside Slips IDS

This document describes how to integrate the finetuned model into Slips as a drop-in
replacement for the existing LLM summarization call. It covers what operations need to
be implemented, their purpose, inputs, outputs, and known limitations.

---

## Overview

The model takes a structured summary of network events for a single IP in a time window
and returns a human-readable security incident report with per-event severity labels.

Three operations are required before and during the model call:

```
Slips alert log (.jsonl)
        │
        ▼
┌───────────────────────┐
│  1. DAG Parser        │  Parse raw IDEA events → structured text
└──────────┬────────────┘
           │  dag_text  (potentially very large)
           ▼
┌───────────────────────┐
│  2. DAG Truncator     │  Cap token length at clean line boundary
└──────────┬────────────┘
           │  dag_text  (guaranteed within context window)
           ▼
┌───────────────────────┐
│  3. Model Call        │  system prompt + dag_text → incident report
└──────────┬────────────┘
           │
           ▼
    Incident Report
```

---

## Operation 1 — DAG Parser

**Purpose:**
Slips logs are raw IDEA-format JSON objects — one per line, one per event. They are not
human-readable and cannot be fed directly to the model. The DAG parser groups all events
belonging to the same incident (same source IP, same timewindow) and formats them into a
single structured text block.

**Input:** `.jsonl` file from Slips, or a stream of IDEA JSON objects

**Output:** One text block per incident:

```
Incident: abc-123
Source IP: 192.168.1.5 | Timewindow: 12
Timeline: 14:00:00 to 15:00:00
Threat Level: 8.5 | Events: 42

14:05 | Detected a horizontal port scan to port 443/TCP. 50 unique dst IPs
14:05 | Detected a horizontal port scan to port 443/TCP. 50 unique dst IPs
14:07 | Connection to known C2 server 185.29.135.234:443
...
```

**Key design decision — event grouping:**
Identical or near-identical events must be collapsed into one line with a count. Without
grouping, a single incident with 500 port scan events produces a 10k+ token block. With
grouping:

```
14:05-14:45 | Horizontal port scan to port 443/TCP, 50 unique dst IPs (487x)
```

This alone brings most incidents within the model's context window. Grouping should
always be applied before truncation.

**Token distribution across the dataset (532 real Slips incidents):**

| Statistic | Tokens |
|-----------|--------|
| Median    | 436    |
| p90       | 3,108  |
| p95       | 3,690  |
| Max       | 36,590 |

About 20% of incidents exceed 2,048 tokens even after grouping, which is why Operation 2
is necessary.

---

## Operation 2 — DAG Truncator

**Purpose:**
Even after grouping, complex incidents (≥2000 events) can still exceed the model's
context window. Silent truncation by the tokenizer mid-sentence produces incoherent
output. Explicit truncation at a clean line boundary — with a marker — lets the model
know the input is partial and generate a coherent partial summary.

**Input:** DAG text from Operation 1, max token limit (recommended: 1800)

**Logic:**
1. Split the DAG on newlines
2. Accumulate lines until the next line would exceed the token limit
3. Append a truncation marker on the last line

**Output:** Same DAG text, cut at the last complete event line before the limit:

```
14:05-14:45 | Horizontal port scan to port 443/TCP (487x)
14:07 | Connection to known C2 server 185.29.135.234:443
[truncated: showing first ~1800 tokens of full DAG]
```

**When to apply:** Only when the DAG exceeds ~1800 tokens after grouping. This leaves
~200 tokens of headroom for the system prompt and the model's response within a 2048
context window. If retraining with `max_seq_length=8192`, raise this limit to ~7800.

**Important:** The truncation marker text must match exactly what was used during
training:
```
[truncated: showing first ~N tokens of full DAG]
```
The model was trained on examples with this marker and will handle it gracefully. Any
different wording is out-of-distribution.

---

## Operation 3 — Model Call

**Purpose:**
Send the structured DAG to the model and receive a formatted incident report.

**Input:** DAG text from Operations 1 and 2.

**Message format — critical:**
The model was trained with instructions in the system role and the DAG alone in the user
role. These must not be merged into a single message.

```python
messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT    # must match training exactly — see below
    },
    {
        "role": "user",
        "content": dag_text         # output of Operations 1+2, nothing else
    }
]
```

**System prompt (copy verbatim — any change degrades output):**

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
- Do not include token counts or performance statistics
```

**Recommended call parameters:**

```python
client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="none")
response = client.chat.completions.create(
    model="finetuned",
    messages=messages,
    max_tokens=512,
    temperature=0.0    # deterministic — this is a structured output task
)
```

**Output:**

```
============================================================
Incident: abc-123
Source IP: 192.168.1.5 | Timewindow: 12
Timeline: 14:00:00 to 15:00:00
Threat Level: 8.5 | Events: 42

• 14:05-14:45 - Port scanning 50 hosts on HTTPS port [HIGH]
• 14:07 - Direct connection to command & control server 185.29.135.234 [CRITICAL]

Total Evidence: 42 events
Severity breakdown: Critical: 1, High: 1, Medium: 0, Low: 0, Info: 0
```

---

## Serving the Model

The model exposes an OpenAI-compatible REST API via `serve_model.py`:

```bash
python3 serve_model.py /path/to/qwen_finetuned_merged_16bit \
  --device cuda \
  --quant 4bit        # remove --quant on A100 / high-VRAM GPUs
```

The server starts on `http://localhost:8000/v1`. Point Slips' existing LLM integration
at this URL with any model name — the server ignores the model name field.

---

## Evaluation Results

Evaluated on 47 held-out Slips incidents. Judge: `gpt-oss-120b` (independent).

| Model | Avg Score | Avg Position | Win Rate |
|-------|-----------|--------------|----------|
| **Qwen2.5-1.5B (finetuned)** | **7.21/10** | **1.48** | **68.1%** |
| GPT-4o-mini | 5.98/10 | 2.40 | 14.9% |
| GPT-4o | 5.11/10 | 2.46 | 12.8% |
| Qwen2.5 3B (no finetuning) | 4.30/10 | 3.25 | 2.1% |
| Qwen2.5 1B (no finetuning) | 2.83/10 | 3.67 | 2.1% |

### Performance by Complexity

| Complexity | Events | Finetuned | GPT-4o-mini | GPT-4o |
|------------|--------|-----------|-------------|--------|
| Simple     | < 500  | **7.97**  | 5.97        | 4.77   |
| Medium     | 500–1999 | **7.43** | 5.29       | 5.14   |
| Complex    | ≥ 2000 | 4.44      | **6.56**    | 6.22   |

The finetuned model outperforms GPT-4o and GPT-4o-mini on simple and medium incidents.
Performance on complex incidents is degraded due to DAG truncation at training time (see
Known Limitations below).

---

## Known Limitations

| Limitation | Impact | Fix |
|-----------|--------|-----|
| Trained at `max_seq_length=2048` | Score drops to 4.44 on complex incidents (≥2000 events) | Retrain with `max_seq_length=8192` and `--max-dag-tokens 7800` in `select_best_responses.py` |
| No truncation marker in training data | Model may not handle truncated inputs gracefully on current weights | Retrain with `--max-dag-tokens` set so truncated examples appear in training data |
| Only ~2 Normal traffic incidents in eval set | Normal traffic performance is uncertain | Collect more Normal incidents for evaluation |
| Single-GPU serving (no batching) | Throughput limited for high-volume Slips deployments | Use vLLM or TGI for production serving |

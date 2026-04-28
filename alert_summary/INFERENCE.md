# Inference Pipeline

## Overview

This pipeline takes raw network security alerts produced by [Slips](https://github.com/stratosphereips/StratosphereLinuxIPS) and uses a language model to turn them into structured, human-readable reports. It is designed for security researchers and analysts who want to evaluate how well different LLMs — including finetuned small models — perform on real network intrusion data.

### What problem does it solve?

Slips detects threats by correlating low-level network events (port scans, C&C connections, DNS anomalies, etc.) into higher-level *incidents*. Each incident can contain thousands of individual events. Reading those raw events directly is impractical: the signal is buried in repetitive, technical log lines.

This pipeline feeds those events to an LLM and asks it to do two things:

1. **Summarize** — translate the raw evidence into a concise, severity-tagged human report that a SOC analyst can act on quickly.
2. **Assess risk** — identify the most likely causes of the activity (malicious, legitimate, or misconfiguration) and produce a structured risk assessment with business impact and investigation priority.

### How it fits into the research workflow

There are two ways to get input data into `inference.py`:

**Path A — Research/benchmarking (sampled dataset)**
```
Slips alerts (alerts.json)
        │
        ▼
sample_dataset.sh         ← sample incidents across multiple captures into one JSONL
        │
        ▼
inference.py              ← run LLM analysis (summary, risk, or both)
        │
        ▼
output JSON               ← one record per incident with LLM-generated fields
```

**Path B — Direct analysis (single capture)**
```
Slips alerts.json  ──────► inference.py  ──────► output JSON
```

The raw `alerts.json` files produced by Slips are already in the same JSONL format that `inference.py` expects — one JSON object per line, with `Incident` and `Event` records. You can feed them directly without any sampling step:

```bash
python3 inference.py \
  sample_logs/alya_datasets/Malware/CTU-Malware-Capture-Botnet-346-1/2018-04-03_win12-fixed/9/alerts.json \
  --task risk \
  --model stratosphere/qwen2.5-1.5b-slips-immune-risk:q8_0 \
  --base-url http://localhost:11434/v1 \
  --group-events --verbose
```

Path B is the natural choice when you have a specific capture you want to analyze. Path A is used when you want a balanced, reproducible dataset drawn from many captures for evaluation or finetuning.

The output JSON is self-contained: each record has the incident metadata plus the LLM analysis. It can be read directly, or fed into the evaluation scripts (`evaluate_summaries.py`, `evaluate_risk.py`) to judge quality with a separate LLM.

### Intended use cases

- **Incident triage** — point the script directly at a Slips `alerts.json` from a live or historical capture and get a structured report immediately
- **Benchmarking finetuned models** — run the same sampled dataset through multiple models and compare their outputs
- **Dataset generation** — produce silver-standard analyses from a strong model (GPT-4o) to use as training targets

---

## Limitations

**No resume / checkpointing.** If inference fails mid-run (network error, model crash), the partial output is not saved. For large datasets, consider splitting the JSONL into smaller chunks first.

**No retry logic.** A single failed LLM call causes that incident's analysis to contain an error string rather than real output. Check for `"failed:"` strings in the output if results look incomplete.

**Token limits are your responsibility.** Large incidents can have thousands of events. If the prompt exceeds the model's context window, the API will return an error. Always use `--group-events` with small models (≤3B parameters). For very large incidents even grouped prompts can be long — there is no automatic truncation.

**Finetuned models may ignore prompt structure.** The prompts were designed for instruction-following models. A finetuned model trained on a specific output format may produce outputs that deviate from the expected structure, especially for the `both` task which it was not trained on.

**Timestamps are relative to capture start.** The IDEA format used by Slips anchors `StartTime` to `1970-01-01`, meaning all timestamps reflect time elapsed since the start of the network capture, not wall-clock time. This is expected behavior, not a bug.

**OpenAI API key required even for Ollama.** The `openai` Python library requires a non-empty `OPENAI_API_KEY` environment variable. For local Ollama models, set it to any non-empty string (e.g. `export OPENAI_API_KEY=ollama`).

---

## Files

| File | Role |
|------|------|
| `inference.py` | Unified inference script — runs summary and/or risk analysis |
| `alert_parser_common.py` | Shared parsing and prompt-building utilities |

---

## `alert_parser_common.py` — Shared Utilities

### Data Classes

**`JSONEvent`**
Represents a single security event from the JSONL file.

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Event UUID |
| `severity` | str | Critical / High / Medium / Low / Info |
| `start_time` | str | ISO timestamp |
| `confidence` | float | Detection confidence score |
| `description` | str | Human-readable event description |
| `source_ips` | List[str] | Source IP addresses |
| `source_ports` | List[int] | Source ports |
| `target_ips` | List[str] | Target IP addresses |
| `target_ports` | List[int] | Target ports |
| `note` | Dict | Parsed JSON from the Note field |

**`JSONIncident`**
Represents an incident (aggregation of correlated events).

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Incident UUID |
| `source_ips` | List[str] | Source IP addresses |
| `start_time` | str | ISO timestamp |
| `correl_ids` | List[str] | Event IDs linked to this incident |
| `note` | Dict | Contains `timewindow`, `accumulated_threat_level`, `EndTime` |

### Classes

**`AlertJSONParser`**
Reads a JSONL file and separates `Incident` and `Event` records.

```python
parser = AlertJSONParser()
parser.parse_file("datasets/my_dataset_01.jsonl")

# Access all incidents
for incident in parser.incidents:
    events = parser.get_incident_events(incident)
```

### Functions

**`format_time(timestamp, short=False)`**
Converts an ISO timestamp to a readable string.
- `short=False` → `"2024-04-05 16:53:07"`
- `short=True`  → `"16:53"`

**`normalize_pattern(description)`**
Replaces IPs, ports, and numbers with placeholders for grouping:
```
"Horizontal port scan to 443/TCP. 50 unique dst IPs"
→ "Horizontal port scan to <PORT>/TCP. <NUM> unique dst IPs"
```

**`group_events_by_pattern(events)`**
Groups a list of `JSONEvent` objects by their normalized description pattern.
Returns a list of dicts: `time_range`, `pattern`, `count`, `samples`, `original_desc`.

**`build_evidence_text(events, group=False)`**
Formats events into a plain-text evidence block for LLM prompts.
- `group=False` — one line per event: `HH:MM | description`
- `group=True`  — grouped with counts: `HH:MM | description (12x similar, samples: 1.2.3.4)`

---

## `inference.py` — Unified Inference Script

### Usage

```
python3 inference.py <input.jsonl> --task {summary|risk|both} [options]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `json_file` | required | Input JSONL file in IDEA format |
| `--task` | `summary` | Analysis task: `summary`, `risk`, or `both` |
| `--model` | `gpt-4o-mini` | LLM model name |
| `--base-url` | `https://api.openai.com/v1` | OpenAI-compatible API endpoint |
| `--output` / `-o` | auto | Output JSON file path |
| `--group-events` | off | Group similar events before sending to LLM (reduces tokens) |
| `--behavior-analysis` | off | Add behavior flow analysis (summary/both tasks only) |
| `--verbose` / `-v` | off | Print progress and token counts to stderr |

### Auto-named Output Files

| Task | Output filename |
|------|----------------|
| `summary` | `{input_base}.llm.{model}.json` |
| `risk` | `{input_base}.cause_risk.{model}.json` |
| `both` | `{input_base}.inference.{model}.json` |

### Output Schema

**`--task summary`**
```json
[
  {
    "incident_id": "54f07359-...",
    "source_ip": "192.168.1.113",
    "timewindow": "1",
    "timeline": "1970-01-01 00:00:16 to 1970-01-01 01:00:16",
    "threat_level": 15.08,
    "event_count": 4736,
    "summary": "...",
    "behavior_analysis": "..."
  }
]
```

**`--task risk`**
```json
[
  {
    "incident_id": "54f07359-...",
    "source_ip": "192.168.1.113",
    "timewindow": "1",
    "timeline": "1970-01-01 00:00:16 to 1970-01-01 01:00:16",
    "threat_level": 15.08,
    "event_count": 4736,
    "cause_analysis": "...",
    "risk_assessment": "..."
  }
]
```

**`--task both`** includes all six analysis fields.

---

## Examples

### OpenAI

```bash
# Summary
python3 inference.py datasets/my_dataset_01.jsonl \
  --task summary --model gpt-4o-mini --group-events --behavior-analysis

# Risk
python3 inference.py datasets/my_dataset_01.jsonl \
  --task risk --model gpt-4o-mini --group-events
```

### Finetuned models via Ollama

```bash
# Summary — finetuned summarization model
python3 inference.py datasets/my_dataset_01.jsonl \
  --task summary \
  --model stratosphere/qwen2.5-1.5b-slips-immune-summarization:q8_0 \
  --base-url http://localhost:11434/v1 \
  --group-events --verbose

# Risk — finetuned risk model
python3 inference.py datasets/my_dataset_01.jsonl \
  --task risk \
  --model stratosphere/qwen2.5-1.5b-slips-immune-risk:q8_0 \
  --base-url http://localhost:11434/v1 \
  --group-events --verbose
```

### Custom output path

```bash
python3 inference.py datasets/my_dataset_01.jsonl \
  --task risk \
  --model stratosphere/qwen2.5-1.5b-slips-immune-risk:q8_0 \
  --base-url http://localhost:11434/v1 \
  --output results/risk_finetuned.json
```

---

## Notes

- `--group-events` is strongly recommended for small models (1.5B) to stay within context limits.
- `--behavior-analysis` adds a second LLM call per incident; only applies to `summary` and `both` tasks.
- The API key is read from the `OPENAI_API_KEY` environment variable (or `.env` file). For Ollama, any non-empty value works.

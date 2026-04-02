# Qwen2.5-1.5B Slips IDS — Immune Summarization

A fine-tuned version of [Qwen2.5-1.5B-Instruct](https://ollama.com/library/qwen2.5:1.5b) specialized in generating concise, actionable security summaries from [Slips IDS](https://github.com/stratosphereips/StratosphereLinuxIPS) alert logs.

Trained at the [Stratosphere Research Laboratory](https://www.stratosphereips.org/), Czech Technical University in Prague.

## Overview

Slips is a machine-learning-based network intrusion detection system (IDS). It generates evidence logs that describe suspicious network behaviors per IP address. This model takes a compacted DAG of those alerts and produces a plain-language summary that a security analyst can act on immediately.

Optimized for edge deployment (Raspberry Pi 5 and similar devices) — fast inference at 1.5B parameters without sacrificing summary quality.

**Fine-tuning method:** SFT + DPO using [Unsloth](https://github.com/unslothai/unsloth) + LoRA on ~480 labeled Slips incidents.
**Training data:** Best-of-N responses selected from GPT-4o, GPT-4o-mini, and Qwen2.5 baseline outputs, scored by an LLM judge.

## Usage

```bash
ollama run stratosphere/qwen2.5-1.5b-slips-immune-summarization
```

### Example prompt

The model receives a compacted DAG entry from Slips, pre-processed for edge deployment:

```
============================================================
Incident: b89dce4b-059f-49c5-a554-a3fbf785612c
Source IP: 192.168.1.113 | Timewindow: 16
Timeline: 1970-01-02 15:00:49 to 1970-01-02 16:00:49
Threat Level: 15.0 | Events: 33

• 15:29-15:30 - 7 events to 177.251.27.6:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 177.251.27.6. (x7)
• 15:38-15:39 - 9 events to 209.205.188.238:449 [MEDIUM]
  - Connection to unknown destination port 449/TCP destination IP 209.205.188.238. (x9)
• 15:48 - Event to 92.53.91.20 [MEDIUM]
  - Multiple reconnection attempts to 92.53.91.20 from 192.168.1.113 reconnections: 5
• 15:09 - Event to A [INFO]
  - A connection without DNS resolution to IP: 194.87.93.30

Total Evidence: 33 events
Severity breakdown: Medium: 32, Info: 1
```

### Example output

```
============================================================
Incident: b89dce4b-059f-49c5-a554-a3fbf785612c
Source IP: 192.168.1.113 | Timewindow: 16
Timeline: 1970-01-02 15:00:49 to 1970-01-02 16:00:49
Threat Level: 15.0 | Events: 33

• 15:29-15:50 - Multiple connections to unknown remote servers on TCP port 449 [MEDIUM]
• 15:29-15:48 - Multiple reconnection attempts to several external IPs from 192.168.1.113 [MEDIUM]
• 15:09 - Direct connection to IP 194.87.93.30 without DNS resolution [INFO]

Total Evidence: 33 events
Severity breakdown: Medium: 2, Info: 1
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
You are a network security analyst assistant. Analyze Slips IDS alert summaries
and provide concise, actionable security assessments. Focus on the most critical
threats, explain the attack pattern, and recommend immediate response actions.
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

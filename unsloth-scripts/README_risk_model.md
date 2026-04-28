---
base_model: unsloth/Qwen2.5-1.5B-Instruct
datasets:
- stratosphere/immune-risk-sft-dataset
- stratosphere/immune-summary-sft-dataset
library_name: transformers
model_name: qwen2.5-1.5b-slips-immune-risk
tags:
- base_model:finetune:unsloth/Qwen2.5-1.5B-Instruct
- network-security
- ids
- slips
- risk-assessment
- cause-analysis
- cybersecurity
- lora
- sft
- transformers
- trl
- unsloth
license: apache-2.0
language:
- en
pipeline_tag: text-generation
---

# Qwen2.5-1.5B — Slips IDS Cause Analysis & Risk Assessment

## Model Description

A fine-tuned version of [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) specialized for dual-task analysis of network security incidents from [Slips IDS](https://github.com/stratosphereips/StratosphereLinuxIPS):

1. **Cause Analysis** — identifying the most likely cause of the incident (malicious activity, misconfiguration, or legitimate behavior) with structured reasoning and alternative hypotheses
2. **Risk Assessment** — producing a calibrated risk level, business impact statement, likelihood of malicious activity, and investigation priority

Slips is a network intrusion detection system that generates DAG-structured alert logs — chains of related security events per source IP per time window. This model takes those raw DAG logs and produces two complementary analyses that help analysts understand *why* an incident occurred and *how urgently* it should be investigated.

The model was fine-tuned using SFT (Supervised Fine-Tuning) on a **combined cause+risk dataset** with best-of-N response selection: for each training incident, the highest-scoring response among GPT-4o, GPT-4o-mini, Qwen2.5 3B, and Qwen2.5 1.5B (judged by an LLM-as-judge) was selected as ground truth. A single LoRA adapter handles both task types.

## Quick Start

### Ollama (Recommended)

Quantized GGUF models are the recommended way to run this model locally. Three quantization levels are available:

```bash
# q4_k_m — smallest, fastest (recommended for most use cases)
ollama run stratosphere/qwen2.5-1.5b-slips-immune-risk:q4_k_m

# q5_k_m — balanced quality/size
ollama run stratosphere/qwen2.5-1.5b-slips-immune-risk:q5_k_m

# q8_0 — highest quality quantized version
ollama run stratosphere/qwen2.5-1.5b-slips-immune-risk:q8_0
```

All three tags are available on [Ollama Hub](https://ollama.com/stratosphere/qwen2.5-1.5b-slips-immune-risk). Use the prompts in the Python section below to structure your queries.

### Python (Transformers)

The model uses two distinct prompt formats — one for cause analysis and one for risk assessment — applied to the same incident DAG.

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_id = "stratosphere/qwen2.5-1.5b-slips-immune-risk"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="auto")

dag_analysis = """
...  # paste your Slips DAG analysis here
"""

incident = {
    "incident_id": "abc123",
    "source_ip": "192.168.1.100",
    "timewindow": "5",
    "threat_level": 8.5,
    "timeline": "2024-01-15 14:00:00 to 2024-01-15 15:00:00",
    "event_count": 42,
    "dag_analysis": dag_analysis,
}

# --- Task 1: Cause Analysis ---
cause_prompt = f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured analysis of possible causes.

INCIDENT METADATA:
- Incident ID: {incident['incident_id']}
- Source IP: {incident['source_ip']}
- Timewindow: {incident['timewindow']}
- Accumulated Threat Level: {incident['threat_level']}
- Time Range: {incident['timeline']}
- Total Events: {incident['event_count']}

SECURITY EVIDENCE:
{incident['dag_analysis']}

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

# --- Task 2: Risk Assessment ---
risk_prompt = f"""You are a cybersecurity analyst. Analyze the following network security incident and provide a structured risk assessment.

INCIDENT METADATA:
- Incident ID: {incident['incident_id']}
- Source IP: {incident['source_ip']}
- Timewindow: {incident['timewindow']}
- Accumulated Threat Level: {incident['threat_level']}
- Time Range: {incident['timeline']}
- Total Events: {incident['event_count']}

SECURITY EVIDENCE:
{incident['dag_analysis']}

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
- Maintain uniform structure and depth across all assessments"""

for prompt in [cause_prompt, risk_prompt]:
    messages = [{"role": "user", "content": prompt}]
    input_ids = tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(model.device)
    output = model.generate(input_ids, max_new_tokens=1024, do_sample=False)
    print(tokenizer.decode(output[0][input_ids.shape[1]:], skip_special_tokens=True))
    print("\n" + "="*60 + "\n")
```

## Training Details

### Dataset

The training data is publicly available at [stratosphere/immune-risk-sft-dataset](https://huggingface.co/datasets/stratosphere/immune-risk-sft-dataset).

- **Source**: 826 incidents from real Slips IDS network captures, filtered by quality (cause score ≥ 14, risk score ≥ 10, token length checks)
- **Responses**: 4 model responses per incident per task (GPT-4o, GPT-4o-mini, Qwen2.5 3B, Qwen2.5 1.5B) scored by an LLM-as-judge
- **Selection**: Best-of-N — highest-scoring response per incident per task used as training target
- **Combined dataset**: cause and risk records interleaved so the model sees both task types throughout training (1328 train / 148 eval records)
- **Split**: 90% train / 10% eval

### Training Procedure

| Parameter | Value |
|-----------|-------|
| Base model | `unsloth/Qwen2.5-1.5B-Instruct` |
| Training method | SFT (Supervised Fine-Tuning) |
| Framework | Unsloth + TRL SFTTrainer |
| LoRA rank (`r`) | 64 |
| LoRA alpha | 64 |
| LoRA dropout | 0.0 |
| RSLoRA | enabled (required at r=64) |
| LoRA targets | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Sequence length | 4096 |
| Batch size | 1 (effective: 16 via gradient accumulation) |
| Gradient accumulation steps | 16 |
| Learning rate | 2e-5 |
| LR scheduler | cosine |
| Warmup steps | 20 |
| Weight decay | 0.01 |
| Epochs | 3 |
| Optimizer | adamw_8bit |
| Precision | BF16 |
| Quantization (training) | 4bit (QLoRA) |
| Response masking | `train_on_responses_only` — loss computed on assistant turns only |

### Framework Versions

- Unsloth: 2026.3.18
- Transformers: (auto-detected)
- PyTorch: (auto-detected)

## Evaluation

Evaluated on 67 held-out Slips IDS incidents using `qwen3.5` as an independent LLM-as-judge. The judge ranked all 5 model responses per incident simultaneously, scoring cause analysis and risk assessment separately. Model labels were randomized per incident to prevent position bias. Inference was performed at 4096 max input tokens, 1024 max output tokens.

### Overall Results

| Rank | Model | Avg Position | Avg Cause Score | Avg Risk Score | Win Rate | Wins |
|------|-------|--------------|-----------------|----------------|----------|------|
| 1 | GPT-4o | 1.70 | 15.33 | 11.99 | 40.3% | 27 |
| 2 | **Qwen2.5-1.5B (finetuned)** | **1.73** | **15.58** | **10.27** | **37.3%** | **25** |
| 3 | GPT-4o-mini | 2.11 | 15.31 | 11.63 | 19.4% | 13 |
| 4 | Qwen2.5 1.5B (baseline) | 3.48 | 9.15 | 8.79 | 3.0% | 2 |
| 5 | Qwen2.5 3B (baseline) | 3.53 | 7.40 | 9.61 | 0.0% | 0 |

The finetuned 1.5B model is nearly tied with GPT-4o on overall ranking (avg position 1.73 vs 1.70) and **beats GPT-4o on cause analysis score** (15.58 vs 15.33). Win rate of 37.3% substantially outperforms GPT-4o-mini (19.4%) and both untuned baselines.

### By Complexity

| Complexity | Events | Cause Score | Risk Score | Win Rate |
|------------|--------|-------------|------------|----------|
| Simple | < 500 (33 incidents) | 15.70 | 9.32 | 54.5% |
| Medium | 500–1999 (8 incidents) | 19.38 | 12.62 | 50.0% |
| Complex | ≥ 2000 (11 incidents) | 13.20 | 11.80 | 27.3% |

Strong on simple and medium incidents. Performance drops on complex incidents (≥ 2000 events), consistent with DAG truncation at the 4096-token input limit.

### By Category

| Category | Count | Cause Score | Risk Score | Win Rate |
|----------|-------|-------------|------------|----------|
| Malware | 47 | 15.52 | 10.08 | 51.1% |
| Normal | 5 | 16.40 | 12.60 | 20.0% |

### Known Limitations

- **Risk scores lag cause scores**: cause avg 15.58 vs risk avg 10.27 — the model is stronger at identifying causes than calibrating risk levels. This reflects a task imbalance in the training data rather than a fundamental model limitation.
- **Complex incidents**: performance drops on incidents with ≥ 2000 events due to DAG truncation at the sequence length limit.
- **Normal traffic**: only 5 Normal incidents in the eval set — results for that category are not statistically reliable.

## Intended Use

- Automated cause analysis of Slips IDS alerts for security analysts
- Risk prioritization and triage of network incidents
- Input to downstream reporting or ticketing workflows

## Out-of-Scope Use

- General-purpose chat or instruction following
- Security domains outside network IDS (malware analysis, vulnerability scanning, etc.)
- Non-English inputs

## Citation

```bibtex
@misc{qwen2.5-1.5b-slips-immune-risk,
  title        = {Qwen2.5-1.5B fine-tuned for Slips IDS cause analysis and risk assessment},
  author       = {Stratosphere Laboratory, CTU Prague},
  year         = {2026},
  howpublished = {\url{https://huggingface.co/stratosphere/qwen2.5-1.5b-slips-immune-risk}}
}
```

## Acknowledgments

This work was supported by the [NLnet Foundation](https://nlnet.nl) as part of the IMMUNE project. NLnet Foundation promotes open internet standards and open source software.

## Model Details

- **Model size**: 1.5B params
- **Tensor type**: FP16
- **License**: Apache-2.0
- **Tags**: Text Generation, Transformers, Safetensors, Network Security, IDS, SLIPS, Risk Assessment, Cause Analysis, Cybersecurity, LoRA, SFT, TRL, Unsloth

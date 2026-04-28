# Qwen2.5-1.5B Slips IDS - Immune Risk

A fine-tuned version of [Qwen2.5-1.5B-Instruct](https://ollama.com/library/qwen2.5:1.5b) specialized in cause analysis and risk assessment for [Slips IDS](https://github.com/stratosphereips/StratosphereLinuxIPS) alert logs.

Trained at the [Stratosphere Research Laboratory](https://www.stratosphereips.org/), Czech Technical University in Prague.

## Overview

Slips is a machine-learning-based network intrusion detection system (IDS). It generates DAG-structured evidence logs that group related security events for an IP address and time window.

This model performs two complementary analyst tasks over the same Slips DAG:

1. **Cause Analysis** - identify the likely cause of an incident, including malicious activity, legitimate activity, and misconfiguration hypotheses.
2. **Risk Assessment** - assign a calibrated risk level and explain business impact, malicious likelihood, and investigation priority.

Optimized for local and edge deployment through Ollama. The model is small enough to run on constrained systems while producing structured analyst-facing outputs.

**Fine-tuning method:** SFT using [Unsloth](https://github.com/unslothai/unsloth) + LoRA on combined cause+risk records.
**Training data:** Best-of-N responses selected from GPT-4o, GPT-4o-mini, Qwen2.5 3B, and Qwen2.5 1.5B baseline outputs, scored by an LLM judge.

## Usage

```bash
ollama run stratosphere/qwen2.5-1.5b-slips-immune-risk
```

The default `latest` tag points to `q4_k_m`.

### Quantization Tags

| Tag | Use case |
|---|---|
| `latest` / `q4_k_m` | Recommended default; smallest and fastest |
| `q5_k_m` | Better quality/size tradeoff |
| `q8_0` | Highest quality quantized version |

```bash
# Default Q4_K_M
ollama pull stratosphere/qwen2.5-1.5b-slips-immune-risk

# Balanced quality/size
ollama pull stratosphere/qwen2.5-1.5b-slips-immune-risk:q5_k_m

# Highest quality quantized model
ollama pull stratosphere/qwen2.5-1.5b-slips-immune-risk:q8_0
```

## Prompting

This model was trained with two separate user prompt formats. Run both prompts on the same incident DAG if you want a complete cause+risk report.

The Ollama model uses Qwen chat formatting internally, so send the prompt directly as the user message.

### Incident Input

Both prompts expect this metadata plus the Slips DAG evidence:

```text
INCIDENT METADATA:
- Incident ID: <incident_id>
- Source IP: <source_ip>
- Timewindow: <timewindow>
- Accumulated Threat Level: <threat_level>
- Time Range: <start> to <end>
- Total Events: <event_count>

SECURITY EVIDENCE:
<compacted Slips DAG analysis>
```

### Cause Analysis Prompt

```text
You are a cybersecurity analyst. Analyze the following network security incident and provide a structured analysis of possible causes.

INCIDENT METADATA:
- Incident ID: <incident_id>
- Source IP: <source_ip>
- Timewindow: <timewindow>
- Accumulated Threat Level: <threat_level>
- Time Range: <timeline>
- Total Events: <event_count>

SECURITY EVIDENCE:
<dag_analysis>

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
- Avoid generic definitions or unnecessary context
```

### Risk Assessment Prompt

```text
You are a cybersecurity analyst. Analyze the following network security incident and provide a structured risk assessment.

INCIDENT METADATA:
- Incident ID: <incident_id>
- Source IP: <source_ip>
- Timewindow: <timewindow>
- Accumulated Threat Level: <threat_level>
- Time Range: <timeline>
- Total Events: <event_count>

SECURITY EVIDENCE:
<dag_analysis>

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
```

## Command-Line Examples

Cause analysis:

```bash
ollama run stratosphere/qwen2.5-1.5b-slips-immune-risk:q4_k_m '<paste the cause analysis prompt here>'
```

Risk assessment:

```bash
ollama run stratosphere/qwen2.5-1.5b-slips-immune-risk:q4_k_m '<paste the risk assessment prompt here>'
```

For repeatable evaluation, use temperature `0` through the Ollama API or the OpenAI-compatible endpoint.

## OpenAI-Compatible API Example

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

response = client.chat.completions.create(
    model="stratosphere/qwen2.5-1.5b-slips-immune-risk:q4_k_m",
    messages=[
        {"role": "user", "content": risk_prompt},
    ],
    temperature=0,
    max_tokens=1024,
)

print(response.choices[0].message.content)
```

## Evaluation

The risk model was evaluated on held-out Slips IDS incidents with an independent LLM-as-judge. The judge ranks model outputs for cause analysis and risk assessment separately while randomizing labels to reduce position bias.

The local evaluation path in this repository is:

```bash
python3 run_finetuned_inference_risk.py \
  --model-name stratosphere/qwen2.5-1.5b-slips-immune-risk:q4_k_m \
  --url http://localhost:11434/v1 \
  --input risk_filtered_eval.json \
  --output risk_finetuned_eval_results.json

python3 ../alert_summary/evaluate_risk.py \
  --input risk_finetuned_eval_results.json \
  --output ../alert_summary/results/risk_finetuned_results.json
```

Reported held-out results from the risk model card:

| Model | Avg Position | Avg Cause Score | Avg Risk Score | Win Rate |
|---|---:|---:|---:|---:|
| GPT-4o | 1.70 | 15.33 | 11.99 | 40.3% |
| Qwen2.5-1.5B Immune Risk | 1.73 | 15.58 | 10.27 | 37.3% |
| GPT-4o-mini | 2.11 | 15.31 | 11.63 | 19.4% |
| Qwen2.5 1.5B baseline | 3.48 | 9.15 | 8.79 | 3.0% |
| Qwen2.5 3B baseline | 3.53 | 7.40 | 9.61 | 0.0% |

## Publishing

The publish script builds and pushes all risk quantization tags:

```bash
./publish_to_ollama_risk.sh
```

Build one tag only:

```bash
./publish_to_ollama_risk.sh --quant q5_k_m
```

The script publishes:

```text
stratosphere/qwen2.5-1.5b-slips-immune-risk:q4_k_m
stratosphere/qwen2.5-1.5b-slips-immune-risk:q5_k_m
stratosphere/qwen2.5-1.5b-slips-immune-risk:q8_0
stratosphere/qwen2.5-1.5b-slips-immune-risk:latest
```

## Integration with Slips

Use the Slips DAG generator to compact raw alert logs before calling the model. The model was trained on structured DAG evidence, not raw unprocessed JSONL events.

For live Slips integration, call the model twice per incident:

1. Cause analysis prompt
2. Risk assessment prompt

Keep the prompt structure stable. Changing section names or output requirements can degrade formatting and evaluation consistency.

## License

This fine-tuned model is released under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), consistent with the base Qwen2.5 model license.

## Links

- [Ollama model](https://ollama.com/stratosphere/qwen2.5-1.5b-slips-immune-risk)
- [Slips IDS](https://github.com/stratosphereips/StratosphereLinuxIPS)
- [Stratosphere Research Laboratory](https://www.stratosphereips.org/)
- [Training code](https://github.com/stratosphereips/Slips-tools/tree/main/unsloth-scripts)
- [Base model: Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)

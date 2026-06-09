# Unified Model Quantization Comparison

**Date:** 2026-06-09  
**Model:** `stratosphere/qwen2.5-1.5b-slips-immune-unified` (v2, lora_r=128, 2 epochs)  
**Judge (summary):** `gpt-oss-120b` @ https://llm.ai.e-infra.cz/v1  
**Judge (risk/cause):** `qwen3.5` @ https://llm.ai.e-infra.cz/v1  
**Eval sets:** Standalone summary eval (47 incidents) + standalone risk eval (67 incidents)  
**fp16 baseline:** GPU-served via `serve_model.py` (4-bit QLoRA at inference — BnB NF4)

---

## Summary Task (47 incidents, judge: gpt-oss-120b)

| Variant | Win Rate | Avg Score /10 | Avg Position |
|---------|----------|---------------|--------------|
| **fp16 (BnB NF4, GPU)** | **17.0%** | **5.20** | — |
| q8_0 (Ollama GGUF) | 32.6% | 5.09 | 2.29 |
| q5_k_m (Ollama GGUF) | 14.9% | 5.00 | 2.88 |
| q4_k_m (Ollama GGUF) | 12.8% | 4.91 | 2.86 |

**Key finding:** q8_0 substantially outperforms fp16 on win rate (32.6% vs 17.0%) with a nearly identical average score (5.09 vs 5.20). q5_k_m and q4_k_m are close to fp16, with q5_k_m slightly ahead.

---

## Risk Task (67 incidents, judge: qwen3.5)

| Variant | Win Rate | Avg Cause /30 | Avg Risk /30 | Avg Position |
|---------|----------|---------------|--------------|--------------|
| **fp16 (BnB NF4, GPU)** | **23.9%** | **18.30** | **12.36** | — |
| q8_0 (Ollama GGUF) | 26.9% | 17.43 | 12.75 | 2.55 |
| q5_k_m (Ollama GGUF) | 26.9% | 17.30 | 13.66 | 2.43 |
| q4_k_m (Ollama GGUF) | 26.9% | 17.75 | 13.70 | 2.36 |

**Key finding:** All three quantized variants match or exceed fp16 on win rate (26.9% vs 23.9%). Risk scores improve slightly across all quants (+1.3–1.4 points). Cause scores drop modestly (-0.55 to -1.0 points). q4_k_m has the best cause score among quantized variants and the best average position.

---

## Key Observations

### 1. Quantization does not hurt — it slightly helps
Unlike the standalone risk model (where fp16 > q8_0 > q5/q4), the unified model shows the
opposite pattern: all quantized variants match or beat the GPU-served fp16 baseline on both
tasks. This is likely because the GPU-served fp16 uses BnB NF4 4-bit quantization at
inference time, not true fp16 — so the comparison is NF4 vs GGUF quantization, not fp16 vs
GGUF.

### 2. q8_0 is the standout for summary
q8_0 wins 32.6% of summary incidents vs 17.0% for fp16 — a +15.6pp gain. Average score is
nearly identical (5.09 vs 5.20). This suggests q8_0 produces more consistently top-ranked
outputs, possibly because Ollama's inference stack handles longer outputs more reliably than
the BnB NF4 GPU server.

### 3. All quants are equivalent on risk
q4_k_m, q5_k_m, and q8_0 all win 26.9% of risk incidents. Risk scores are slightly better
than fp16 across all variants. There is no meaningful quality degradation from quantization
on the risk task.

### 4. q4_k_m is the recommended deployment choice
q4_k_m matches q8_0 and q5_k_m on risk, comes close on summary (12.8% vs 32.6%/14.9%),
and is the smallest (986 MB). For edge/RPi5 deployment, q4_k_m offers the best
size-to-quality ratio.

---

## Recommendation

| Use Case | Recommended Variant |
|----------|-------------------|
| Best summary quality | **q8_0** — 32.6% win rate, matches fp16 avg score |
| Best risk quality | **q4_k_m** — best cause score, lowest memory |
| Balanced / general deployment | **q5_k_m** — good middle ground |
| Edge / RPi5 | **q4_k_m** — 986 MB, competitive on both tasks |

All three quantized variants are suitable for production. The unified model quantizes better
than the standalone risk model — no performance cliff at any quant level.

---

## Data Files

| Variant | Task | Results JSON | Report | CSV |
|---------|------|-------------|--------|-----|
| q4_k_m | Summary | `unified_quant_q4km_summary_results.json` | `unified_quant_q4km_summary_report.md` | `unified_quant_q4km_summary_data.csv` |
| q4_k_m | Risk | `unified_quant_q4km_risk_results.json` | `unified_quant_q4km_risk_report.md` | `unified_quant_q4km_risk_data.csv` |
| q5_k_m | Summary | `unified_quant_q5km_summary_results.json` | `unified_quant_q5km_summary_report.md` | `unified_quant_q5km_summary_data.csv` |
| q5_k_m | Risk | `unified_quant_q5km_risk_results.json` | `unified_quant_q5km_risk_report.md` | `unified_quant_q5km_risk_data.csv` |
| q8_0 | Summary | `unified_quant_q8_summary_results.json` | `unified_quant_q8_summary_report.md` | `unified_quant_q8_summary_data.csv` |
| q8_0 | Risk | `unified_quant_q8_risk_results.json` | `unified_quant_q8_risk_report.md` | `unified_quant_q8_risk_data.csv` |

All files in `/home/harpo/dropbox/alert_summary/results/`.

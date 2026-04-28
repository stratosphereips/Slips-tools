# Finetuning Improvement Plan: Slips IDS Risk Analysis

## Context

Goal: finetune a small LLM (Qwen2.5 3B, targeting RPi5 deployment) to produce structured cause analysis and risk assessments from Slips IDS alert DAG representations.

**Current baseline:** DAG analysis as input → GPT-4o response as output → SFT (supervised finetuning).

**Approach (first version):** Two separate finetuned tasks, mirroring the original dataset generation pipeline:
- **Task A — Cause Analysis:** cause prompt → `cause_analysis` output
- **Task B — Risk Assessment:** risk prompt → `risk_assessment` output

Each task is trained independently, using the same prompt format that `alert_cause_risk_analyzer.py` sent to the LLMs when building the dataset. No prompt modifications — the training conversations are faithful reproductions of the original LLM calls.

**Existing assets:**
- `../alert_summary/datasets/risk_dataset.json` — multi-model dataset with 4 model responses per incident (GPT-4o, GPT-4o-mini, Qwen2.5:15b, Qwen2.5:3b), each response is a dict with `cause_analysis` and `risk_assessment` fields
- `../alert_summary/datasets/risk_dataset_results_oss.json` — **LLM-as-judge results already generated** for all 532 incidents, with per-model scores and rankings. Key finding: **GPT-4o dominates risk** (avg score 7.98, wins 65.6% of incidents), GPT-4o-mini ranks second (avg 7.34, 26.3%), Qwen2.5:3b third (5.33, 4.9%), Qwen2.5:15b weakest (4.29, 3.2%).
- `../alert_summary/alert_cause_risk_analyzer.py` — original dataset generation script; defines `_build_cause_prompt()` and `_build_risk_prompt()`, both sent as single user-turn messages (no system message)
- `../alert_summary/run_evaluation_risk.sh` — fully automated end-to-end risk evaluation pipeline (sample → judge → analyze → HTML dashboard)
- `train_qwen.py`, `config.yaml` — Unsloth + LoRA + SFTTrainer stack (shared with summarization)

---

## Training Conversation Format

The dataset was generated with **no system message** — each prompt was sent as a single user turn containing the full instructions + incident data. Training must match this exactly.

**Task A — Cause Analysis:**
```json
[
  {"role": "user",      "content": "<full _build_cause_prompt() output for this incident>"},
  {"role": "assistant", "content": "<cause_analysis text>"}
]
```

**Task B — Risk Assessment:**
```json
[
  {"role": "user",      "content": "<full _build_risk_prompt() output for this incident>"},
  {"role": "assistant", "content": "<risk_assessment text>"}
]
```

The prompt text is reconstructed at dataset-build time by calling `_build_cause_prompt()` / `_build_risk_prompt()` from `alert_cause_risk_analyzer.py` with the incident's DAG data.

---

## Proposed Improvements

### 1. Best-of-N Ground Truth Selection

**Problem:** Training solely on GPT-4o outputs is noisy. Judge results show GPT-4o wins 65.6% of incidents, meaning ~34% are better covered by another model.

**Status:** Judge scores are available in `risk_dataset_results_oss.json` for all 532 incidents. No additional evaluation runs needed.

**Approach:** Join scores from the results file with response texts from `risk_dataset.json` using `incident_id`, then select the highest-scoring model's response per incident as ground truth. Expected: ~66% GPT-4o, ~26% GPT-4o-mini, ~5% Qwen2.5:3b chosen.

**Key difference from summarization:** Each response is a dict (`cause_analysis`, `risk_assessment`). Best-of-N selection applies to the **whole response** — the same winning model's `cause_analysis` and `risk_assessment` are used together, keeping the two outputs internally consistent.

**New script:** `select_best_responses_risk.py` (in `unsloth-scripts/`)

---

### 2. Preference Dataset + DPO/ORPO Training

**Problem:** SFT only teaches "what a good answer looks like." It does not teach the model to avoid weak patterns.

**Approach:** Build a preference dataset from the multi-model outputs using the already-available scores:
- **Chosen**: highest-scored response per incident
- **Rejected**: Qwen2.5:15b output (avg score 4.29, weakest by a large margin) or lowest-scored response per incident

Train with DPO or ORPO (both supported by TRL, already in the stack) after SFT warmup.

**New script:** `create_preference_dataset_risk.py` (in `unsloth-scripts/`)
**Updates:** `train_qwen.py` (add DPO/ORPO trainer option if not already present), `config.yaml`

---

### 3. Dataset Quality Filtering

**Problem:** Some training examples teach bad habits (generic outputs, wrong risk levels).

**Approach:** Filter before training using the available judge scores:
- Reject examples where best-of-N score is below 5 (bottom quartile — note: risk scores are higher overall than summarization scores, adjust threshold accordingly)
- Reject examples where `cause_analysis` is < 50 tokens or > 600 tokens
- Reject examples where `risk_assessment` is < 30 tokens or > 300 tokens
- Reject examples where `risk_assessment` does not contain a valid risk level keyword (`Critical`, `High`, `Medium`, `Low`)

**New script:** `filter_dataset_risk.py` (in `unsloth-scripts/`)

---

### 4. Train/Validation Split

**Problem:** With ~532 incidents (fewer after filtering), there is no held-out set to detect overfitting.

**Approach:** Same as summarization plan — stable 90/10 train/eval split at dataset-build time:
- All dataset-building scripts emit `<name>_train.json` (90%) and `<name>_eval.json` (10%)
- Split is shuffled with `random_state=42` for reproducibility
- `config.yaml` gains a `dataset.eval_path` key (`null` = skip eval)
- `train_qwen.py` loads eval split and wires `eval_dataset` into `SFTTrainer`

**Scripts affected:**
- `filter_dataset_risk.py` (new) — emit `risk_filtered_train.json` + `risk_filtered_eval.json`
- `select_best_responses_risk.py` (new) — emit `risk_train_dataset.json` + `risk_eval_dataset.json`
- `create_preference_dataset_risk.py` (new) — emit `risk_dpo_train_dataset.json` + `risk_dpo_eval_dataset.json`

---

### 5. Prompt Template Parity

**Key constraint:** Do NOT modify `alert_cause_risk_analyzer.py`. The training prompts must be reconstructed to match what was used during dataset generation.

**Approach:** In `select_best_responses_risk.py`, import and call `_build_cause_prompt()` and `_build_risk_prompt()` directly from `alert_cause_risk_analyzer.py` to reconstruct the exact user-turn content for each incident. This guarantees zero drift between the prompts used during dataset generation and the prompts used at training time — and at inference time, since the deployed model will also be called through `alert_cause_risk_analyzer.py`.

---

### 6. Two-Stage Training: SFT → DPO

Best practice for small instruction-tuned models:

- **Stage 1 — SFT**: Train on best-of-N filtered ground truth (improvements 1 + 3)
- **Stage 2 — DPO/ORPO**: Apply preference learning using chosen/rejected pairs (improvement 2)

Both Task A (cause) and Task B (risk) go through the same two stages. They can be trained as separate adapters or sequentially on the same adapter — the simpler approach is separate adapters, one per task.

**Files:** `train_qwen.py`, `config.yaml`

---

### 7. Close the Evaluation Loop

The risk evaluation pipeline is fully automated in `../alert_summary/run_evaluation_risk.sh`. After finetuning, inject the finetuned model's outputs into the evaluation sample and re-run against the existing 4-model baseline.

**Reference scores to beat:**
- GPT-4o: avg 7.98 (wins 65.6%)
- GPT-4o-mini: avg 7.34 (wins 26.3%)
- Qwen2.5:3b baseline: avg 5.33 (wins 4.9%)

**Then re-run:** `../alert_summary/run_evaluation_risk.sh`

---

## Recommended Execution Order

| Step | Action | Script | Notes |
|------|--------|--------|-------|
| 1 | Filter low-quality examples → emit train/eval split | `filter_dataset_risk.py` (new) | 90/10, seed 42, score threshold 5 |
| 2 | Select best response per incident, reconstruct prompts | `select_best_responses_risk.py` (new) | imports prompts from `alert_cause_risk_analyzer.py` |
| 3 | SFT with validation loss tracking | `train_qwen.py` + `config.yaml` | run twice: once for cause, once for risk |
| 4 | Build preference dataset (DPO) | `create_preference_dataset_risk.py` (new) | 90/10 split |
| 5 | DPO/ORPO training | `train_qwen.py` (updated) | same eval wiring |
| 6 | Evaluate finetuned model | `../alert_summary/run_evaluation_risk.sh` | compare vs 4-model baseline |

---

## Key Files Reference

| Purpose | Path |
|---------|------|
| Multi-model risk dataset (4 responses/incident) | `../alert_summary/datasets/risk_dataset.json` |
| Judge results (scores for all 532 incidents) | `../alert_summary/datasets/risk_dataset_results_oss.json` |
| Original prompt definitions (do not modify) | `../alert_summary/alert_cause_risk_analyzer.py` |
| Training script | `train_qwen.py` |
| Training config | `config.yaml` |
| Full risk eval pipeline | `../alert_summary/run_evaluation_risk.sh` |
| Filter + train/eval split script | `filter_dataset_risk.py` (new, `unsloth-scripts/`) |
| Best-response selector + prompt reconstructor | `select_best_responses_risk.py` (new, `unsloth-scripts/`) |
| Preference dataset builder | `create_preference_dataset_risk.py` (new, `unsloth-scripts/`) |
| SFT cause training split (output) | `risk_cause_train_dataset.json` (`unsloth-scripts/`) |
| SFT cause validation split (output) | `risk_cause_eval_dataset.json` (`unsloth-scripts/`) |
| SFT risk training split (output) | `risk_assessment_train_dataset.json` (`unsloth-scripts/`) |
| SFT risk validation split (output) | `risk_assessment_eval_dataset.json` (`unsloth-scripts/`) |
| DPO training split (output) | `risk_dpo_train_dataset.json` (`unsloth-scripts/`) |
| DPO validation split (output) | `risk_dpo_eval_dataset.json` (`unsloth-scripts/`) |

---

## Differences from Summarization Plan

| Aspect | Summarization | Risk |
|--------|--------------|------|
| Response format | Plain string | Dict: `{cause_analysis, risk_assessment}` |
| Training tasks | Single task | Two tasks (cause + risk), trained separately |
| Dominant model | GPT-4o-mini (46.1%) | GPT-4o (65.6%) |
| Score threshold (filter) | 4 | 5 (scores are higher overall) |
| Token limits | 50–400 tokens | cause: 50–600, risk: 30–300 |
| System message | Yes (in `select_best_responses.py`) | No — full prompt in user turn only |
| Prompt source | Inline in `select_best_responses.py` | Imported from `alert_cause_risk_analyzer.py` |

---

## Out of Scope

- Modifying `alert_cause_risk_analyzer.py` or any dataset generation script
- Combining cause + risk into a single model output (deferred to a second approach)
- RLHF with human feedback
- Full model training (LoRA adapters only via Unsloth)
- Changing base model (Qwen2.5:3b stays)
- Rebuilding evaluation infrastructure (already fully automated)

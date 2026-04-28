# Finetuning Improvement Plan: Slips IDS Summarization

## Context

Goal: finetune a small LLM (Qwen2.5 3B, targeting RPi5 deployment) to produce concise, actionable security summaries from Slips IDS alert DAG representations.

**Current baseline:** DAG analysis as input → GPT-4o response as output → SFT (supervised finetuning).

**Existing assets:**
- `../alert_summary/datasets/summarization_dataset_v3.json` — multi-model dataset with 4 model responses per incident (GPT-4o, GPT-4o-mini, Qwen2.5:15b, Qwen2.5:3b)
- `../alert_summary/datasets/summarization_dataset_v3_results_oss.json` — **LLM-as-judge results already generated** for all 532 incidents, with per-model scores and rankings. Judge ran via OSS-compatible endpoint (not OpenAI). Key finding: **GPT-4o-mini is the strongest model** (avg score 6.35, wins 46.1% of incidents), GPT-4o ranks second (avg 5.65, 36.7%), Qwen2.5:3b third (4.38, 15.6%), Qwen2.5:15b weakest (2.81, 1.7%).
- `../alert_summary/evaluate_summaries.py` — LLM-as-judge script, already supports OSS/non-OpenAI judge models via `--judge` flag and configurable `base_url`
- `../alert_summary/run_evaluation_summary.sh` — fully automated end-to-end evaluation pipeline (sample → judge → analyze → HTML dashboard)
- `train_qwen.py`, `prepare_data.py`, `config.yaml` — Unsloth + LoRA + SFTTrainer stack

---

## Proposed Improvements

### 1. Best-of-N Ground Truth Selection

**Problem:** Training solely on GPT-4o outputs is noisy — some responses may be verbose, unfocused, or contain hallucinated patterns. The judge results confirm GPT-4o-mini actually outperforms GPT-4o on 46.1% of incidents.

**Status:** Judge scores are available in `summarization_dataset_v3_results_oss.json` for all 532 incidents. No additional evaluation runs needed.

**Approach:** Join scores from the results file with response texts from `summarization_dataset_v3.json` using `incident_id`, then select the highest-scoring model's response per incident as ground truth. Expected: ~46% GPT-4o-mini, ~37% GPT-4o, ~16% Qwen2.5:3b chosen.

**New script:** `select_best_responses.py` (in `unsloth-scripts/`)

---

### 2. Preference Dataset + DPO/ORPO Training

**Problem:** SFT only teaches "what a good answer looks like." It does not teach the model to avoid weak patterns.

**Approach:** Build a preference dataset from the multi-model outputs using the already-available scores:
- **Chosen**: highest-scored response per incident
- **Rejected**: Qwen2.5:15b output (avg score 2.81, weakest by a large margin) or lowest-scored response per incident

Train with DPO or ORPO (both supported by TRL, already in the stack) after SFT warmup. This is the approach used in Zephyr and Mistral-Instruct.

**New script:** `create_preference_dataset.py` (in `unsloth-scripts/`)
**Updates:** `train_qwen.py` (add DPO/ORPO trainer option), `config.yaml`

---

### 3. Dataset Quality Filtering

**Problem:** Some training examples teach bad habits (generic outputs, wrong threat levels).

**Approach:** Filter before training using the available judge scores:
- Reject summaries < 50 tokens or > 400 tokens
- Reject examples where summary threat level contradicts DAG threat level
- Reject examples where the best-of-N score is below 4 (bottom quartile based on observed score distribution)

**New script:** `filter_dataset.py` (in `unsloth-scripts/`)

---

### 4. Train/Validation Split

**Problem:** With ~532 incidents (fewer after filtering), there is no held-out set to detect overfitting. The current `train_qwen.py` passes only a `train_dataset` to `SFTTrainer`, and the `evaluation` section of `config.yaml` (with `eval_steps`, `metric_for_best_model`, `load_best_model_at_end`) is not wired into `TrainingArguments` or the trainer.

**Approach:** Add a stable 90/10 train/validation split at dataset-build time:
- All dataset-building scripts emit `<name>_train.json` (90%) and `<name>_eval.json` (10%)
- Split is shuffled with `random_state=42` for reproducibility (use `sklearn.model_selection.train_test_split` or numpy equivalent)
- `config.yaml` gains a `dataset.eval_path` key (`null` = skip eval)
- `train_qwen.py` loads the eval split, wires `eval_dataset` into `SFTTrainer`, and activates the `eval_strategy`, `eval_steps`, `metric_for_best_model`, `load_best_model_at_end`, and `save_total_limit` fields in `TrainingArguments`

**Scripts affected:**
- `filter_dataset.py` (new, in `unsloth-scripts/`) — emit `_train.json` + `_eval.json`
- `select_best_responses.py` (new, in `unsloth-scripts/`) — same
- `create_preference_dataset.py` (new, in `unsloth-scripts/`) — same (for DPO chosen/rejected pairs)
- `train_qwen.py` — load eval split, wire into trainer
- `config.yaml` — add `dataset.eval_path`, fix eval fields, add `save_total_limit: 2`

**Output files:** All generated train/eval JSON files are written to `unsloth-scripts/` (e.g., `train_dataset.json`, `eval_dataset.json`) so they are co-located with the training scripts and config.

**Key config changes:**
```yaml
dataset:
  eval_path: "eval_dataset.json"   # null = skip validation

evaluation:
  eval_steps: 50                   # reduced from 100 (appropriate for small dataset)
  save_total_limit: 2              # keep only 2 checkpoints to save disk
```

**Verification:** Trainer logs show `eval_loss` at each eval step; best checkpoint is saved after training.

---

### 5. Prompt Template Parity

**Problem:** If the system prompt at finetuning time differs from inference time, small models fail to generalize.

**Approach:**
- Always use `--merge-evidence` / `--group-events` DAG format in training data (achieves 72-96% token reduction)
- Define a single system prompt used by both `prepare_data.py` and the inference wrapper
- Verify the Alpaca/ChatML template in `train_qwen.py` matches the inference template

**Files to align:** `prepare_data.py`, `../alert_summary/alert_dag_parser_llm.py`

---

### 6. Two-Stage Training: SFT → DPO

Best practice for small instruction-tuned models:

- **Stage 1 — SFT**: Train on best-of-N filtered ground truth (improvements 1 + 3)
- **Stage 2 — DPO/ORPO**: Apply preference learning using chosen/rejected pairs (improvement 2)

**Files:** `train_qwen.py`, `config.yaml`

---

### 7. Close the Evaluation Loop

The evaluation pipeline is fully automated and `evaluate_summaries.py` already supports OSS judge models. After finetuning, inject the finetuned model's outputs into the evaluation sample and re-run against the existing 4-model baseline using any available judge (OpenAI or OSS).

**New script:** `../alert_summary/datasets/run_finetuned_inference.py`
**Then re-run:** `../alert_summary/run_evaluation_summary.sh`
**Note:** The finetuned model's score can be compared directly against the baseline average scores (GPT-4o-mini: 6.35, GPT-4o: 5.65, Qwen2.5:3b: 4.38).

---

## Recommended Execution Order

| Step | Action | Script | Notes |
|------|--------|--------|-------|
| 1 | Filter low-quality examples → emit train/eval split | `filter_dataset.py` (new, `unsloth-scripts/`) | 90/10, seed 42 |
| 2 | Select best response per incident | `select_best_responses.py` (new, `unsloth-scripts/`) | preserves split from step 1 |
| 3 | SFT with validation loss tracking | `train_qwen.py` + `config.yaml` | eval every 50 steps |
| 4 | Build preference dataset (DPO) | `create_preference_dataset.py` (new, `unsloth-scripts/`) | 90/10 split |
| 5 | DPO/ORPO training | `train_qwen.py` (updated) | same eval wiring |
| 6 | Evaluate finetuned model | `../alert_summary/run_evaluation_summary.sh` | compare vs 4-model baseline |

---

## Key Files Reference

| Purpose | Path |
|---------|------|
| Multi-model dataset (4 responses/incident) | `../alert_summary/datasets/summarization_dataset_v3.json` |
| Judge results (scores for all 532 incidents) | `../alert_summary/datasets/summarization_dataset_v3_results_oss.json` |
| Training script | `train_qwen.py` |
| Training config | `config.yaml` |
| Data preparation | `prepare_data.py` |
| Full eval pipeline | `../alert_summary/run_evaluation_summary.sh` |
| LLM judge script (OSS-compatible) | `../alert_summary/evaluate_summaries.py` |
| Result analysis | `../alert_summary/analyze_results.py` |
| Evaluation sample | `../alert_summary/datasets/evaluation_sample.json.gz` |
| Filter + train/eval split script | `filter_dataset.py` (new, `unsloth-scripts/`) |
| Best-response selector script | `select_best_responses.py` (new, `unsloth-scripts/`) |
| Preference dataset builder script | `create_preference_dataset.py` (new, `unsloth-scripts/`) |
| SFT training split (output) | `train_dataset.json` (`unsloth-scripts/`) |
| SFT validation split (output) | `eval_dataset.json` (`unsloth-scripts/`) |
| DPO training split (output) | `dpo_train_dataset.json` (`unsloth-scripts/`) |
| DPO validation split (output) | `dpo_eval_dataset.json` (`unsloth-scripts/`) |

---

## Out of Scope

- RLHF with human feedback (too expensive at this scale)
- Full model training (LoRA adapters only via Unsloth)
- Changing base model (Qwen2.5:3b stays)
- Rebuilding evaluation infrastructure (already fully automated)

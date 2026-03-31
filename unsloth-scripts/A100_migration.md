# A100 Migration — Recommended Configuration Changes

Target hardware: NVIDIA A100 80GB (compute capability 8.0, BF16 native)

---

## 1. `config.yaml`

### Model

| Parameter | Current (Titan V 12GB) | A100 |
|-----------|----------------------|------|
| `load_in_4bit` | `true` | `false` — full precision, plenty of VRAM |
| `max_seq_length` | `2048` | `4096` (or `8192` for very large incidents) |
| `lora_r` | `16` | `64` — higher rank, more adapter capacity |
| `lora_alpha` | `16` | `64` — keep equal to `lora_r` |
| `use_rslora` | `false` | `true` — stabilizes training at higher ranks |

### Training

| Parameter | Current (Titan V 12GB) | A100 |
|-----------|----------------------|------|
| `per_device_train_batch_size` | `1` | `8` — real batches, not simulated |
| `gradient_accumulation_steps` | `8` | `2` — effective batch size stays at 16 |
| `fp16` | `true` | `false` |
| `bf16` | `false` | `true` — A100 native, more numerically stable |
| `optimizer` | `adamw_8bit` | `adamw_torch` — no need for 8bit with 80GB VRAM |
| `dataloader_num_workers` | `0` | `4` — A100 machines typically have many CPU cores |

### Expected diff

```yaml
model:
  load_in_4bit: false
  max_seq_length: 4096
  lora_r: 64
  lora_alpha: 64
  use_rslora: true

training:
  per_device_train_batch_size: 8
  gradient_accumulation_steps: 2
  fp16: false
  bf16: true
  optimizer: "adamw_torch"
  dataloader_num_workers: 4
```

---

## 2. `filter_dataset.py`

| Parameter | Current | A100 |
|-----------|---------|------|
| `MAX_TOKENS` (line 37) | `400` | `800` — allows richer, more detailed responses |

With larger context available, the 400-token cap on response length is the main bottleneck
for training data quality. Raising it to 800 recovers incidents with longer summaries that
were previously discarded.

```python
MAX_TOKENS = 800   # was 400
```

---

## 3. `run_finetuned_inference.py`

| Parameter | Current | A100 |
|-----------|---------|------|
| `--max-input-tokens` default (line 105) | `2048` | `0` (no limit) or `6000` |

Currently, complex incidents with large DAG analyses are silently skipped during inference
because their input exceeds 2048 tokens. Pass `--max-input-tokens 0` to disable the filter,
or match your `max_seq_length`:

```bash
python3 run_finetuned_inference.py \
  --input filtered_eval.json \
  --output finetuned_eval_results.json \
  --max-input-tokens 0 \
  ...
```

---

## Impact Chain

```
filter_dataset.py  MAX_TOKENS 400 → 800
  └─ more/longer responses survive into filtered_train.json

config.yaml  max_seq_length 2048 → 4096
  └─ model attends over full DAG input + longer response during training

run_finetuned_inference.py  --max-input-tokens 0
  └─ complex incidents (large graphs) no longer skipped during eval
```

---

## Notes

- With a 1.5B model on an A100, training 3 epochs takes ~2–3 minutes — consider bumping
  `num_train_epochs` to 5 at no real cost.
- After SFT converges, the A100 has enough headroom to run a DPO stage immediately after
  (`mode: dpo` in config) without changing any other parameters.
- `save_method: merged_16bit` will produce a ~3GB merged model — fine on A100 local storage.

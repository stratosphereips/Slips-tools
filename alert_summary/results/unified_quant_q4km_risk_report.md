# LLM Risk Evaluation Summary Report

**Judge:** qwen3.5
**Total Evaluations:** 67

## Overall Performance Rankings

| Rank | Model | Avg Position | Avg Cause Score | Avg Risk Score | Win Rate | Wins |
|------|-------|--------------|-----------------|----------------|----------|------|
| 1 | GPT-4o | 1.96 | 19.91 | 15.09 | 41.8% | 28 |
| 2 | GPT-4o-mini | 2.07 | 19.03 | 14.00 | 29.9% | 20 |
| 3 | Finetuned | 2.36 | 17.75 | 13.70 | 26.9% | 18 |
| 4 | Qwen2.5 1.5B | 4.07 | 11.25 | 11.24 | 1.5% | 1 |
| 5 | Qwen2.5 3B | 4.54 | 9.66 | 12.09 | 0.0% | 0 |

## Position Distribution

| Model | 1st | 2nd | 3rd | 4th | 5th |
|-------|-----|-----|-----|-----|-----|
| GPT-4o | 28 | 21 | 12 | 5 | 1 |
| GPT-4o-mini | 20 | 24 | 21 | 2 | 0 |
| Finetuned | 18 | 18 | 22 | 7 | 2 |
| Qwen2.5 1.5B | 1 | 4 | 9 | 28 | 25 |
| Qwen2.5 3B | 0 | 0 | 3 | 25 | 39 |

## Performance by Incident Category

### Malware Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 62 | 1.92 | 20.00 | 15.03 | 25 |
| GPT-4o-mini | 62 | 2.10 | 19.02 | 13.92 | 18 |
| Finetuned | 62 | 2.29 | 18.08 | 13.79 | 18 |
| Qwen2.5 1.5B | 62 | 4.15 | 11.16 | 11.02 | 1 |
| Qwen2.5 3B | 62 | 4.55 | 9.58 | 12.03 | 0 |

### Normal Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o-mini | 5 | 1.80 | 19.20 | 15.00 | 2 |
| GPT-4o | 5 | 2.40 | 18.80 | 15.80 | 3 |
| Finetuned | 5 | 3.20 | 13.60 | 12.60 | 0 |
| Qwen2.5 1.5B | 5 | 3.20 | 12.40 | 14.00 | 0 |
| Qwen2.5 3B | 5 | 4.40 | 10.60 | 12.80 | 0 |

## Performance by Incident Complexity

### Simple Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| Finetuned | 44 | 1.98 | 19.57 | 14.02 | 17 |
| GPT-4o-mini | 44 | 2.18 | 18.75 | 13.02 | 13 |
| GPT-4o | 44 | 2.23 | 19.18 | 14.20 | 13 |
| Qwen2.5 1.5B | 44 | 3.93 | 12.09 | 12.09 | 1 |
| Qwen2.5 3B | 44 | 4.68 | 10.07 | 11.75 | 0 |

### Medium Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 8 | 1.50 | 20.50 | 17.88 | 5 |
| GPT-4o-mini | 8 | 2.12 | 19.50 | 16.00 | 2 |
| Finetuned | 8 | 2.50 | 17.25 | 14.62 | 1 |
| Qwen2.5 3B | 8 | 4.12 | 10.38 | 11.88 | 0 |
| Qwen2.5 1.5B | 8 | 4.75 | 8.88 | 8.88 | 0 |

### Complex Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 15 | 1.40 | 21.73 | 16.20 | 10 |
| GPT-4o-mini | 15 | 1.73 | 19.60 | 15.80 | 5 |
| Finetuned | 15 | 3.40 | 12.67 | 12.27 | 0 |
| Qwen2.5 1.5B | 15 | 4.13 | 10.07 | 10.00 | 0 |
| Qwen2.5 3B | 15 | 4.33 | 8.07 | 13.20 | 0 |

## Key Insights

**Best Overall Model:** GPT-4o
- Average Position: 1.96
- Average Cause Score: 19.91
- Average Risk Score: 15.09
- Win Rate: 41.8%

**Best for Malware Incidents:** GPT-4o
- Avg Position: 1.92

**Best for Normal Incidents:** GPT-4o-mini
- Avg Position: 1.80

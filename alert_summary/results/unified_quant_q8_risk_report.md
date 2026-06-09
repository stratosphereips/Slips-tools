# LLM Risk Evaluation Summary Report

**Judge:** qwen3.5
**Total Evaluations:** 67

## Overall Performance Rankings

| Rank | Model | Avg Position | Avg Cause Score | Avg Risk Score | Win Rate | Wins |
|------|-------|--------------|-----------------|----------------|----------|------|
| 1 | GPT-4o | 1.87 | 19.93 | 15.18 | 44.8% | 30 |
| 2 | GPT-4o-mini | 2.12 | 18.85 | 14.31 | 26.9% | 18 |
| 3 | Finetuned | 2.55 | 17.43 | 12.75 | 26.9% | 18 |
| 4 | Qwen2.5 1.5B | 4.19 | 11.28 | 11.64 | 1.5% | 1 |
| 5 | Qwen2.5 3B | 4.27 | 9.57 | 12.84 | 0.0% | 0 |

## Position Distribution

| Model | 1st | 2nd | 3rd | 4th | 5th |
|-------|-----|-----|-----|-----|-----|
| GPT-4o | 30 | 22 | 11 | 2 | 2 |
| GPT-4o-mini | 18 | 26 | 20 | 3 | 0 |
| Finetuned | 18 | 15 | 20 | 7 | 7 |
| Qwen2.5 1.5B | 1 | 2 | 8 | 28 | 28 |
| Qwen2.5 3B | 0 | 2 | 8 | 27 | 30 |

## Performance by Incident Category

### Malware Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 62 | 1.79 | 20.10 | 15.24 | 28 |
| GPT-4o-mini | 62 | 2.16 | 18.74 | 14.45 | 16 |
| Finetuned | 62 | 2.52 | 17.63 | 12.76 | 17 |
| Qwen2.5 1.5B | 62 | 4.24 | 11.18 | 11.52 | 1 |
| Qwen2.5 3B | 62 | 4.29 | 9.44 | 12.89 | 0 |

### Normal Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o-mini | 5 | 1.60 | 20.20 | 12.60 | 2 |
| GPT-4o | 5 | 2.80 | 17.80 | 14.40 | 2 |
| Finetuned | 5 | 3.00 | 15.00 | 12.60 | 1 |
| Qwen2.5 1.5B | 5 | 3.60 | 12.60 | 13.20 | 0 |
| Qwen2.5 3B | 5 | 4.00 | 11.20 | 12.20 | 0 |

## Performance by Incident Complexity

### Simple Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| Finetuned | 44 | 2.05 | 19.66 | 13.84 | 17 |
| GPT-4o | 44 | 2.16 | 19.09 | 14.30 | 13 |
| GPT-4o-mini | 44 | 2.25 | 18.50 | 13.34 | 13 |
| Qwen2.5 1.5B | 44 | 4.09 | 12.16 | 12.23 | 1 |
| Qwen2.5 3B | 44 | 4.45 | 9.80 | 12.41 | 0 |

### Medium Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 8 | 1.50 | 20.62 | 15.88 | 5 |
| GPT-4o-mini | 8 | 2.00 | 19.00 | 14.62 | 2 |
| Finetuned | 8 | 2.62 | 15.12 | 15.88 | 1 |
| Qwen2.5 3B | 8 | 4.12 | 10.25 | 11.88 | 0 |
| Qwen2.5 1.5B | 8 | 4.75 | 9.38 | 9.50 | 0 |

### Complex Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 15 | 1.20 | 22.00 | 17.40 | 12 |
| GPT-4o-mini | 15 | 1.80 | 19.80 | 17.00 | 3 |
| Qwen2.5 3B | 15 | 3.80 | 8.53 | 14.60 | 0 |
| Finetuned | 15 | 4.00 | 12.13 | 7.87 | 0 |
| Qwen2.5 1.5B | 15 | 4.20 | 9.73 | 11.07 | 0 |

## Key Insights

**Best Overall Model:** GPT-4o
- Average Position: 1.87
- Average Cause Score: 19.93
- Average Risk Score: 15.18
- Win Rate: 44.8%

**Best for Malware Incidents:** GPT-4o
- Avg Position: 1.79

**Best for Normal Incidents:** GPT-4o-mini
- Avg Position: 1.60

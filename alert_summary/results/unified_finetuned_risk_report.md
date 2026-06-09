# LLM Risk Evaluation Summary Report

**Judge:** qwen3.5
**Total Evaluations:** 68

## Overall Performance Rankings

| Rank | Model | Avg Position | Avg Cause Score | Avg Risk Score | Win Rate | Wins |
|------|-------|--------------|-----------------|----------------|----------|------|
| 1 | GPT-4o | 1.51 | 19.79 | 16.24 | 63.2% | 43 |
| 2 | GPT-4o-mini | 2.19 | 17.90 | 14.90 | 22.1% | 15 |
| 3 | Finetuned | 3.06 | 15.04 | 12.13 | 10.3% | 7 |
| 4 | Qwen2.5 3B | 4.07 | 10.06 | 13.12 | 2.9% | 2 |
| 5 | Qwen2.5 1.5B | 4.16 | 10.74 | 11.07 | 1.5% | 1 |

## Position Distribution

| Model | 1st | 2nd | 3rd | 4th | 5th |
|-------|-----|-----|-----|-----|-----|
| GPT-4o | 43 | 17 | 7 | 0 | 1 |
| GPT-4o-mini | 15 | 32 | 15 | 5 | 1 |
| Finetuned | 7 | 14 | 25 | 12 | 10 |
| Qwen2.5 3B | 2 | 3 | 12 | 22 | 29 |
| Qwen2.5 1.5B | 1 | 2 | 9 | 29 | 27 |

## Performance by Incident Category

### Malware Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 65 | 1.51 | 19.85 | 16.14 | 42 |
| GPT-4o-mini | 65 | 2.20 | 17.97 | 14.91 | 14 |
| Finetuned | 65 | 3.09 | 14.91 | 12.05 | 6 |
| Qwen2.5 3B | 65 | 4.03 | 10.17 | 13.26 | 2 |
| Qwen2.5 1.5B | 65 | 4.17 | 10.60 | 11.26 | 1 |

### Normal Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 3 | 1.67 | 18.67 | 18.33 | 1 |
| GPT-4o-mini | 3 | 2.00 | 16.33 | 14.67 | 1 |
| Finetuned | 3 | 2.33 | 18.00 | 14.00 | 1 |
| Qwen2.5 1.5B | 3 | 4.00 | 13.67 | 7.00 | 0 |
| Qwen2.5 3B | 3 | 5.00 | 7.67 | 10.00 | 0 |

## Performance by Incident Complexity

### Simple Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 42 | 1.62 | 19.86 | 15.21 | 24 |
| GPT-4o-mini | 42 | 2.26 | 18.19 | 14.38 | 10 |
| Finetuned | 42 | 2.83 | 17.55 | 13.07 | 5 |
| Qwen2.5 1.5B | 42 | 4.02 | 11.74 | 12.31 | 1 |
| Qwen2.5 3B | 42 | 4.26 | 10.48 | 12.93 | 2 |

### Medium Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 8 | 1.75 | 18.88 | 16.75 | 4 |
| GPT-4o-mini | 8 | 1.75 | 18.50 | 15.00 | 3 |
| Finetuned | 8 | 2.50 | 16.38 | 14.50 | 1 |
| Qwen2.5 3B | 8 | 4.38 | 9.12 | 13.00 | 0 |
| Qwen2.5 1.5B | 8 | 4.62 | 9.38 | 8.75 | 0 |

### Complex Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 18 | 1.17 | 20.06 | 18.39 | 15 |
| GPT-4o-mini | 18 | 2.22 | 16.94 | 16.06 | 2 |
| Qwen2.5 3B | 18 | 3.50 | 9.50 | 13.61 | 0 |
| Finetuned | 18 | 3.83 | 8.61 | 8.89 | 1 |
| Qwen2.5 1.5B | 18 | 4.28 | 9.00 | 9.22 | 0 |

## Key Insights

**Best Overall Model:** GPT-4o
- Average Position: 1.51
- Average Cause Score: 19.79
- Average Risk Score: 16.24
- Win Rate: 63.2%

**Best for Malware Incidents:** GPT-4o
- Avg Position: 1.51

**Best for Normal Incidents:** GPT-4o
- Avg Position: 1.67

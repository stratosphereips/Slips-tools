# LLM Risk Evaluation Summary Report

**Judge:** qwen3.5
**Total Evaluations:** 67

## Overall Performance Rankings

| Rank | Model | Avg Position | Avg Cause Score | Avg Risk Score | Win Rate | Wins |
|------|-------|--------------|-----------------|----------------|----------|------|
| 1 | GPT-4o | 1.79 | 20.15 | 15.40 | 50.7% | 34 |
| 2 | GPT-4o-mini | 2.18 | 19.07 | 13.87 | 20.9% | 14 |
| 3 | Finetuned | 2.43 | 17.30 | 13.66 | 26.9% | 18 |
| 4 | Qwen2.5 3B | 4.22 | 9.84 | 12.33 | 0.0% | 0 |
| 5 | Qwen2.5 1.5B | 4.37 | 10.90 | 10.63 | 1.5% | 1 |

## Position Distribution

| Model | 1st | 2nd | 3rd | 4th | 5th |
|-------|-----|-----|-----|-----|-----|
| GPT-4o | 34 | 17 | 13 | 2 | 1 |
| GPT-4o-mini | 14 | 29 | 22 | 2 | 0 |
| Finetuned | 18 | 18 | 20 | 6 | 5 |
| Qwen2.5 3B | 0 | 1 | 7 | 35 | 24 |
| Qwen2.5 1.5B | 1 | 2 | 5 | 22 | 37 |

## Performance by Incident Category

### Malware Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 62 | 1.74 | 20.42 | 15.35 | 32 |
| GPT-4o-mini | 62 | 2.21 | 18.97 | 13.81 | 11 |
| Finetuned | 62 | 2.35 | 17.52 | 13.69 | 18 |
| Qwen2.5 3B | 62 | 4.26 | 9.69 | 12.23 | 0 |
| Qwen2.5 1.5B | 62 | 4.44 | 10.79 | 10.44 | 1 |

### Normal Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o-mini | 5 | 1.80 | 20.40 | 14.60 | 3 |
| GPT-4o | 5 | 2.40 | 16.80 | 16.00 | 2 |
| Finetuned | 5 | 3.40 | 14.60 | 13.20 | 0 |
| Qwen2.5 1.5B | 5 | 3.60 | 12.20 | 13.00 | 0 |
| Qwen2.5 3B | 5 | 3.80 | 11.60 | 13.60 | 0 |

## Performance by Incident Complexity

### Simple Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 44 | 1.95 | 19.48 | 14.23 | 21 |
| Finetuned | 44 | 2.02 | 18.98 | 14.23 | 16 |
| GPT-4o-mini | 44 | 2.36 | 18.61 | 12.50 | 6 |
| Qwen2.5 1.5B | 44 | 4.27 | 11.70 | 11.09 | 1 |
| Qwen2.5 3B | 44 | 4.39 | 10.09 | 11.95 | 0 |

### Medium Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 8 | 1.50 | 20.25 | 17.88 | 5 |
| GPT-4o-mini | 8 | 2.25 | 19.38 | 15.25 | 1 |
| Finetuned | 8 | 2.38 | 16.75 | 15.50 | 2 |
| Qwen2.5 3B | 8 | 3.88 | 10.38 | 12.88 | 0 |
| Qwen2.5 1.5B | 8 | 5.00 | 9.12 | 9.00 | 0 |

### Complex Incidents

| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |
|-------|-------|--------------|-----------|----------|------|
| GPT-4o | 15 | 1.47 | 22.07 | 17.53 | 8 |
| GPT-4o-mini | 15 | 1.60 | 20.27 | 17.13 | 7 |
| Finetuned | 15 | 3.67 | 12.67 | 11.00 | 0 |
| Qwen2.5 3B | 15 | 3.93 | 8.80 | 13.13 | 0 |
| Qwen2.5 1.5B | 15 | 4.33 | 9.47 | 10.13 | 0 |

## Key Insights

**Best Overall Model:** GPT-4o
- Average Position: 1.79
- Average Cause Score: 20.15
- Average Risk Score: 15.40
- Win Rate: 50.7%

**Best for Malware Incidents:** GPT-4o
- Avg Position: 1.74

**Best for Normal Incidents:** GPT-4o-mini
- Avg Position: 1.80

#!/usr/bin/env python3
"""
Readability analysis for finetuned model summaries.

Compares the finetuned model against all other models present in
finetuned_eval_results.json on metrics relevant to human-readable summaries:
  - Compression ratio (summary length / DAG length)
  - Verbatim copy rate (lines reproduced verbatim from DAG)
  - Abstraction rate (bullet lines that paraphrase rather than copy)
  - Formatting issues (markdown code fences leaking into output)
  - Error rate (server errors / empty outputs)

Outputs a markdown report and prints a summary table.
"""

import json
import argparse
import os
import sys
from pathlib import Path


MODEL_LABELS = {
    'llm_gpt_4o_analysis': 'GPT-4o',
    'llm_gpt4o_mini_analysis': 'GPT-4o-mini',
    'llm_qwen2_5:3b_analysis': 'Qwen2.5 3B',
    'llm_qwen2_5_analysis': 'Qwen2.5 1B',
    'llm_finetuned_analysis': 'Finetuned',
}


def get_summary_text(val):
    """Extract the summary string from a model response (dict or plain string)."""
    if isinstance(val, dict):
        return val.get('summary', '') or ''
    return str(val) if val else ''


def strip_fences(text):
    """Remove markdown code fences if present."""
    t = text.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[-1] if '\n' in t else ''
        if t.endswith('```'):
            t = t[:-3]
    return t.strip()


def analyze(data, model_keys):
    stats = {k: {
        'errors': 0,
        'markdown_fences': 0,
        'compression_ratios': [],
        'verbatim_lines': 0,
        'abstracted_bullets': 0,
        'total_records': 0,
    } for k in model_keys}

    for record in data:
        dag = record.get('dag_analysis', '')
        dag_len = len(dag)
        dag_line_set = set(l.strip() for l in dag.split('\n') if l.strip())

        for key in model_keys:
            if key not in record:
                continue
            stats[key]['total_records'] += 1
            raw = get_summary_text(record[key])

            if not raw.strip() or 'ERROR' in raw:
                stats[key]['errors'] += 1
                continue

            has_fence = raw.strip().startswith('```')
            if has_fence:
                stats[key]['markdown_fences'] += 1

            clean = strip_fences(raw)
            ratio = len(clean) / dag_len if dag_len > 0 else 0
            stats[key]['compression_ratios'].append(ratio)

            lines = clean.split('\n')
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped in dag_line_set:
                    stats[key]['verbatim_lines'] += 1
                if stripped.startswith('•') and stripped not in dag_line_set:
                    stats[key]['abstracted_bullets'] += 1

    return stats


def format_report(stats, model_keys, n_records, finetuned_key):
    lines = []
    lines.append('# Readability Analysis Report\n')
    lines.append(
        'Metrics for human-readable summary quality. '
        'Lower compression = more concise. Higher abstraction = more paraphrasing (better). '
        'Verbatim lines and fences are negative signals.\n'
    )

    header = '| Model | Records | Errors | Fences | Avg Compress | Verbatim Lines | Abstracted Bullets |'
    sep    = '|-------|---------|--------|--------|-------------|----------------|-------------------|'
    lines.append(header)
    lines.append(sep)

    for key in model_keys:
        s = stats[key]
        label = MODEL_LABELS.get(key, key)
        marker = ' **\u2b50**' if key == finetuned_key else ''
        ratios = s['compression_ratios']
        avg_r = sum(ratios) / len(ratios) if ratios else 0.0
        lines.append(
            f'| {label}{marker} | {s["total_records"]} | {s["errors"]} | {s["markdown_fences"]} '
            f'| {avg_r:.2f} | {s["verbatim_lines"]} | {s["abstracted_bullets"]} |'
        )

    lines.append('')

    # Finetuned-specific commentary
    ft = stats.get(finetuned_key)
    if ft:
        ft_ratios = ft['compression_ratios']
        ft_avg = sum(ft_ratios) / len(ft_ratios) if ft_ratios else 0.0
        lines.append('## Finetuned Model Assessment\n')

        verdicts = []

        # Compression
        other_avgs = []
        for k, s in stats.items():
            if k == finetuned_key:
                continue
            r = s['compression_ratios']
            if r:
                other_avgs.append(sum(r) / len(r))
        if other_avgs:
            mean_other = sum(other_avgs) / len(other_avgs)
            if ft_avg < mean_other - 0.05:
                verdicts.append(f'**Compression**: GOOD — finetuned ({ft_avg:.2f}) is more concise than the average of other models ({mean_other:.2f}).')
            elif ft_avg > mean_other + 0.15:
                verdicts.append(f'**Compression**: POOR — finetuned ({ft_avg:.2f}) is more verbose than the average of other models ({mean_other:.2f}). Likely copying large portions of the DAG.')
            else:
                verdicts.append(f'**Compression**: NEUTRAL — finetuned ({ft_avg:.2f}) is comparable to other models ({mean_other:.2f}).')

        # Abstraction
        other_abs = [stats[k]['abstracted_bullets'] for k in model_keys if k != finetuned_key and stats[k]['total_records'] > 0]
        if other_abs:
            mean_abs = sum(other_abs) / len(other_abs)
            if ft['abstracted_bullets'] > mean_abs * 1.2:
                verdicts.append(f'**Abstraction**: GOOD — {ft["abstracted_bullets"]} abstracted bullets vs avg {mean_abs:.0f} for other models.')
            elif ft['abstracted_bullets'] < mean_abs * 0.5:
                verdicts.append(f'**Abstraction**: POOR — only {ft["abstracted_bullets"]} abstracted bullets vs avg {mean_abs:.0f}. Model may be echoing raw log lines.')
            else:
                verdicts.append(f'**Abstraction**: NEUTRAL — {ft["abstracted_bullets"]} abstracted bullets, close to other models ({mean_abs:.0f} avg).')

        # Verbatim
        other_verb = [stats[k]['verbatim_lines'] for k in model_keys if k != finetuned_key and stats[k]['total_records'] > 0]
        if other_verb:
            mean_verb = sum(other_verb) / len(other_verb)
            if ft['verbatim_lines'] > mean_verb * 1.5:
                verdicts.append(f'**Verbatim copy**: HIGH — {ft["verbatim_lines"]} verbatim lines vs avg {mean_verb:.0f}. Model is reproducing raw events instead of summarizing.')
            else:
                verdicts.append(f'**Verbatim copy**: OK — {ft["verbatim_lines"]} verbatim lines (avg {mean_verb:.0f}).')

        # Fences
        if ft['markdown_fences'] > 0:
            pct = ft['markdown_fences'] / ft['total_records'] * 100
            verdicts.append(f'**Formatting**: WARNING — {ft["markdown_fences"]}/{ft["total_records"]} outputs ({pct:.0f}%) contain markdown code fences. These need to be stripped before display.')
        else:
            verdicts.append('**Formatting**: CLEAN — no markdown code fences detected.')

        # Errors
        if ft['errors'] > 0:
            verdicts.append(f'**Errors**: {ft["errors"]}/{ft["total_records"]} records returned errors (likely context-length overflow on large DAGs).')

        for v in verdicts:
            lines.append(f'- {v}')

    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Readability analysis for finetuned model summaries')
    parser.add_argument('--input', '-i', default='finetuned_eval_results.json',
                        help='Path to eval results JSON (default: finetuned_eval_results.json)')
    parser.add_argument('--output', '-o', default=None,
                        help='Output markdown report path (default: print only)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'ERROR: Input file not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        data = json.load(f)

    print(f'Loaded {len(data)} records from {args.input}')

    # Detect which model keys are present
    model_keys = [k for k in MODEL_LABELS if any(k in r for r in data)]
    finetuned_key = 'llm_finetuned_analysis'

    if finetuned_key not in model_keys:
        print('WARNING: llm_finetuned_analysis not found in any record. Nothing to compare.', file=sys.stderr)
        sys.exit(1)

    dag_lens = [len(r.get('dag_analysis', '')) for r in data]
    print(f'DAG avg length: {sum(dag_lens)/len(dag_lens):.0f} chars')

    stats = analyze(data, model_keys)

    # Print summary table to stdout
    print('\n=== Readability Summary ===')
    print(f'{"Model":<22} {"Compress":>9} {"Verbatim":>9} {"Abstracted":>11} {"Fences":>7} {"Errors":>7}')
    print('-' * 70)
    for key in model_keys:
        s = stats[key]
        label = MODEL_LABELS.get(key, key)
        marker = ' *' if key == finetuned_key else ''
        ratios = s['compression_ratios']
        avg_r = sum(ratios) / len(ratios) if ratios else 0.0
        print(f'{label+marker:<22} {avg_r:>9.2f} {s["verbatim_lines"]:>9} {s["abstracted_bullets"]:>11} {s["markdown_fences"]:>7} {s["errors"]:>7}')
    print('(* = finetuned model)')

    report = format_report(stats, model_keys, len(data), finetuned_key)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            f.write(report)
        print(f'\nReport saved to {args.output}')
    else:
        print('\n' + report)


if __name__ == '__main__':
    main()

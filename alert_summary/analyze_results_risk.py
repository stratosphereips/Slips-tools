#!/usr/bin/env python3
"""
Analyze risk evaluation results from judge LLM.
Handles separate cause_scores and risk_scores per incident.
"""

import json
import csv
from collections import defaultdict, Counter
from typing import List, Dict


def load_results(filepath: str) -> List[Dict]:
    with open(filepath, 'r') as f:
        return json.load(f)


def calculate_statistics(results: List[Dict]) -> Dict:
    models = set()
    for result in results:
        models.update(result['cause_scores'].keys())
    models = sorted(list(models))

    print(f"Detected models: {models}")

    position_counts = {model: Counter() for model in models}
    cause_scores_list = {model: [] for model in models}
    risk_scores_list = {model: [] for model in models}

    category_performance = {
        'Malware': {model: {'positions': [], 'cause_scores': [], 'risk_scores': []} for model in models},
        'Normal':  {model: {'positions': [], 'cause_scores': [], 'risk_scores': []} for model in models},
    }
    complexity_performance = {
        'simple':  {model: {'positions': [], 'cause_scores': [], 'risk_scores': []} for model in models},
        'medium':  {model: {'positions': [], 'cause_scores': [], 'risk_scores': []} for model in models},
        'complex': {model: {'positions': [], 'cause_scores': [], 'risk_scores': []} for model in models},
    }

    for result in results:
        rankings = result['rankings']
        cause_scores = result['cause_scores']
        risk_scores = result['risk_scores']
        category = result['category']
        event_count = result['event_count']

        if event_count < 500:
            complexity = 'simple'
        elif event_count < 2000:
            complexity = 'medium'
        else:
            complexity = 'complex'

        for position, model in rankings.items():
            position_num = int(position)
            position_counts[model][position_num] += 1
            category_performance[category][model]['positions'].append(position_num)
            complexity_performance[complexity][model]['positions'].append(position_num)

        for model in models:
            cs = cause_scores.get(model, {}).get('total', 0)
            rs = risk_scores.get(model, {}).get('total', 0)
            cause_scores_list[model].append(cs)
            risk_scores_list[model].append(rs)
            category_performance[category][model]['cause_scores'].append(cs)
            category_performance[category][model]['risk_scores'].append(rs)
            complexity_performance[complexity][model]['cause_scores'].append(cs)
            complexity_performance[complexity][model]['risk_scores'].append(rs)

    stats = {
        'models': models,
        'total_evaluations': len(results),
        'model_stats': {},
    }

    for model in models:
        positions = []
        for pos in range(1, len(models) + 1):
            positions.extend([pos] * position_counts[model][pos])

        avg_position  = sum(positions) / len(positions) if positions else 0
        avg_cause     = sum(cause_scores_list[model]) / len(cause_scores_list[model]) if cause_scores_list[model] else 0
        avg_risk      = sum(risk_scores_list[model])  / len(risk_scores_list[model])  if risk_scores_list[model]  else 0
        win_rate      = position_counts[model][1] / len(results) * 100 if results else 0

        stats['model_stats'][model] = {
            'position_distribution': dict(position_counts[model]),
            'win_count':       position_counts[model][1],
            'win_rate':        win_rate,
            'average_position': avg_position,
            'average_cause_score': avg_cause,
            'average_risk_score':  avg_risk,
            'cause_scores': cause_scores_list[model],
            'risk_scores':  risk_scores_list[model],
        }

    def agg(perf_dict):
        out = {}
        for model in models:
            p  = perf_dict[model]['positions']
            cs = perf_dict[model]['cause_scores']
            rs = perf_dict[model]['risk_scores']
            out[model] = {
                'count':            len(p),
                'average_position': sum(p)  / len(p)  if p  else 0,
                'average_cause':    sum(cs) / len(cs) if cs else 0,
                'average_risk':     sum(rs) / len(rs) if rs else 0,
                'wins':             sum(1 for x in p if x == 1),
            }
        return out

    stats['category_stats'] = {cat: agg(category_performance[cat]) for cat in ['Malware', 'Normal']}
    stats['complexity_stats'] = {c: agg(complexity_performance[c]) for c in ['simple', 'medium', 'complex']}

    return stats


def generate_summary_report(stats: Dict, judge: str = "qwen3.5") -> str:
    report = []
    report.append("# LLM Risk Evaluation Summary Report")
    report.append("")
    report.append(f"**Judge:** {judge}")
    report.append(f"**Total Evaluations:** {stats['total_evaluations']}")
    report.append("")

    sorted_models = sorted(
        stats['models'],
        key=lambda m: stats['model_stats'][m]['average_position']
    )

    report.append("## Overall Performance Rankings")
    report.append("")
    report.append("| Rank | Model | Avg Position | Avg Cause Score | Avg Risk Score | Win Rate | Wins |")
    report.append("|------|-------|--------------|-----------------|----------------|----------|------|")

    for rank, model in enumerate(sorted_models, 1):
        ms = stats['model_stats'][model]
        report.append(
            f"| {rank} | {model} | {ms['average_position']:.2f} | "
            f"{ms['average_cause_score']:.2f} | {ms['average_risk_score']:.2f} | "
            f"{ms['win_rate']:.1f}% | {ms['win_count']} |"
        )

    report.append("")

    report.append("## Position Distribution")
    report.append("")
    ordinals = ['1st', '2nd', '3rd'] + [f'{i}th' for i in range(4, len(sorted_models) + 1)]
    report.append("| Model | " + " | ".join(ordinals) + " |")
    report.append("|-------|" + "-----|" * len(sorted_models))
    for model in sorted_models:
        dist = stats['model_stats'][model]['position_distribution']
        cols = " | ".join(str(dist.get(i, 0)) for i in range(1, len(sorted_models) + 1))
        report.append(f"| {model} | {cols} |")
    report.append("")

    report.append("## Performance by Incident Category")
    report.append("")
    for category in ['Malware', 'Normal']:
        report.append(f"### {category} Incidents")
        report.append("")
        report.append("| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |")
        report.append("|-------|-------|--------------|-----------|----------|------|")
        cat = stats['category_stats'][category]
        for model in sorted(stats['models'], key=lambda m: cat[m]['average_position'] if cat[m]['count'] > 0 else 999):
            cs = cat[model]
            if cs['count'] > 0:
                report.append(
                    f"| {model} | {cs['count']} | {cs['average_position']:.2f} | "
                    f"{cs['average_cause']:.2f} | {cs['average_risk']:.2f} | {cs['wins']} |"
                )
        report.append("")

    report.append("## Performance by Incident Complexity")
    report.append("")
    for complexity in ['simple', 'medium', 'complex']:
        report.append(f"### {complexity.capitalize()} Incidents")
        report.append("")
        report.append("| Model | Count | Avg Position | Avg Cause | Avg Risk | Wins |")
        report.append("|-------|-------|--------------|-----------|----------|------|")
        comp = stats['complexity_stats'][complexity]
        for model in sorted(stats['models'], key=lambda m: comp[m]['average_position'] if comp[m]['count'] > 0 else 999):
            cs = comp[model]
            if cs['count'] > 0:
                report.append(
                    f"| {model} | {cs['count']} | {cs['average_position']:.2f} | "
                    f"{cs['average_cause']:.2f} | {cs['average_risk']:.2f} | {cs['wins']} |"
                )
        report.append("")

    report.append("## Key Insights")
    report.append("")
    best = sorted_models[0]
    ms = stats['model_stats'][best]
    report.append(f"**Best Overall Model:** {best}")
    report.append(f"- Average Position: {ms['average_position']:.2f}")
    report.append(f"- Average Cause Score: {ms['average_cause_score']:.2f}")
    report.append(f"- Average Risk Score: {ms['average_risk_score']:.2f}")
    report.append(f"- Win Rate: {ms['win_rate']:.1f}%")
    report.append("")

    for category in ['Malware', 'Normal']:
        best_cat = min(
            stats['models'],
            key=lambda m: stats['category_stats'][category][m]['average_position']
            if stats['category_stats'][category][m]['count'] > 0 else 999
        )
        report.append(f"**Best for {category} Incidents:** {best_cat}")
        report.append(f"- Avg Position: {stats['category_stats'][category][best_cat]['average_position']:.2f}")
        report.append("")

    return "\n".join(report)


def export_to_csv(results: List[Dict], stats: Dict, output_path: str):
    models = stats['models']
    slug = lambda m: m.lower().replace(' ', '_').replace('.', '').replace('-', '_')

    n = len(models)
    rank_fields        = [f'rank_{i}' for i in range(1, n + 1)]
    cause_score_fields = [f'{slug(m)}_cause_score' for m in models]
    risk_score_fields  = [f'{slug(m)}_risk_score'  for m in models]
    position_fields    = [f'{slug(m)}_position'    for m in models]

    fieldnames = ['incident_id', 'category', 'event_count', 'threat_level'] + \
                 rank_fields + cause_score_fields + risk_score_fields + position_fields

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            rankings = result['rankings']
            cause_scores = result['cause_scores']
            risk_scores  = result['risk_scores']
            model_positions = {model: int(pos) for pos, model in rankings.items()}

            row = {
                'incident_id': result['incident_id'],
                'category':    result['category'],
                'event_count': result['event_count'],
                'threat_level': result['threat_level'],
            }
            for i in range(1, n + 1):
                row[f'rank_{i}'] = rankings.get(str(i), '')
            for m in models:
                row[f'{slug(m)}_cause_score'] = cause_scores.get(m, {}).get('total', '')
                row[f'{slug(m)}_risk_score']  = risk_scores.get(m, {}).get('total', '')
                row[f'{slug(m)}_position']    = model_positions.get(m, '')

            writer.writerow(row)

    print(f"Exported detailed data to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Analyze risk LLM evaluation results')
    parser.add_argument('--results', '-r', default='results/risk_finetuned_results.json')
    parser.add_argument('--summary', '-s', default='results/risk_finetuned_report.md')
    parser.add_argument('--csv',     '-c', default='results/risk_finetuned_data.csv')
    parser.add_argument('--judge',   '-j', default='qwen3.5')

    args = parser.parse_args()

    print(f"Input:  {args.results}")
    print(f"Output: {args.summary}")
    print(f"        {args.csv}")

    print("\nLoading evaluation results...")
    results = load_results(args.results)
    print(f"Loaded {len(results)} evaluation results")

    print("\nCalculating statistics...")
    stats = calculate_statistics(results)

    print("\nGenerating summary report...")
    report = generate_summary_report(stats, judge=args.judge)

    with open(args.summary, 'w') as f:
        f.write(report)
    print(f"Saved summary report to: {args.summary}")

    print("\n" + report)

    print("\nExporting to CSV...")
    export_to_csv(results, stats, args.csv)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Summary report: {args.summary}")
    print(f"Detailed CSV:   {args.csv}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Analyze evaluation results from judge LLM.
Generate summary statistics and reports.
"""

import json
import csv
from collections import defaultdict, Counter
from typing import List, Dict

def load_results(filepath: str) -> List[Dict]:
    """Load evaluation results from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def calculate_statistics(results: List[Dict]) -> Dict:
    """
    Calculate comprehensive statistics from evaluation results.

    Returns:
        Dictionary containing various statistics
    """
    # Auto-detect model names from results
    models = set()
    for result in results:
        models.update(result['scores'].keys())
    models = sorted(list(models))

    print(f"Detected models: {models}")

    # Initialize counters
    position_counts = {model: Counter() for model in models}
    scores_list = {model: [] for model in models}
    category_performance = {
        'Malware': {model: {'positions': [], 'scores': []} for model in models},
        'Normal': {model: {'positions': [], 'scores': []} for model in models}
    }
    complexity_performance = {
        'simple': {model: {'positions': [], 'scores': []} for model in models},
        'medium': {model: {'positions': [], 'scores': []} for model in models},
        'complex': {model: {'positions': [], 'scores': []} for model in models}
    }

    # Process each evaluation
    for result in results:
        rankings = result['rankings']
        scores = result['scores']
        category = result['category']
        event_count = result['event_count']

        # Determine complexity
        if event_count < 500:
            complexity = 'simple'
        elif event_count < 2000:
            complexity = 'medium'
        else:
            complexity = 'complex'

        # Count positions for each model
        for position, model in rankings.items():
            position_num = int(position)
            position_counts[model][position_num] += 1

            # Track by category
            category_performance[category][model]['positions'].append(position_num)

            # Track by complexity
            complexity_performance[complexity][model]['positions'].append(position_num)

        # Collect scores
        for model, score in scores.items():
            scores_list[model].append(score)
            category_performance[category][model]['scores'].append(score)
            complexity_performance[complexity][model]['scores'].append(score)

    # Calculate aggregate metrics
    stats = {
        'models': models,
        'total_evaluations': len(results),
        'model_stats': {}
    }

    for model in models:
        positions = []
        for pos in range(1, 5):
            positions.extend([pos] * position_counts[model][pos])

        avg_position = sum(positions) / len(positions) if positions else 0
        avg_score = sum(scores_list[model]) / len(scores_list[model]) if scores_list[model] else 0
        win_rate = (position_counts[model][1] / len(results) * 100) if len(results) > 0 else 0

        stats['model_stats'][model] = {
            'position_distribution': dict(position_counts[model]),
            'win_count': position_counts[model][1],
            'win_rate': win_rate,
            'average_position': avg_position,
            'average_score': avg_score,
            'scores': scores_list[model]
        }

    # Category-specific stats
    stats['category_stats'] = {}
    for category in ['Malware', 'Normal']:
        stats['category_stats'][category] = {}
        for model in models:
            positions = category_performance[category][model]['positions']
            scores = category_performance[category][model]['scores']

            if positions:
                avg_pos = sum(positions) / len(positions)
                avg_score = sum(scores) / len(scores) if scores else 0
                wins = sum(1 for p in positions if p == 1)
            else:
                avg_pos = 0
                avg_score = 0
                wins = 0

            stats['category_stats'][category][model] = {
                'count': len(positions),
                'average_position': avg_pos,
                'average_score': avg_score,
                'wins': wins
            }

    # Complexity-specific stats
    stats['complexity_stats'] = {}
    for complexity in ['simple', 'medium', 'complex']:
        stats['complexity_stats'][complexity] = {}
        for model in models:
            positions = complexity_performance[complexity][model]['positions']
            scores = complexity_performance[complexity][model]['scores']

            if positions:
                avg_pos = sum(positions) / len(positions)
                avg_score = sum(scores) / len(scores) if scores else 0
                wins = sum(1 for p in positions if p == 1)
            else:
                avg_pos = 0
                avg_score = 0
                wins = 0

            stats['complexity_stats'][complexity][model] = {
                'count': len(positions),
                'average_position': avg_pos,
                'average_score': avg_score,
                'wins': wins
            }

    return stats

def generate_summary_report(stats: Dict) -> str:
    """Generate a Markdown summary report."""
    report = []

    report.append("# LLM Evaluation Summary Report")
    report.append("")
    report.append("**Judge:** GPT-4o")
    report.append(f"**Total Evaluations:** {stats['total_evaluations']}")
    report.append("")

    # Overall Rankings
    report.append("## Overall Performance Rankings")
    report.append("")

    # Sort models by average position (lower is better)
    sorted_models = sorted(
        stats['models'],
        key=lambda m: stats['model_stats'][m]['average_position']
    )

    report.append("| Rank | Model | Avg Position | Avg Score | Win Rate | Wins |")
    report.append("|------|-------|--------------|-----------|----------|------|")

    for rank, model in enumerate(sorted_models, 1):
        mstats = stats['model_stats'][model]
        report.append(
            f"| {rank} | {model} | {mstats['average_position']:.2f} | "
            f"{mstats['average_score']:.2f}/10 | {mstats['win_rate']:.1f}% | "
            f"{mstats['win_count']} |"
        )

    report.append("")

    # Position Distribution
    report.append("## Position Distribution")
    report.append("")

    report.append("| Model | 1st | 2nd | 3rd | 4th |")
    report.append("|-------|-----|-----|-----|-----|")

    for model in sorted_models:
        dist = stats['model_stats'][model]['position_distribution']
        report.append(
            f"| {model} | {dist.get(1, 0)} | {dist.get(2, 0)} | "
            f"{dist.get(3, 0)} | {dist.get(4, 0)} |"
        )

    report.append("")

    # Category Performance
    report.append("## Performance by Incident Category")
    report.append("")

    for category in ['Malware', 'Normal']:
        report.append(f"### {category} Incidents")
        report.append("")
        report.append("| Model | Count | Avg Position | Avg Score | Wins |")
        report.append("|-------|-------|--------------|-----------|------|")

        cat_stats = stats['category_stats'][category]
        sorted_cat = sorted(
            stats['models'],
            key=lambda m: cat_stats[m]['average_position'] if cat_stats[m]['count'] > 0 else 999
        )

        for model in sorted_cat:
            cstats = cat_stats[model]
            if cstats['count'] > 0:
                report.append(
                    f"| {model} | {cstats['count']} | {cstats['average_position']:.2f} | "
                    f"{cstats['average_score']:.2f}/10 | {cstats['wins']} |"
                )

        report.append("")

    # Complexity Performance
    report.append("## Performance by Incident Complexity")
    report.append("")

    for complexity in ['simple', 'medium', 'complex']:
        report.append(f"### {complexity.capitalize()} Incidents")
        report.append("")
        report.append("| Model | Count | Avg Position | Avg Score | Wins |")
        report.append("|-------|-------|--------------|-----------|------|")

        comp_stats = stats['complexity_stats'][complexity]
        sorted_comp = sorted(
            stats['models'],
            key=lambda m: comp_stats[m]['average_position'] if comp_stats[m]['count'] > 0 else 999
        )

        for model in sorted_comp:
            cstats = comp_stats[model]
            if cstats['count'] > 0:
                report.append(
                    f"| {model} | {cstats['count']} | {cstats['average_position']:.2f} | "
                    f"{cstats['average_score']:.2f}/10 | {cstats['wins']} |"
                )

        report.append("")

    # Key Insights
    report.append("## Key Insights")
    report.append("")

    best_overall = sorted_models[0]
    best_stats = stats['model_stats'][best_overall]
    report.append(f"**Best Overall Model:** {best_overall}")
    report.append(f"- Average Position: {best_stats['average_position']:.2f}")
    report.append(f"- Average Score: {best_stats['average_score']:.2f}/10")
    report.append(f"- Win Rate: {best_stats['win_rate']:.1f}%")
    report.append("")

    # Find best for malware vs normal
    best_malware = min(
        stats['models'],
        key=lambda m: stats['category_stats']['Malware'][m]['average_position']
        if stats['category_stats']['Malware'][m]['count'] > 0 else 999
    )
    best_normal = min(
        stats['models'],
        key=lambda m: stats['category_stats']['Normal'][m]['average_position']
        if stats['category_stats']['Normal'][m]['count'] > 0 else 999
    )

    report.append(f"**Best for Malware Incidents:** {best_malware}")
    report.append(f"- Avg Position: {stats['category_stats']['Malware'][best_malware]['average_position']:.2f}")
    report.append("")

    report.append(f"**Best for Normal Incidents:** {best_normal}")
    report.append(f"- Avg Position: {stats['category_stats']['Normal'][best_normal]['average_position']:.2f}")

    return "\n".join(report)

def export_to_csv(results: List[Dict], stats: Dict, output_path: str):
    """Export detailed results to CSV for further analysis."""
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = [
            'incident_id', 'category', 'event_count', 'threat_level',
            'rank_1', 'rank_2', 'rank_3', 'rank_4',
            'gpt4o_score', 'gpt4o_mini_score', 'qwen15b_score', 'qwen_score',
            'gpt4o_position', 'gpt4o_mini_position', 'qwen15b_position', 'qwen_position'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            rankings = result['rankings']
            scores = result['scores']

            # Create position lookup (model -> position)
            model_positions = {model: int(pos) for pos, model in rankings.items()}

            row = {
                'incident_id': result['incident_id'],
                'category': result['category'],
                'event_count': result['event_count'],
                'threat_level': result['threat_level'],
                'rank_1': rankings.get('1', ''),
                'rank_2': rankings.get('2', ''),
                'rank_3': rankings.get('3', ''),
                'rank_4': rankings.get('4', ''),
                'gpt4o_score': scores.get('GPT-4o', ''),
                'gpt4o_mini_score': scores.get('GPT-4o-mini', ''),
                'qwen15b_score': scores.get('Qwen2.5 15B', ''),
                'qwen_score': scores.get('Qwen2.5', ''),
                'gpt4o_position': model_positions.get('GPT-4o', ''),
                'gpt4o_mini_position': model_positions.get('GPT-4o-mini', ''),
                'qwen15b_position': model_positions.get('Qwen2.5 15B', ''),
                'qwen_position': model_positions.get('Qwen2.5', '')
            }

            writer.writerow(row)

    print(f"Exported detailed data to: {output_path}")

def main():
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Analyze LLM evaluation results and generate reports')
    parser.add_argument('--results', '-r', default='results/evaluation_results.json',
                        help='Path to evaluation results JSON file (default: results/evaluation_results.json)')
    parser.add_argument('--summary', '-s', default='results/evaluation_summary.md',
                        help='Path to output summary Markdown file (default: results/evaluation_summary.md)')
    parser.add_argument('--csv', '-c', default='results/evaluation_data.csv',
                        help='Path to output CSV file (default: results/evaluation_data.csv)')

    args = parser.parse_args()

    # Configuration from arguments
    results_file = args.results
    summary_file = args.summary
    csv_file = args.csv

    print(f"Input:  {results_file}")
    print(f"Output: {summary_file}")
    print(f"        {csv_file}")

    # Load results
    print("\nLoading evaluation results...")
    results = load_results(results_file)
    print(f"Loaded {len(results)} evaluation results")

    # Calculate statistics
    print("\nCalculating statistics...")
    stats = calculate_statistics(results)

    # Generate summary report
    print("\nGenerating summary report...")
    report = generate_summary_report(stats)

    # Save summary report
    with open(summary_file, 'w') as f:
        f.write(report)
    print(f"Saved summary report to: {summary_file}")

    # Print to console
    print("\n" + report)

    # Export to CSV
    print("\nExporting to CSV...")
    export_to_csv(results, stats, csv_file)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"Summary report: {summary_file}")
    print(f"Detailed CSV: {csv_file}")

if __name__ == "__main__":
    main()

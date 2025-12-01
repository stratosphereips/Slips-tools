#!/usr/bin/env python3
"""
Generate interactive HTML dashboard for evaluation results.
Creates a comprehensive visualization with charts and incident browser.
"""

import json
from typing import List, Dict
from collections import Counter

def load_results(filepath: str) -> List[Dict]:
    """Load evaluation results from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def load_sample(filepath: str) -> List[Dict]:
    """Load evaluation sample data."""
    with open(filepath, 'r') as f:
        return json.load(f)

def calculate_head_to_head(results: List[Dict]) -> Dict:
    """Calculate head-to-head win rates between models."""
    # Auto-detect model names from results
    models = set()
    for result in results:
        models.update(result['scores'].keys())
    models = sorted(list(models))

    # Track pairwise comparisons
    comparisons = {m1: {m2: {'wins': 0, 'total': 0} for m2 in models if m2 != m1} for m1 in models}

    for result in results:
        rankings = result['rankings']

        # Get position for each model
        model_positions = {model: int(pos) for pos, model in rankings.items()}

        # Compare each pair
        for m1 in models:
            for m2 in models:
                if m1 != m2:
                    pos1 = model_positions.get(m1, 5)
                    pos2 = model_positions.get(m2, 5)

                    comparisons[m1][m2]['total'] += 1
                    if pos1 < pos2:  # Lower position is better
                        comparisons[m1][m2]['wins'] += 1

    # Calculate win percentages
    win_rates = {m1: {} for m1 in models}
    for m1 in models:
        for m2 in models:
            if m1 != m2:
                total = comparisons[m1][m2]['total']
                wins = comparisons[m1][m2]['wins']
                win_rates[m1][m2] = (wins / total * 100) if total > 0 else 0

    return win_rates

def generate_dashboard_html(results: List[Dict], sample_data: List[Dict]) -> str:
    """Generate complete HTML dashboard."""

    # Auto-detect model names from results
    models = set()
    for result in results:
        models.update(result['scores'].keys())
    models = sorted(list(models))

    # Define colors for charts (with defaults for unknown models)
    default_colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#ff6b6b', '#51cf66']
    colors = {}
    color_map = {
        'GPT-4o': '#667eea',
        'GPT-4o-mini': '#764ba2',
        'Qwen2.5 15B': '#f093fb',
        'Qwen2.5 3B': '#ff6b6b',
        'Qwen2.5': '#4facfe'
    }
    for i, model in enumerate(models):
        colors[model] = color_map.get(model, default_colors[i % len(default_colors)])

    # Auto-detect dataset type and create field mappings
    dataset_type = 'unknown'
    model_field_map = {}  # Maps model names to their field names in sample data
    content_fields = {}  # Maps content type to field names

    if sample_data:
        first_sample = sample_data[0]
        sample_keys = list(first_sample.keys())

        # Check for risk dataset fields
        if any('cause_risk' in k for k in sample_keys):
            dataset_type = 'risk'
            # Map model names to risk field names
            field_patterns = {
                'GPT-4o': 'cause_risk_gpt_4o',
                'GPT-4o-mini': 'cause_risk_gpt_4o_mini',
                'Qwen2.5 3B': 'cause_risk_qwen2_5:3b',
                'Qwen2.5': 'cause_risk_qwen2_5'
            }
            for model in models:
                model_field_map[model] = field_patterns.get(model, '')
            content_fields = {
                'field1': 'cause_analysis',
                'field2': 'risk_assessment',
                'label1': 'Cause Analysis',
                'label2': 'Risk Assessment'
            }
        # Check for summarization dataset fields
        elif any('llm_' in k and '_analysis' in k for k in sample_keys):
            dataset_type = 'summarization'
            # Map model names to llm field names
            field_patterns = {
                'GPT-4o': 'llm_gpt_4o_analysis',
                'GPT-4o-mini': 'llm_gpt4o_mini_analysis',
                'Qwen2.5 15B': 'llm_qwen2_5:15b_analysis',
                'Qwen2.5': 'llm_qwen2_5_analysis'
            }
            for model in models:
                model_field_map[model] = field_patterns.get(model, '')
            content_fields = {
                'field1': 'summary',
                'field2': 'behavior_analysis',
                'label1': 'Summary',
                'label2': 'Behavior Analysis'
            }

    # Calculate statistics
    position_counts = {model: Counter() for model in models}
    scores_list = {model: [] for model in models}
    category_stats = {
        'Malware': {model: {'positions': [], 'scores': []} for model in models},
        'Normal': {model: {'positions': [], 'scores': []} for model in models}
    }

    for result in results:
        rankings = result['rankings']
        scores = result['scores']
        category = result['category']

        for position, model in rankings.items():
            position_num = int(position)
            position_counts[model][position_num] += 1
            category_stats[category][model]['positions'].append(position_num)

        for model, score in scores.items():
            scores_list[model].append(score)
            category_stats[category][model]['scores'].append(score)

    # Calculate averages
    model_stats = {}
    for model in models:
        positions = []
        for pos in range(1, 5):
            positions.extend([pos] * position_counts[model][pos])

        avg_position = sum(positions) / len(positions) if positions else 0
        avg_score = sum(scores_list[model]) / len(scores_list[model]) if scores_list[model] else 0
        win_rate = (position_counts[model][1] / len(results) * 100) if len(results) > 0 else 0

        model_stats[model] = {
            'win_count': position_counts[model][1],
            'win_rate': win_rate,
            'avg_position': avg_position,
            'avg_score': avg_score,
            'positions': position_counts[model]
        }

    # Calculate head-to-head
    head_to_head = calculate_head_to_head(results)

    # Sort models by average position
    sorted_models = sorted(models, key=lambda m: model_stats[m]['avg_position'])

    # Create incident details list
    incident_details = []
    sample_lookup = {s['incident_id']: s for s in sample_data}

    for result in results:
        incident_id = result['incident_id']
        sample = sample_lookup.get(incident_id, {})

        # Get winner (rank 1)
        winner = result['rankings'].get('1', 'N/A')
        winner_score = result['scores'].get(winner, 0)

        incident_details.append({
            'id': incident_id[:8],
            'full_id': incident_id,
            'category': result['category'],
            'events': result['event_count'],
            'threat_level': result['threat_level'],
            'winner': winner,
            'winner_score': winner_score,
            'rankings': result['rankings'],
            'scores': result['scores'],
            'justification': result['justification'],
            'dag_analysis': sample.get('dag_analysis', 'N/A'),
            'summaries': {model: sample.get(model_field_map.get(model, ''), {}) for model in models},
            'content_fields': content_fields
        })

    # Set dashboard title based on dataset type
    if dataset_type == 'risk':
        dashboard_title = "LLM Evaluation Dashboard - Risk Analysis"
        dashboard_header = "🔍 LLM Evaluation Dashboard - Cybersecurity Risk Analysis"
        model_section_title = "Model Risk Analyses"
    else:
        dashboard_title = "LLM Evaluation Dashboard - Security Summaries"
        dashboard_header = "🔍 LLM Evaluation Dashboard - Network Security Summaries"
        model_section_title = "Model Summaries"

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard_title}</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

    <!-- DataTables -->
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">

    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f8f9fa;
            padding-bottom: 50px;
        }}
        .navbar {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card {{
            border: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border-radius: 8px;
        }}
        .card-header {{
            background: white;
            border-bottom: 2px solid #f0f0f0;
            font-weight: 600;
            color: #333;
        }}
        .metric-card {{
            text-align: center;
            padding: 20px;
        }}
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            color: #6c757d;
            font-size: 0.9rem;
            text-transform: uppercase;
        }}
        .rank-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.85rem;
        }}
        .rank-1 {{ background: #d4edda; color: #155724; }}
        .rank-2 {{ background: #d1ecf1; color: #0c5460; }}
        .rank-3 {{ background: #fff3cd; color: #856404; }}
        .rank-4 {{ background: #f8d7da; color: #721c24; }}
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}
        .incident-row {{
            cursor: pointer;
            transition: background 0.2s;
        }}
        .incident-row:hover {{
            background: #f8f9fa;
        }}
        .incident-details {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 10px;
        }}
        .summary-box {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }}
        .dag-box {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }}
        .heatmap-cell {{
            padding: 10px;
            text-align: center;
            font-weight: 600;
            border-radius: 4px;
        }}
        .heat-high {{ background: #28a745; color: white; }}
        .heat-medium {{ background: #ffc107; color: #333; }}
        .heat-low {{ background: #dc3545; color: white; }}
        .theme-toggle {{
            cursor: pointer;
            padding: 8px 16px;
            border-radius: 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            transition: background 0.3s;
        }}
        .theme-toggle:hover {{
            background: rgba(255,255,255,0.3);
        }}
        @media print {{
            .no-print {{ display: none; }}
            .card {{ box-shadow: none; border: 1px solid #ddd; }}
        }}
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-dark mb-4">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">
                {dashboard_header}
            </span>
            <div>
                <span class="text-white me-3">
                    <strong>{len(results)}</strong> Incidents | Judge: <strong>GPT-4o</strong>
                </span>
                <button class="theme-toggle no-print" onclick="toggleTheme()">🌓 Toggle Theme</button>
            </div>
        </div>
    </nav>

    <div class="container-fluid">
        <!-- Summary Metrics -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{len(results)}</div>
                    <div class="metric-label">Total Incidents</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{sorted_models[0]}</div>
                    <div class="metric-label">Top Performer</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{model_stats[sorted_models[0]]['win_rate']:.1f}%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="metric-value">{model_stats[sorted_models[0]]['avg_score']:.1f}/10</div>
                    <div class="metric-label">Top Score</div>
                </div>
            </div>
        </div>

        <!-- Overall Rankings -->
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        📊 Overall Model Rankings
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="winRateChart"></canvas>
                        </div>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Model</th>
                                    <th>Avg Position</th>
                                    <th>Avg Score</th>
                                    <th>Wins</th>
                                </tr>
                            </thead>
                            <tbody>
"""

    for rank, model in enumerate(sorted_models, 1):
        stats = model_stats[model]
        html += f"""                                <tr>
                                    <td><span class="rank-badge rank-{rank}">{rank}</span></td>
                                    <td><strong>{model}</strong></td>
                                    <td>{stats['avg_position']:.2f}</td>
                                    <td>{stats['avg_score']:.2f}</td>
                                    <td>{stats['win_count']} ({stats['win_rate']:.1f}%)</td>
                                </tr>
"""

    html += """                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        📈 Position Distribution
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="positionChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Category Performance -->
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        🎯 Performance by Incident Category
                    </div>
                    <div class="card-body">
                        <div class="chart-container" style="height: 350px;">
                            <canvas id="categoryChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Head-to-Head -->
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        ⚔️ Head-to-Head Win Rates
                        <small class="text-muted">(Row beats Column)</small>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-bordered text-center">
                                <thead>
                                    <tr>
                                        <th></th>
"""

    for model in models:
        html += f"                                        <th>{model.replace('Qwen2.5', 'Q2.5').replace(' 15B', '15B')}</th>\n"

    html += """                                    </tr>
                                </thead>
                                <tbody>
"""

    for m1 in models:
        html += f"                                    <tr>\n                                        <th>{m1.replace('Qwen2.5', 'Q2.5').replace(' 15B', '15B')}</th>\n"
        for m2 in models:
            if m1 == m2:
                html += "                                        <td>-</td>\n"
            else:
                rate = head_to_head[m1][m2]
                heat_class = 'heat-high' if rate >= 60 else ('heat-medium' if rate >= 40 else 'heat-low')
                html += f"                                        <td class='heatmap-cell {heat_class}'>{rate:.0f}%</td>\n"
        html += "                                    </tr>\n"

    html += """                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Incident Browser -->
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        🔎 Incident Browser
                        <span class="badge bg-secondary float-end">Click row to expand details</span>
                    </div>
                    <div class="card-body">
                        <table id="incidentTable" class="table table-striped table-hover" style="width:100%">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Category</th>
                                    <th>Events</th>
                                    <th>Threat</th>
                                    <th>Winner</th>
                                    <th>Score</th>
                                    <th>Positions</th>
                                </tr>
                            </thead>
                            <tbody>
"""

    for incident in incident_details:
        rankings_str = ' → '.join([f"{pos}:{model[:4]}" for pos, model in sorted(incident['rankings'].items())])
        html += f"""                                <tr class="incident-row" onclick="toggleDetails('{incident['full_id']}')">
                                    <td><code>{incident['id']}</code></td>
                                    <td><span class="badge bg-{'danger' if incident['category'] == 'Malware' else 'success'}">{incident['category']}</span></td>
                                    <td>{incident['events']}</td>
                                    <td>{incident['threat_level']:.2f}</td>
                                    <td><strong>{incident['winner']}</strong></td>
                                    <td>{incident['winner_score']:.1f}/10</td>
                                    <td><small>{rankings_str}</small></td>
                                </tr>
                                <tr id="details-{incident['full_id']}" style="display:none;">
                                    <td colspan="7">
                                        <div class="incident-details">
                                            <h6>📋 Judge Evaluation</h6>
                                            <p><strong>Justification:</strong> {incident['justification']}</p>

                                            <h6 class="mt-3">📊 Scores & Rankings</h6>
                                            <div class="row">
"""

        for pos in ['1', '2', '3', '4']:
            model = incident['rankings'].get(pos, 'N/A')
            score = incident['scores'].get(model, 0)
            html += f"""                                                <div class="col-md-3">
                                                    <div class="summary-box">
                                                        <span class="rank-badge rank-{pos}">#{pos}</span>
                                                        <strong>{model}</strong>
                                                        <div class="text-muted">Score: {score}/10</div>
                                                    </div>
                                                </div>
"""

        html += """                                            </div>

                                            <h6 class="mt-3">🔍 DAG Analysis (Raw Evidence)</h6>
                                            <div class="dag-box">"""

        # Truncate DAG for display (first 2000 chars)
        dag_text = incident['dag_analysis'][:2000]
        if len(incident['dag_analysis']) > 2000:
            dag_text += "\n\n... [truncated for display] ..."

        html += dag_text.replace('<', '&lt;').replace('>', '&gt;')

        html += f"""</div>

                                            <h6 class="mt-3">📝 {model_section_title}</h6>
"""

        # Add summaries for each model (with dynamic field detection)
        fields = incident.get('content_fields', {})
        field1_name = fields.get('field1', 'summary')
        field2_name = fields.get('field2', 'behavior_analysis')
        label1 = fields.get('label1', 'Summary')
        label2 = fields.get('label2', 'Behavior')

        for model in models:
            summary_data = incident['summaries'].get(model, {})
            if isinstance(summary_data, dict):
                text1 = summary_data.get(field1_name, 'N/A')
                text2 = summary_data.get(field2_name, 'N/A')
            else:
                text1 = 'N/A'
                text2 = 'N/A'

            # Truncate and add ellipsis
            text1_display = text1[:500] + ('...' if len(text1) > 500 else '') if text1 != 'N/A' else 'N/A'
            text2_display = text2[:500] + ('...' if len(text2) > 500 else '') if text2 != 'N/A' else 'N/A'

            html += f"""                                            <div class="summary-box">
                                                <strong>{model}</strong>
                                                <div class="mt-2"><em>{label1}:</em> {text1_display}</div>
                                                <div class="mt-2"><em>{label2}:</em> {text2_display}</div>
                                            </div>
"""

        html += """                                        </div>
                                    </td>
                                </tr>
"""

    html += """                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>

    <script>
        // Data
        const modelStats = """ + json.dumps(model_stats) + """;
        const categoryStats = """ + json.dumps(category_stats) + """;

        // Chart colors
        const colors = {
            'GPT-4o': '#667eea',
            'GPT-4o-mini': '#764ba2',
            'Qwen2.5 15B': '#f093fb',
            'Qwen2.5': '#4facfe'
        };

        // Win Rate Chart
        new Chart(document.getElementById('winRateChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(sorted_models) + """,
                datasets: [{
                    label: 'Win Rate (%)',
                    data: """ + json.dumps([model_stats[m]['win_rate'] for m in sorted_models]) + """,
                    backgroundColor: """ + json.dumps([colors.get(m, '#ccc') for m in sorted_models]) + """
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: 'Win Rate (% Ranked #1)' }
                },
                scales: {
                    y: { beginAtZero: true, max: 100 }
                }
            }
        });

        // Position Distribution Chart
        new Chart(document.getElementById('positionChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(sorted_models) + """,
                datasets: [
                    {
                        label: '1st Place',
                        data: """ + json.dumps([model_stats[m]['positions'].get(1, 0) for m in sorted_models]) + """,
                        backgroundColor: '#28a745'
                    },
                    {
                        label: '2nd Place',
                        data: """ + json.dumps([model_stats[m]['positions'].get(2, 0) for m in sorted_models]) + """,
                        backgroundColor: '#17a2b8'
                    },
                    {
                        label: '3rd Place',
                        data: """ + json.dumps([model_stats[m]['positions'].get(3, 0) for m in sorted_models]) + """,
                        backgroundColor: '#ffc107'
                    },
                    {
                        label: '4th Place',
                        data: """ + json.dumps([model_stats[m]['positions'].get(4, 0) for m in sorted_models]) + """,
                        backgroundColor: '#dc3545'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Position Distribution' }
                },
                scales: {
                    x: { stacked: true },
                    y: { stacked: true }
                }
            }
        });

        // Category Performance Chart
        const categoryData = {
            'Malware': """ + json.dumps({m: len(category_stats['Malware'][m]['positions']) for m in models}) + """,
            'Normal': """ + json.dumps({m: len(category_stats['Normal'][m]['positions']) for m in models}) + """
        };

        const categoryWins = {
            'Malware': """ + json.dumps({m: sum(1 for p in category_stats['Malware'][m]['positions'] if p == 1) for m in models}) + """,
            'Normal': """ + json.dumps({m: sum(1 for p in category_stats['Normal'][m]['positions'] if p == 1) for m in models}) + """
        };

        new Chart(document.getElementById('categoryChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(models) + """,
                datasets: [
                    {
                        label: 'Malware Wins',
                        data: Object.values(categoryWins['Malware']),
                        backgroundColor: '#dc3545'
                    },
                    {
                        label: 'Normal Wins',
                        data: Object.values(categoryWins['Normal']),
                        backgroundColor: '#28a745'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Wins by Category' }
                }
            }
        });

        // DataTable
        $(document).ready(function() {
            $('#incidentTable').DataTable({
                pageLength: 25,
                order: [[2, 'desc']],
                language: {
                    search: "Search incidents:"
                }
            });
        });

        // Toggle incident details
        function toggleDetails(id) {
            const row = document.getElementById('details-' + id);
            if (row.style.display === 'none') {
                row.style.display = 'table-row';
            } else {
                row.style.display = 'none';
            }
        }

        // Theme toggle
        let darkMode = false;
        function toggleTheme() {
            darkMode = !darkMode;
            if (darkMode) {
                document.body.style.background = '#1a1a1a';
                document.body.style.color = '#f0f0f0';
                document.querySelectorAll('.card').forEach(card => {
                    card.style.background = '#2d2d2d';
                    card.style.color = '#f0f0f0';
                });
            } else {
                document.body.style.background = '#f8f9fa';
                document.body.style.color = '#333';
                document.querySelectorAll('.card').forEach(card => {
                    card.style.background = 'white';
                    card.style.color = '#333';
                });
            }
        }
    </script>
</body>
</html>
"""

    return html

def main():
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Generate interactive HTML dashboard for evaluation results')
    parser.add_argument('--results', '-r', default='results/summary_results.json',
                        help='Path to evaluation results JSON file (default: results/summary_results.json)')
    parser.add_argument('--sample', '-s', default='datasets/summary_sample.json',
                        help='Path to evaluation sample JSON file (default: datasets/summary_sample.json)')
    parser.add_argument('--output', '-o', default='results/summary_dashboard.html',
                        help='Path to output HTML file (default: results/summary_dashboard.html)')

    args = parser.parse_args()

    # Configuration from arguments
    results_file = args.results
    sample_file = args.sample
    output_file = args.output

    print("="*60)
    print("Generating Interactive HTML Dashboard")
    print("="*60)
    print(f"\nInput files:")
    print(f"  Results: {results_file}")
    print(f"  Sample:  {sample_file}")
    print(f"  Output:  {output_file}")

    # Load data
    print("\nLoading evaluation results...")
    results = load_results(results_file)
    print(f"  Loaded {len(results)} evaluation results")

    print("\nLoading sample data...")
    sample_data = load_sample(sample_file)
    print(f"  Loaded {len(sample_data)} incidents")

    # Generate HTML
    print("\nGenerating HTML dashboard...")
    html = generate_dashboard_html(results, sample_data)

    # Save
    print(f"\nSaving dashboard to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print("\n" + "="*60)
    print("DASHBOARD GENERATED SUCCESSFULLY")
    print("="*60)
    print(f"\nOpen in browser: {output_file}")
    print("\nFeatures:")
    print("  ✓ Interactive charts (Chart.js)")
    print("  ✓ Searchable incident table (DataTables)")
    print("  ✓ Expandable incident details")
    print("  ✓ Head-to-head comparison matrix")
    print("  ✓ Category performance breakdown")
    print("  ✓ Dark/Light theme toggle")
    print("  ✓ Print-friendly layout")
    print("\nTip: Click on any incident row to see full details!")

if __name__ == "__main__":
    main()

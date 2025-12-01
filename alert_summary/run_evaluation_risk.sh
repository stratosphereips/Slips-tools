#!/bin/bash
# Run complete LLM-as-Judge evaluation workflow for Risk Analysis
# Evaluates cause & risk assessment outputs from different LLMs

set -e  # Exit on error

echo "================================================================"
echo "LLM-as-Judge Evaluation Framework - Risk Analysis"
echo "Cybersecurity Risk Analyst Perspective"
echo "================================================================"

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not set"
    echo "Please export OPENAI_API_KEY or add to .env file"
    exit 1
fi

# Check if conda environment should be activated
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "Using conda environment: $CONDA_DEFAULT_ENV"
else
    echo "Note: No conda environment active"
fi

echo ""

# Step 1: Create evaluation sample
echo "Step 1/3: Creating risk evaluation sample..."
echo "----------------------------------------------------------------"
python3 datasets/create_risk_sample.py

if [ ! -f "datasets/risk_sample.json" ]; then
    echo "ERROR: Failed to create risk evaluation sample"
    exit 1
fi

echo ""
echo "Press Enter to continue with evaluation (this will cost ~$5)..."
echo "Or Ctrl+C to cancel"
read

# Step 2: Run evaluation
echo ""
echo "Step 2/3: Running GPT-4o judge evaluation (risk analyst)..."
echo "----------------------------------------------------------------"
python3 evaluate_risk.py

if [ ! -f "results/risk_results.json" ]; then
    echo "ERROR: Evaluation failed to produce results"
    exit 1
fi

# Step 3: Analyze results
echo ""
echo "Step 3/4: Analyzing results..."
echo "----------------------------------------------------------------"
python3 analyze_results.py --results results/risk_results.json --summary results/risk_summary.md --csv results/risk_data.csv

# Step 4: Generate dashboard (optional)
echo ""
echo "Step 4/4: Generate interactive HTML dashboard? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Generating dashboard..."
    python3 generate_dashboard.py --results results/risk_results.json --sample datasets/risk_sample.json --output results/risk_dashboard.html
    DASHBOARD_GENERATED=true
else
    echo "Skipping dashboard generation"
    DASHBOARD_GENERATED=false
fi

# Display results
echo ""
echo "================================================================"
echo "WORKFLOW COMPLETE"
echo "================================================================"
echo ""
echo "Generated files:"
echo "  - datasets/risk_sample.json             (50 sampled incidents)"
echo "  - results/risk_results.json             (judge rankings)"
echo "  - results/risk_summary.md               (summary report)"
echo "  - results/risk_data.csv                 (detailed data)"
if [ "$DASHBOARD_GENERATED" = true ]; then
    echo "  - results/risk_dashboard.html           (interactive dashboard)"
    echo ""
    echo "🌐 Open dashboard in browser:"
    echo "  firefox results/risk_dashboard.html"
    echo "  # or"
    echo "  google-chrome results/risk_dashboard.html"
fi
echo ""
echo "View summary report:"
echo "  cat results/risk_summary.md"
echo ""

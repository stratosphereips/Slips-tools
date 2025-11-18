#!/bin/bash

# Generate Cause & Risk Analysis Script
# Wrapper for alert_cause_risk_analyzer.py to generate Cause and Risk analysis from JSONL files

set -euo pipefail

# Default configuration
DEFAULT_MODEL="gpt-4o-mini"
DEFAULT_BASE_URL="https://api.openai.com/v1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage information
usage() {
    cat << EOF
Usage: $0 <input.jsonl> [options]

Generate Cause & Risk analysis from JSONL alert file using LLM.

Arguments:
    input.jsonl         Input JSONL file (from sample_dataset.py)

Options:
    --output FILE              Output file (default: {input_base}.cause_risk.{model}.json)
    --model MODEL              LLM model to use (default: gpt-4o-mini)
    --base-url URL             LLM API base URL (default: https://api.openai.com/v1)
    --incident-id UUID         Analyze specific incident by ID
    --group-events             Group similar events to reduce token count (recommended for large incidents)
    --verbose                  Verbose output
    --help                     Show this help message

Output Files:
    {input_base}.cause_risk.{model}.json   Cause & Risk analysis output in JSON format (unless --output specified)

Examples:
    # Generate Cause & Risk analysis with default model (gpt-4o-mini)
    $0 my_dataset.jsonl

    # Use Qwen model via Ollama
    $0 my_dataset.jsonl --model qwen2.5:3b --base-url http://10.147.20.102:11434/v1

    # Use grouped events to reduce token usage
    $0 my_dataset.jsonl --model gpt-4o-mini --group-events

    # Analyze specific incident with verbose output
    $0 my_dataset.jsonl --incident-id 96b2b890-8e6d-458a-9217-71cfff0ef1c5 --verbose

    # Compare multiple models on same dataset
    $0 dataset.jsonl --model gpt-4o-mini
    $0 dataset.jsonl --model qwen2.5:3b --base-url http://10.147.20.102:11434/v1
    $0 dataset.jsonl --model qwen2.5:15b --base-url http://10.147.20.102:11434/v1
EOF
}

# Print colored status messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Extract simple model name for filename
get_model_name() {
    local model="$1"
    # Extract just the model name (e.g., "qwen2.5:3b" -> "qwen2.5", "gpt-4o-mini" -> "gpt-4o-mini")
    local model_name=$(echo "$model" | sed 's/:.*$//' | sed 's/\//_/g')
    echo "$model_name"
}

# Main execution function
main() {
    local input_file=""
    local output_file=""
    local model="$DEFAULT_MODEL"
    local base_url="$DEFAULT_BASE_URL"
    local incident_id=""
    local group_events=false
    local verbose=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --output)
                output_file="$2"
                shift 2
                ;;
            --model)
                model="$2"
                shift 2
                ;;
            --base-url)
                base_url="$2"
                shift 2
                ;;
            --incident-id)
                incident_id="$2"
                shift 2
                ;;
            --group-events)
                group_events=true
                shift
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                if [[ -z "$input_file" ]]; then
                    input_file="$1"
                else
                    log_error "Too many positional arguments"
                    usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$input_file" ]]; then
        log_error "Input file is required"
        usage
        exit 1
    fi

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        exit 1
    fi

    # Auto-generate output filename if not specified
    if [[ -z "$output_file" ]]; then
        local base_name="${input_file%.jsonl}"
        local model_name=$(get_model_name "$model")
        output_file="${base_name}.cause_risk.${model_name}.json"
    fi

    # Check if alert_cause_risk_analyzer.py exists
    if [[ ! -f "$SCRIPT_DIR/alert_cause_risk_analyzer.py" ]]; then
        log_error "alert_cause_risk_analyzer.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed"
        exit 1
    fi

    log_info "Generating Cause & Risk analysis..."
    log_info "Input: $input_file"
    log_info "Model: $model"
    log_info "Base URL: $base_url"
    log_info "Output: $output_file"
    [[ -n "$incident_id" ]] && log_info "Incident ID filter: $incident_id"

    # Build command
    local cmd="python3 $SCRIPT_DIR/alert_cause_risk_analyzer.py"
    cmd+=" $input_file"
    cmd+=" --output $output_file"
    cmd+=" --model $model"
    cmd+=" --base-url $base_url"

    [[ -n "$incident_id" ]] && cmd+=" --incident-id $incident_id"
    [[ "$group_events" == true ]] && cmd+=" --group-events"
    [[ "$verbose" == true ]] && cmd+=" --verbose"

    # Execute
    if ! eval "$cmd" 2>&1; then
        log_error "Failed to generate Cause & Risk analysis"
        exit 1
    fi

    if [[ ! -f "$output_file" ]]; then
        log_error "Output file not created: $output_file"
        exit 1
    fi

    log_success "Cause & Risk analysis generated: $output_file"

    # Show file size
    local file_size=$(ls -lh "$output_file" | awk '{print $5}')
    log_info "File size: $file_size"
}

# Run main function with all arguments
main "$@"

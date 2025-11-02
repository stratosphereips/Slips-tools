#!/bin/bash

# Generate DAG Analysis Script
# Wrapper for alert_dag_parser.py to generate DAG analysis from JSONL files

set -euo pipefail

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

Generate DAG analysis from JSONL alert file.

Arguments:
    input.jsonl         Input JSONL file (from sample_dataset.py)

Options:
    --output FILE              Output file (default: {input_base}.dag.txt)
    --incident-id UUID         Analyze specific incident by ID
    --verbose                  Verbose output
    --help                     Show this help message

Output Files:
    {input_base}.dag.json     DAG analysis output in JSON format (unless --output specified)

Examples:
    # Generate DAG analysis (auto-naming)
    $0 my_dataset.jsonl

    # Custom output file
    $0 my_dataset.jsonl --output custom_analysis.txt

    # Analyze specific incident
    $0 my_dataset.jsonl --incident-id 96b2b890-8e6d-458a-9217-71cfff0ef1c5

    # Verbose mode
    $0 my_dataset.jsonl --verbose
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

# Main execution function
main() {
    local input_file=""
    local output_file=""
    local incident_id=""
    local verbose=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --output)
                output_file="$2"
                shift 2
                ;;
            --incident-id)
                incident_id="$2"
                shift 2
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
        output_file="${base_name}.dag.json"
    fi

    # Check if alert_dag_parser.py exists
    if [[ ! -f "$SCRIPT_DIR/alert_dag_parser.py" ]]; then
        log_error "alert_dag_parser.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed"
        exit 1
    fi

    log_info "Generating DAG analysis..."
    log_info "Input: $input_file"
    log_info "Output: $output_file"
    [[ -n "$incident_id" ]] && log_info "Incident ID filter: $incident_id"

    # Build command
    local cmd="python3 $SCRIPT_DIR/alert_dag_parser.py"
    cmd+=" $input_file"
    cmd+=" --output $output_file"

    [[ -n "$incident_id" ]] && cmd+=" --incident-id $incident_id"
    [[ "$verbose" == true ]] && cmd+=" --verbose"

    # Execute
    if ! eval "$cmd" 2>&1; then
        log_error "Failed to generate DAG analysis"
        exit 1
    fi

    if [[ ! -f "$output_file" ]]; then
        log_error "Output file not created: $output_file"
        exit 1
    fi

    log_success "DAG analysis generated: $output_file"

    # Show file size
    local file_size=$(ls -lh "$output_file" | awk '{print $5}')
    log_info "File size: $file_size"
}

# Run main function with all arguments
main "$@"

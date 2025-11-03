#!/bin/bash

# Sample Dataset Script
# Wrapper for sample_dataset.py to sample incidents from Slips dataset

set -euo pipefail

# Default configuration
DEFAULT_BASE_DIR="./sample_logs/alya_datasets"
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
Usage: $0 <num_incidents> <output_name> [options]

Sample incidents from Slips dataset for analysis.

Arguments:
    num_incidents       Number of incidents to sample
    output_name         Output file name (will create {output_name}.jsonl)

Options:
    --category CATEGORY        Filter by category (normal or malware)
    --severity SEVERITY        Filter by severity (low, medium, or high)
    --base-dir DIR             Base directory for dataset (default: ./sample_logs/alya_datasets)
    --seed N                   Random seed for reproducibility
    --include-stats            Generate statistics file
    --help                     Show this help message

Output Files:
    {output_name}.jsonl        Sampled incidents and events (JSONL format)
    {output_name}.stats.json   Statistics (if --include-stats specified)

Examples:
    # Sample 10 random incidents
    $0 10 my_sample

    # Sample malware incidents with reproducible seed
    $0 20 malware_dataset --category malware --seed 42

    # Sample high-severity incidents with statistics
    $0 15 high_severity --severity high --include-stats
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
    local num_incidents=""
    local output_name=""
    local category=""
    local severity=""
    local base_dir="$DEFAULT_BASE_DIR"
    local seed=""
    local include_stats=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --category)
                category="$2"
                shift 2
                ;;
            --severity)
                severity="$2"
                shift 2
                ;;
            --base-dir)
                base_dir="$2"
                shift 2
                ;;
            --seed)
                seed="$2"
                shift 2
                ;;
            --include-stats)
                include_stats=true
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
                if [[ -z "$num_incidents" ]]; then
                    num_incidents="$1"
                elif [[ -z "$output_name" ]]; then
                    output_name="$1"
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
    if [[ -z "$num_incidents" ]]; then
        log_error "Number of incidents is required"
        usage
        exit 1
    fi

    if [[ -z "$output_name" ]]; then
        log_error "Output name is required"
        usage
        exit 1
    fi

    # Validate num_incidents is a number
    if ! [[ "$num_incidents" =~ ^[0-9]+$ ]]; then
        log_error "Number of incidents must be a positive integer"
        exit 1
    fi

    # Check if sample_dataset.py exists
    if [[ ! -f "$SCRIPT_DIR/sample_dataset.py" ]]; then
        log_error "sample_dataset.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed"
        exit 1
    fi

    log_info "Sampling dataset..."
    log_info "Number of incidents: $num_incidents"
    log_info "Output: ${output_name}.jsonl"
    [[ -n "$category" ]] && log_info "Category filter: $category"
    [[ -n "$severity" ]] && log_info "Severity filter: $severity"
    [[ -n "$seed" ]] && log_info "Random seed: $seed"

    # Build command
    local cmd="python3 $SCRIPT_DIR/sample_dataset.py"
    cmd+=" --num-incidents $num_incidents"
    cmd+=" --output ${output_name}.jsonl"
    cmd+=" --base-dir $base_dir"

    [[ -n "$category" ]] && cmd+=" --category $category"
    [[ -n "$severity" ]] && cmd+=" --severity $severity"
    [[ -n "$seed" ]] && cmd+=" --seed $seed"
    [[ "$include_stats" == true ]] && cmd+=" --include-stats"

    # Execute
    if ! eval "$cmd" 2>&1; then
        log_error "Failed to sample dataset"
        exit 1
    fi

    if [[ ! -f "${output_name}.jsonl" ]]; then
        log_error "Output file not created: ${output_name}.jsonl"
        exit 1
    fi

    log_success "Dataset sampled: ${output_name}.jsonl"

    # Show file size
    local file_size=$(ls -lh "${output_name}.jsonl" | awk '{print $5}')
    log_info "File size: $file_size"

    if [[ -f "${output_name}.stats.json" ]]; then
        log_success "Statistics generated: ${output_name}.stats.json"
    fi
}

# Run main function with all arguments
main "$@"

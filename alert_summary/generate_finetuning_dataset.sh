#!/bin/bash

# Finetuning Dataset Generator
# Creates a complete dataset by sampling alerts and analyzing them with both parsers

set -euo pipefail

# Default configuration
DEFAULT_MODEL="gpt-4o-mini"
DEFAULT_BASE_URL="https://api.openai.com/v1"
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
Usage: $0 <num_incidents> <output_base> [options]

Generate a finetuning dataset by sampling alerts and analyzing with both parsers.

Arguments:
    num_incidents       Number of incidents to sample
    output_base         Base name for output files (without extension)

Options:
    --category CATEGORY        Filter by category (normal or malware)
    --severity SEVERITY        Filter by severity (low, medium, or high)
    --model MODEL              LLM model to use (default: gpt-4o-mini)
    --base-url URL             LLM API base URL (default: https://api.openai.com/v1)
    --base-dir DIR             Base directory for dataset (default: ./sample_logs/alya_datasets)
    --seed N                   Random seed for reproducibility
    --include-stats            Generate statistics file
    --skip-sample              Skip sampling step (use existing .jsonl file)
    --skip-dag                 Skip DAG generation step (use existing .dag.txt file)
    --model-suffix SUFFIX      Suffix for LLM output file (default: auto from model name)
    --verbose                  Verbose output
    --help                     Show this help message

Output Files:
    {output_base}.jsonl                 Sampled incidents and events (JSONL format)
    {output_base}.dag.txt               DAG analysis output
    {output_base}.llm.{model}.txt       LLM-enhanced analysis output
    {output_base}.stats.json            Statistics (if --include-stats specified)

Examples:
    # Sample 10 incidents and analyze
    $0 10 dataset_sample

    # Sample malware incidents only with reproducible seed
    $0 20 malware_dataset --category malware --seed 42

    # Sample high-severity incidents with verbose output
    $0 15 high_severity --severity high --verbose --include-stats

    # Use custom model
    $0 10 dataset --model qwen2.5:3b --base-url http://10.147.20.102:11434/v1

    # Reuse existing sample for different LLM models
    $0 10 dataset --model gpt-4o-mini --seed 42
    $0 10 dataset --skip-sample --skip-dag --model qwen2.5:3b --base-url http://10.147.20.102:11434/v1
    $0 10 dataset --skip-sample --skip-dag --model llama3 --base-url http://10.147.20.102:11434/v1
EOF
}

# Print colored status messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Validate requirements
check_requirements() {
    # Check if sample_dataset.py exists
    if [[ ! -f "$SCRIPT_DIR/sample_dataset.py" ]]; then
        log_error "sample_dataset.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check if alert_dag_parser.py exists
    if [[ ! -f "$SCRIPT_DIR/alert_dag_parser.py" ]]; then
        log_error "alert_dag_parser.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check if alert_dag_parser_llm.py exists
    if [[ ! -f "$SCRIPT_DIR/alert_dag_parser_llm.py" ]]; then
        log_error "alert_dag_parser_llm.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed"
        exit 1
    fi
}

# Handle interruption gracefully
handle_interrupt() {
    log_warning ""
    log_warning "Interrupted by user. Cleaning up..."

    # Show which files were created
    if [[ -f "${output_base}.jsonl" ]]; then
        log_info "Partial dataset saved: ${output_base}.jsonl"
    fi
    if [[ -f "${output_base}.dag.txt" ]]; then
        log_info "Partial DAG analysis saved: ${output_base}.dag.txt"
    fi
    if [[ -f "${output_base}.llm.txt" ]]; then
        log_info "Partial LLM analysis saved: ${output_base}.llm.txt"
    fi

    exit 130
}

# Main execution function
main() {
    local num_incidents=""
    local output_base=""
    local category=""
    local severity=""
    local model="$DEFAULT_MODEL"
    local base_url="$DEFAULT_BASE_URL"
    local base_dir="$DEFAULT_BASE_DIR"
    local seed=""
    local include_stats=false
    local verbose=false
    local skip_sample=false
    local skip_dag=false
    local model_suffix=""

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
            --model)
                model="$2"
                shift 2
                ;;
            --base-url)
                base_url="$2"
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
            --skip-sample)
                skip_sample=true
                shift
                ;;
            --skip-dag)
                skip_dag=true
                shift
                ;;
            --model-suffix)
                model_suffix="$2"
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
                if [[ -z "$num_incidents" ]]; then
                    num_incidents="$1"
                elif [[ -z "$output_base" ]]; then
                    output_base="$1"
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
    if [[ -z "$output_base" ]]; then
        log_error "Output base name is required"
        usage
        exit 1
    fi

    # If not skipping sample, validate num_incidents
    if [[ "$skip_sample" == false ]]; then
        if [[ -z "$num_incidents" ]]; then
            log_error "Number of incidents is required (or use --skip-sample)"
            usage
            exit 1
        fi

        if ! [[ "$num_incidents" =~ ^[0-9]+$ ]]; then
            log_error "Number of incidents must be a positive integer"
            exit 1
        fi
    fi

    # If skipping sample, check that JSONL exists
    if [[ "$skip_sample" == true ]]; then
        if [[ ! -f "${output_base}.jsonl" ]]; then
            log_error "Cannot skip sampling: ${output_base}.jsonl not found"
            exit 1
        fi
    fi

    # If skipping DAG, check that DAG file exists
    if [[ "$skip_dag" == true ]]; then
        if [[ ! -f "${output_base}.dag.txt" ]]; then
            log_error "Cannot skip DAG generation: ${output_base}.dag.txt not found"
            exit 1
        fi
    fi

    # Setup signal handler
    trap 'handle_interrupt' INT TERM

    # Check requirements
    check_requirements

    log_info "Starting finetuning dataset generation pipeline..."
    log_info "Output base: $output_base"
    [[ "$skip_sample" == false ]] && log_info "Number of incidents: $num_incidents"
    [[ "$skip_sample" == true ]] && log_info "Skipping sampling (using existing .jsonl)"
    [[ "$skip_dag" == true ]] && log_info "Skipping DAG generation (using existing .dag.txt)"
    [[ -n "$category" ]] && log_info "Category filter: $category"
    [[ -n "$severity" ]] && log_info "Severity filter: $severity"
    [[ -n "$seed" ]] && log_info "Random seed: $seed"
    log_info "LLM Model: $model"
    echo ""

    # ============================================================
    # STEP 1: Sample the dataset
    # ============================================================
    if [[ "$skip_sample" == false ]]; then
        log_info "STEP 1/3: Sampling dataset..."

        local sample_cmd="python3 $SCRIPT_DIR/sample_dataset.py"
        sample_cmd+=" --num-incidents $num_incidents"
        sample_cmd+=" --output ${output_base}.jsonl"
        sample_cmd+=" --base-dir $base_dir"

        [[ -n "$category" ]] && sample_cmd+=" --category $category"
        [[ -n "$severity" ]] && sample_cmd+=" --severity $severity"
        [[ -n "$seed" ]] && sample_cmd+=" --seed $seed"
        [[ "$include_stats" == true ]] && sample_cmd+=" --include-stats"

        if [[ "$verbose" == true ]]; then
            log_info "Running: $sample_cmd"
        fi

        if ! eval "$sample_cmd" 2>&1; then
            log_error "Failed to sample dataset"
            exit 1
        fi

        if [[ ! -f "${output_base}.jsonl" ]]; then
            log_error "Sample output file not created: ${output_base}.jsonl"
            exit 1
        fi

        log_success "Dataset sampled: ${output_base}.jsonl"
        echo ""
    else
        log_info "STEP 1/3: Using existing sample: ${output_base}.jsonl"
        echo ""
    fi

    # ============================================================
    # STEP 2: Generate DAG analysis
    # ============================================================
    if [[ "$skip_dag" == false ]]; then
        log_info "STEP 2/3: Generating DAG analysis..."

        local dag_cmd="python3 $SCRIPT_DIR/alert_dag_parser.py"
        dag_cmd+=" ${output_base}.jsonl"
        dag_cmd+=" --output ${output_base}.dag.txt"

        [[ "$verbose" == true ]] && dag_cmd+=" --verbose"

        if [[ "$verbose" == true ]]; then
            log_info "Running: $dag_cmd"
        fi

        if ! eval "$dag_cmd" 2>&1; then
            log_error "Failed to generate DAG analysis"
            exit 1
        fi

        if [[ ! -f "${output_base}.dag.txt" ]]; then
            log_error "DAG output file not created: ${output_base}.dag.txt"
            exit 1
        fi

        log_success "DAG analysis generated: ${output_base}.dag.txt"
        echo ""
    else
        log_info "STEP 2/3: Using existing DAG analysis: ${output_base}.dag.txt"
        echo ""
    fi

    # ============================================================
    # STEP 3: Generate LLM analysis
    # ============================================================
    log_info "STEP 3/3: Generating LLM-enhanced analysis..."

    # Determine output filename
    local llm_output_file
    if [[ -n "$model_suffix" ]]; then
        llm_output_file="${output_base}.llm.${model_suffix}.txt"
    else
        # Auto-generate from model name
        local model_name=$(echo "$model" | sed 's/:.*$//' | sed 's/\//_/g')
        llm_output_file="${output_base}.llm.${model_name}.txt"
    fi

    local llm_cmd="python3 $SCRIPT_DIR/alert_dag_parser_llm.py"
    llm_cmd+=" ${output_base}.jsonl"
    llm_cmd+=" --output $llm_output_file"
    llm_cmd+=" --model $model"
    llm_cmd+=" --base-url $base_url"

    [[ "$verbose" == true ]] && llm_cmd+=" --verbose"

    if [[ "$verbose" == true ]]; then
        log_info "Running: $llm_cmd"
    fi

    if ! eval "$llm_cmd" 2>&1; then
        log_error "Failed to generate LLM analysis"
        exit 1
    fi

    if [[ ! -f "$llm_output_file" ]]; then
        log_error "LLM output file not created: $llm_output_file"
        exit 1
    fi

    log_success "LLM analysis generated: $llm_output_file"
    echo ""

    # ============================================================
    # Summary
    # ============================================================
    log_success "Pipeline completed successfully!"
    echo ""
    log_info "Generated files:"
    log_info "  - ${output_base}.jsonl              (Sampled incidents + events)"
    log_info "  - ${output_base}.dag.txt            (DAG analysis)"
    log_info "  - $llm_output_file   (LLM-enhanced analysis)"

    if [[ -f "${output_base}.stats.json" ]]; then
        log_info "  - ${output_base}.stats.json         (Statistics)"
    fi

    echo ""

    # Show file sizes
    log_info "File sizes:"
    ls -lh "${output_base}.jsonl" "${output_base}.dag.txt" "$llm_output_file" 2>/dev/null | awk '{if (NR>1) print "  - " $9 ": " $5}'

    echo ""
    log_success "Dataset ready for finetuning!"
}

# Run main function with all arguments
main "$@"

#!/bin/bash

# Slips DAG Analysis with LLM Integration
# This script executes the Slips DAG generator and feeds output to an LLM for security analysis

set -euo pipefail

# Default configuration
DEFAULT_MODEL="gpt-4o-mini"
DEFAULT_BASE_URL="https://api.openai.com/v1"
DEFAULT_FORMAT="minimal"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLM_TOOL="../benchmark_models/stream_query_llm_long_prompt.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage information
usage() {
    cat << EOF
Usage: $0 <log_file> [ip_address] [options]

Analyze Slips evidence logs using DAG generation and LLM analysis.

Arguments:
    log_file        Path to the Slips evidence log file
    ip_address      Optional: specific IP address to analyze

Options:
    --format FORMAT        Output format: minimal, compact, pattern, full (default: minimal)
    --model MODEL          LLM model to use (default: gpt-4o-mini)
    --base-url URL         LLM API base URL (default: https://api.openai.com/v1)
    --detailed             Use full format with summary for detailed analysis
    --all-ips              Analyze all IPs in the log (default behavior if no IP specified)
    --max-events N         Limit to N events per IP
    --include-threat-level Include threat level information in output
    --per-analysis         Generate separate DAG for each alert/analysis instead of per IP
    --output FILE          Save analysis to file
    --dag-only             Only run DAG generation, skip LLM analysis
    --help                 Show this help message

Examples:
    # Quick analysis of all threats
    $0 sample_logs/slips-evidence.log

    # Detailed analysis of specific IP
    $0 sample_logs/slips.log 192.168.1.113 --detailed

    # Pattern analysis with custom model
    $0 sample_logs/slips-5.log --format pattern --model qwen2.5:3b

    # Include threat level information in output
    $0 sample_logs/slips.log --include-threat-level --output analysis.txt

    # Generate DAG per analysis/alert instead of per IP
    $0 sample_logs/slips.log --per-analysis --format compact
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
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate requirements
check_requirements() {
    # Check if DAG generator exists
    if [[ ! -f "$SCRIPT_DIR/slips_dag_generator.py" ]]; then
        log_error "slips_dag_generator.py not found in $SCRIPT_DIR"
        exit 1
    fi

    # Check if LLM tool exists
    if [[ ! -f "$SCRIPT_DIR/$LLM_TOOL" ]]; then
        log_error "LLM query tool not found at $SCRIPT_DIR/$LLM_TOOL"
        exit 1
    fi

    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed"
        exit 1
    fi
}

# Generate security analysis prompt
create_analysis_prompt() {
    local dag_output="$1"
    cat << EOF
You are a cybersecurity analyst. Analyze the following Slips network security evidence and provide a concise assessment.

SECURITY EVIDENCE:
$dag_output

Please provide:
1. **Threat Severity**: Overall risk level (Critical/High/Medium/Low)
2. **Attack Patterns**: Key attack types and techniques identified
3. **Priority Actions**: Top 3 immediate actions for security team
4. **Key Findings**: Most concerning security events (max 3 bullet points)

Keep the analysis focused and actionable for incident response teams.
EOF
}

# Main execution function
main() {
    local log_file=""
    local ip_address=""
    local format="$DEFAULT_FORMAT"
    local model="$DEFAULT_MODEL"
    local base_url="$DEFAULT_BASE_URL"
    local output_file=""
    local dag_args=()
    local dag_only=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --format)
                format="$2"
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
            --detailed)
                format="full"
                dag_args+=(--summary)
                shift
                ;;
            --all-ips)
                dag_args+=(--all-ips)
                shift
                ;;
            --max-events)
                dag_args+=(--max-events "$2")
                shift 2
                ;;
            --include-threat-level)
                dag_args+=(--include-threat-level)
                shift
                ;;
            --per-analysis)
                dag_args+=(--per-analysis)
                shift
                ;;
            --output)
                output_file="$2"
                shift 2
                ;;
            --dag-only)
                dag_only=true
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
                if [[ -z "$log_file" ]]; then
                    log_file="$1"
                elif [[ -z "$ip_address" ]]; then
                    ip_address="$1"
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
    if [[ -z "$log_file" ]]; then
        log_error "Log file is required"
        usage
        exit 1
    fi

    if [[ ! -f "$log_file" ]]; then
        log_error "Log file not found: $log_file"
        exit 1
    fi

    # Check requirements
    check_requirements

    # Build DAG command
    local dag_cmd="python3 $SCRIPT_DIR/slips_dag_generator.py"
    dag_cmd+=" $log_file"
    
    if [[ -n "$ip_address" ]]; then
        dag_cmd+=" $ip_address"
    else
        dag_cmd+=" --all-ips"
    fi
    
    dag_cmd+=" --$format"
    
    for arg in "${dag_args[@]}"; do
        dag_cmd+=" $arg"
    done

    log_info "Generating DAG analysis..."
    log_info "Command: $dag_cmd"

    # Execute DAG generation
    local dag_output
    if ! dag_output=$(eval "$dag_cmd" 2>&1); then
        log_error "DAG generation failed:"
        echo "$dag_output"
        exit 1
    fi

    if [[ -z "$dag_output" ]]; then
        log_warning "No security evidence found in log file"
        exit 0
    fi

    log_success "DAG analysis completed"

    # If dag-only mode, just output and exit
    if [[ "$dag_only" == true ]]; then
        echo "$dag_output"
        if [[ -n "$output_file" ]]; then
            echo "$dag_output" > "$output_file"
            log_success "DAG output saved to $output_file"
        fi
        exit 0
    fi

    # Generate LLM analysis prompt
    log_info "Preparing LLM analysis..."
    local analysis_prompt
    analysis_prompt=$(create_analysis_prompt "$dag_output")

    # Create temporary file for prompt
    local temp_prompt
    temp_prompt=$(mktemp)
    echo "$analysis_prompt" > "$temp_prompt"

    # Execute LLM analysis
    log_info "Running LLM analysis with model: $model"
    local llm_cmd="python3 $SCRIPT_DIR/$LLM_TOOL"
    llm_cmd+=" --prompt $temp_prompt"
    llm_cmd+=" --model $model"
    llm_cmd+=" --base_url $base_url"

    local analysis_output
    if ! analysis_output=$(eval "$llm_cmd" 2>&1); then
        log_error "LLM analysis failed:"
        echo "$analysis_output"
        rm -f "$temp_prompt"
        exit 1
    fi

    # Clean up temporary file
    rm -f "$temp_prompt"

    # Display results
    echo
    echo "==================== SECURITY ANALYSIS REPORT ===================="
    echo "$analysis_output"
    echo "===================================================================="

    # Save to file if requested
    if [[ -n "$output_file" ]]; then
        {
            echo "==================== DAG EVIDENCE ===================="
            echo "$dag_output"
            echo
            echo "==================== LLM ANALYSIS ===================="
            echo "$analysis_output"
        } > "$output_file"
        log_success "Full analysis saved to $output_file"
    fi

    log_success "Analysis completed successfully"
}

# Run main function with all arguments
main "$@"
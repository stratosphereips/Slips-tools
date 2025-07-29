#!/bin/bash

# Slips Dataset Generator
# Creates a JSON dataset with multi-perspective analysis of each Slips alert

set -euo pipefail

# Default configuration
DEFAULT_MODEL="gpt-4o-mini"
DEFAULT_BASE_URL="https://api.openai.com/v1"
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
Usage: $0 <log_file> <output.json> [options]

Generate a JSON dataset from Slips evidence logs with multi-perspective analysis.

Arguments:
    log_file        Path to the Slips evidence log file
    output.json     Path to output JSON dataset file

Options:
    --model MODEL          LLM model to use (default: gpt-4o-mini)
    --base-url URL         LLM API base URL (default: https://api.openai.com/v1)
    --text-output FILE     Also generate human-readable text output
    --help                 Show this help message

Examples:
    # Generate dataset with default model
    $0 sample_logs/slips.log dataset.json

    # Use custom model and generate text output
    $0 sample_logs/slips.log dataset.json --model qwen2.5:3b --text-output analysis.txt
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

# Create behavior analysis prompt
create_behavior_prompt() {
    local alert_evidence="$1"
    cat << EOF
You are a cybersecurity analyst. Analyze the following network security alert and provide a clear technical explanation of the network behavior observed.

SECURITY ALERT:
$alert_evidence

Please provide a concise technical explanation of what network behavior was observed in this alert. Focus on:
- What specific network activities occurred
- Technical details of the observed behavior
- Network protocols and communication patterns involved

Keep the explanation technical but clear, suitable for security analysts.
EOF
}

# Create cause analysis prompt
create_cause_prompt() {
    local alert_evidence="$1"
    cat << EOF
You are a cybersecurity analyst. Analyze the following network security alert and explain the possible causes of this behavior.

SECURITY ALERT:
$alert_evidence

Please provide an analysis of the possible causes of this network behavior. Consider:
- Potential attack vectors or techniques
- Possible legitimate reasons for this behavior
- Common scenarios that could lead to this pattern
- Root cause analysis from a security perspective

Provide a balanced analysis covering both malicious and benign possibilities.
EOF
}

# Create risk assessment prompt
create_risk_prompt() {
    local alert_evidence="$1"
    cat << EOF
You are a cybersecurity analyst. Analyze the following network security alert and provide a risk assessment.

SECURITY ALERT:
$alert_evidence

Please provide a risk assessment for this alert including:
- Risk level (Critical/High/Medium/Low) with justification
- Potential business impact if this represents a real threat
- Likelihood this represents actual malicious activity
- Recommended priority for investigation

Base your assessment on common cybersecurity knowledge and threat intelligence.
EOF
}

# Query LLM with a prompt
query_llm() {
    local prompt="$1"
    local model="$2"
    local base_url="$3"
    
    # Create temporary file for prompt
    local temp_prompt
    temp_prompt=$(mktemp)
    echo "$prompt" > "$temp_prompt"
    
    # Execute LLM query
    local llm_cmd="python3 $SCRIPT_DIR/$LLM_TOOL"
    llm_cmd+=" --prompt $temp_prompt"
    llm_cmd+=" --model $model"
    llm_cmd+=" --base_url $base_url"
    # llm_cmd+=" --stats_only"  # Remove stats_only to get clean output
    
    local response
    if response=$(eval "$llm_cmd" 2>/dev/null); then
        # Remove the temporary file
        rm -f "$temp_prompt"
        echo "$response"
        return 0
    else
        rm -f "$temp_prompt"
        echo "Error: LLM query failed"
        return 1
    fi
}

# Escape JSON string
escape_json() {
    local input="$1"
    # Escape backslashes, quotes, and newlines for JSON
    echo "$input" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//'
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

    # Check jq availability for JSON processing
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi

}

# Main execution function
main() {
    local log_file=""
    local output_file=""
    local model="$DEFAULT_MODEL"
    local base_url="$DEFAULT_BASE_URL"
    local text_output=""

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --model)
                model="$2"
                shift 2
                ;;
            --base-url)
                base_url="$2"
                shift 2
                ;;
            --text-output)
                text_output="$2"
                shift 2
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
                elif [[ -z "$output_file" ]]; then
                    output_file="$1"
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

    if [[ -z "$output_file" ]]; then
        log_error "Output JSON file is required"
        usage
        exit 1
    fi

    if [[ ! -f "$log_file" ]]; then
        log_error "Log file not found: $log_file"
        exit 1
    fi

    # Check requirements
    check_requirements

    log_info "Starting dataset generation..."
    log_info "Input: $log_file"
    log_info "Output: $output_file"
    log_info "Model: $model"

    # Check if the log file is already DAG output or raw Slips log
    if grep -q "============================================================" "$log_file"; then
        log_info "Input appears to be pre-processed DAG output, using directly..."
        dag_output=$(cat "$log_file")
    else
        log_info "Generating DAG analysis in per-analysis mode..."
        local dag_cmd="python3 $SCRIPT_DIR/slips_dag_generator.py $log_file --per-analysis --minimal"
        
        if ! dag_output=$(eval "$dag_cmd" 2>&1); then
            log_error "DAG generation failed:"
            echo "$dag_output"
            exit 1
        fi
    fi

    if [[ -z "$dag_output" ]]; then
        log_warning "No security evidence found in log file"
        echo '{"dataset": []}' > "$output_file"
        log_success "Empty dataset created: $output_file"
        exit 0
    fi

    log_success "DAG analysis completed"
    
    # Parse individual alerts from DAG output
    log_info "Parsing individual alerts..."
    
    # Use a more robust approach to split by separator while preserving multi-line blocks
    local temp_file=$(mktemp)
    echo "$dag_output" > "$temp_file"
    
    # Split by separator and read complete blocks
    local alerts=()
    local current_block=""
    local in_block=false
    
    while IFS= read -r line; do
        if [[ "$line" == "============================================================" ]]; then
            if [[ -n "$current_block" ]]; then
                # Trim and save the completed block
                current_block=$(echo "$current_block" | sed '/^[[:space:]]*$/d')
                if [[ -n "$current_block" ]]; then
                    alerts+=("$current_block")
                fi
            fi
            current_block=""
            in_block=false
        else
            if [[ -n "$line" || "$in_block" == true ]]; then
                in_block=true
                if [[ -n "$current_block" ]]; then
                    current_block+=$'\n'"$line"
                else
                    current_block="$line"
                fi
            fi
        fi
    done < "$temp_file"
    
    # Don't forget the last block if there's no trailing separator
    if [[ -n "$current_block" ]]; then
        current_block=$(echo "$current_block" | sed '/^[[:space:]]*$/d')
        if [[ -n "$current_block" ]]; then
            alerts+=("$current_block")
        fi
    fi
    
    rm -f "$temp_file"
    
    local alert_count=${#alerts[@]}
    log_info "Found $alert_count alerts to analyze"
    
    if [[ $alert_count -eq 0 ]]; then
        log_warning "No alerts found in DAG output"
        echo '{"dataset": []}' > "$output_file"
        log_success "Empty dataset created: $output_file"
        exit 0
    fi
    
    # Initialize JSON output
    echo '{"dataset": [' > "$output_file"
    local first_entry=true
    
    # Process each alert with LLM analysis
    local current_alert=1
    for alert in "${alerts[@]}"; do
        # Skip empty alerts
        if [[ -z "$alert" || "$alert" =~ ^[[:space:]]*$ ]]; then
            continue
        fi
        
        log_info "Processing alert $current_alert/$alert_count..."
        
        # Generate the three analyses
        log_info "  Generating behavior analysis..."
        local behavior_prompt
        behavior_prompt=$(create_behavior_prompt "$alert")
        local behavior_analysis
        behavior_analysis=$(query_llm "$behavior_prompt" "$model" "$base_url")
        
        log_info "  Generating cause analysis..."
        local cause_prompt
        cause_prompt=$(create_cause_prompt "$alert")
        local cause_analysis
        cause_analysis=$(query_llm "$cause_prompt" "$model" "$base_url")
        
        log_info "  Generating risk assessment..."
        local risk_prompt
        risk_prompt=$(create_risk_prompt "$alert")
        local risk_assessment
        risk_assessment=$(query_llm "$risk_prompt" "$model" "$base_url")
        
        # Escape content for JSON
        local escaped_evidence
        escaped_evidence=$(escape_json "$alert")
        local escaped_behavior
        escaped_behavior=$(escape_json "$behavior_analysis")
        local escaped_cause
        escaped_cause=$(escape_json "$cause_analysis")
        local escaped_risk
        escaped_risk=$(escape_json "$risk_assessment")
        
        # Add comma if not first entry
        if [[ "$first_entry" == false ]]; then
            echo ',' >> "$output_file"
        fi
        first_entry=false
        
        # Add JSON entry
        cat >> "$output_file" << EOF
    {
        "alert_id": $current_alert,
        "evidence": "$escaped_evidence",
        "behavior_explanation": "$escaped_behavior",
        "cause_analysis": "$escaped_cause",
        "risk_assessment": "$escaped_risk"
    }
EOF
        
        ((current_alert++))
    done
    
    # Close JSON
    echo '' >> "$output_file"
    echo ']}' >> "$output_file"
    
    log_success "Dataset generation completed!"
    log_success "Generated dataset with $((current_alert-1)) alerts: $output_file"
    
    # Generate text output if requested
    if [[ -n "$text_output" ]]; then
        log_info "Generating text output: $text_output"
        
        # Generate human-readable text format
        {
            echo "==============================================="
            echo "        SLIPS SECURITY ANALYSIS REPORT"
            echo "==============================================="
            echo "Generated: $(date)"
            echo "Model: $model"
            echo "Total Alerts: $((current_alert-1))"
            echo ""
            
            # Process each alert from the JSON
            local alert_id=1
            while jq -e ".dataset[$((alert_id-1))]" "$output_file" >/dev/null 2>&1; do
                local evidence behavior cause risk
                
                evidence=$(jq -r ".dataset[$((alert_id-1))].evidence" "$output_file")
                behavior=$(jq -r ".dataset[$((alert_id-1))].behavior_explanation" "$output_file" | sed 's/^AI: //')
                cause=$(jq -r ".dataset[$((alert_id-1))].cause_analysis" "$output_file" | sed 's/^AI: //')
                risk=$(jq -r ".dataset[$((alert_id-1))].risk_assessment" "$output_file" | sed 's/^AI: //')
                
                echo "==============================================="
                echo "ALERT #$alert_id"
                echo "==============================================="
                echo ""
                echo "EVIDENCE:"
                echo "$evidence"
                echo ""
                echo "BEHAVIOR ANALYSIS:"
                echo "$behavior"
                echo ""
                echo "CAUSE ANALYSIS:"
                echo "$cause"
                echo ""
                echo "RISK ASSESSMENT:"
                echo "$risk"
                echo ""
                echo ""
                
                ((alert_id++))
            done
        } > "$text_output"
        
        log_success "Text output generated: $text_output"
    fi
}

# Run main function with all arguments
main "$@"
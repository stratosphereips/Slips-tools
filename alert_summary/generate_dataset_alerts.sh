#!/bin/bash

# Slips Alerts Dataset Generator (JSONL/IDEA Format)
# Creates a JSON dataset with multi-perspective analysis of each Slips incident

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

# Global error log
ERROR_LOG=""

# Print usage information
usage() {
    cat << EOF
Usage: $0 <alerts.json> <output.json> [options]

Generate a JSON dataset from Slips JSONL/IDEA alert files with multi-perspective analysis.

Arguments:
    alerts.json     Path to the JSONL alerts file (IDEA format)
    output.json     Path to output JSON dataset file

Options:
    --model MODEL          LLM model to use (default: gpt-4o-mini)
    --base-url URL         LLM API base URL (default: https://api.openai.com/v1)
    --text-output FILE     Also generate human-readable text output
    --csv-output FILE      Also generate CSV format output
    --help                 Show this help message

Examples:
    # Generate dataset with default model
    $0 sample_logs/alya_datasets/Malware/.../alerts.json dataset.json

    # Use custom model and generate text output
    $0 alerts.json dataset.json --model qwen2.5:3b --text-output analysis.txt

    # Generate both JSON and CSV output
    $0 alerts.json dataset.json --csv-output dataset.csv
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
    if [[ -n "$ERROR_LOG" ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$ERROR_LOG"
    fi
}

# Create behavior analysis prompt
create_behavior_prompt() {
    local alert_evidence="$1"
    cat << EOF
You are a cybersecurity analyst. Analyze the following network security alert and provide a concise, structured technical explanation of the observed network behavior.

SECURITY ALERT:
$alert_evidence

Output Requirements:
- Respond with ONLY the analysis content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:
  **Source:** [IP address]
  **Activity:** [Brief activity type]
  **Detected Flows:**
  • [flow description using format: src_ip:port/proto → dest_targets (service)]
  • [additional flows as needed]

  **Summary:** [1-2 sentence technical summary of the behavior]

Guidelines:
- Be succinct (fewer words than raw evidence)
- Focus only on actual network activity observed
- Use consistent port/protocol notation (e.g., 80/TCP, 443/TCP)
- Express flows in compact format when possible
- Avoid high-level definitions or irrelevant metadata
- Keep technical depth consistent across all analyses
- Use bullet points for flows, structured format for sections

EOF
}

# Create cause analysis prompt
create_cause_prompt() {
    local alert_evidence="$1"
    cat << EOF
You are a cybersecurity analyst. Analyze the following network security alert and provide a structured analysis of possible causes.

SECURITY ALERT:
$alert_evidence

Output Requirements:
- Respond with ONLY the analysis content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:

**Possible Causes:**

**1. Malicious Activity:**
• [Specific attack technique or malicious cause]
• [Additional malicious possibilities if relevant]

**2. Legitimate Activity:**
• [Benign operational cause]
• [Additional legitimate possibilities if relevant]

**3. Misconfigurations:**
• [Technical misconfigurations that could cause this behavior]

**Conclusion:** [1-2 sentence assessment of most likely cause category with recommendation for further investigation]

Guidelines:
- Be succinct (fewer words than raw evidence)
- Focus on relevant causes only (attack techniques, misconfigurations, legitimate operations)
- Use precise analyst-level language
- Maintain consistent structure and depth across all analyses
- Avoid generic definitions or unnecessary context

EOF
}

# Create risk assessment prompt
create_risk_prompt() {
    local alert_evidence="$1"
    cat << EOF
You are a cybersecurity analyst. Analyze the following network security alert and provide a structured risk assessment.

SECURITY ALERT:
$alert_evidence

Output Requirements:
- Respond with ONLY the assessment content
- Do NOT include any prefixes (like "AI:"), statistics, or metadata
- Do NOT include token counts, timing information, or performance stats
- Use this exact structure:

**Risk Level:** [Critical/High/Medium/Low]

**Justification:** [1-2 sentence technical justification for the risk level]

**Business Impact:** [Single clear sentence describing the most relevant business effect]

**Likelihood of Malicious Activity:** [High/Medium/Low] - [Brief rationale]

**Investigation Priority:** [Immediate/High/Medium/Low] - [Brief justification]

Guidelines:
- Use only the four risk levels: Critical, High, Medium, Low
- Keep justifications concise and technical
- Focus business impact on most relevant effect (data access, service disruption, etc.)
- Use consistent language for likelihood assessments
- Maintain uniform structure and depth across all assessments
- Avoid verbose or generic text

EOF
}

# Query LLM with a prompt (with retry logic)
query_llm() {
    local prompt="$1"
    local model="$2"
    local base_url="$3"
    local max_retries=3
    local retry_delay=5

    # Create temporary file for prompt
    local temp_prompt
    temp_prompt=$(mktemp)
    echo "$prompt" > "$temp_prompt"

    # Execute LLM query with retry logic
    for attempt in $(seq 1 $max_retries); do
        local llm_cmd="python3 $SCRIPT_DIR/$LLM_TOOL"
        llm_cmd+=" --prompt $temp_prompt"
        llm_cmd+=" --model $model"
        llm_cmd+=" --base_url $base_url"

        local response
        if response=$(eval "$llm_cmd" 2>&1); then
            # Check for actual content (not just success exit code)
            if [[ -n "$response" && ! "$response" =~ ^Error ]]; then
                rm -f "$temp_prompt"
                echo "$response"
                return 0
            fi
        fi

        # Retry logic
        if [[ $attempt -lt $max_retries ]]; then
            log_warning "LLM query failed (attempt $attempt/$max_retries). Retrying in ${retry_delay}s..."
            sleep $retry_delay
        fi
    done

    # All retries failed
    rm -f "$temp_prompt"
    log_error "LLM query failed after $max_retries attempts"
    log_error "Last response: $response"
    return 1
}

# Escape JSON string
escape_json() {
    local input="$1"
    # Escape backslashes, quotes, and newlines for JSON
    echo "$input" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//'
}

# Escape CSV string
escape_csv() {
    local input="$1"
    # Replace newlines with spaces and escape double quotes
    echo "$input" | tr '\n' ' ' | sed 's/"/\"\"/g'
}

# Validate requirements
check_requirements() {
    # Check if alert DAG parser exists
    if [[ ! -f "$SCRIPT_DIR/alert_dag_parser.py" ]]; then
        log_error "alert_dag_parser.py not found in $SCRIPT_DIR"
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

# Validate JSONL alert file format
validate_alert_file() {
    local file="$1"

    # Check if file contains JSONL format
    if ! head -1 "$file" | python3 -m json.tool >/dev/null 2>&1; then
        log_error "File is not valid JSONL format (first line is not valid JSON)"
        return 1
    fi

    # Check if file contains Incidents
    local incident_count
    incident_count=$(grep -c '"Status": "Incident"' "$file" 2>/dev/null || echo "0")

    if [[ "$incident_count" -eq 0 ]]; then
        log_error "No Incidents found in file (expected IDEA format with Status: Incident)"
        return 1
    fi

    # Check if file contains Events
    local event_count
    event_count=$(grep -c '"Status": "Event"' "$file" 2>/dev/null || echo "0")

    if [[ "$event_count" -eq 0 ]]; then
        log_warning "No Events found in file (only Incidents present)"
    fi

    log_info "Validated JSONL file: $incident_count incidents, $event_count events"
    return 0
}

# Handle interruption gracefully
handle_interrupt() {
    log_warning ""
    log_warning "Interrupted by user. Saving partial dataset..."

    # Close JSON properly if output file exists
    if [[ -f "$output_file" ]]; then
        echo '' >> "$output_file"
        echo ']}' >> "$output_file"
        log_success "Partial dataset saved: $output_file ($((current_alert-1)) alerts)"
    fi

    if [[ -f "$ERROR_LOG" && -s "$ERROR_LOG" ]]; then
        log_warning "Errors logged to: $ERROR_LOG"
    fi

    exit 130
}

# Main execution function
main() {
    local log_file=""
    local output_file=""
    local model="$DEFAULT_MODEL"
    local base_url="$DEFAULT_BASE_URL"
    local text_output=""
    local csv_output=""

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
            --csv-output)
                csv_output="$2"
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
        log_error "Alert file is required"
        usage
        exit 1
    fi

    if [[ -z "$output_file" ]]; then
        log_error "Output JSON file is required"
        usage
        exit 1
    fi

    if [[ ! -f "$log_file" ]]; then
        log_error "Alert file not found: $log_file"
        exit 1
    fi

    # Setup error log
    ERROR_LOG="${output_file}.errors.log"
    > "$ERROR_LOG"  # Clear/create error log

    # Setup signal handler
    trap 'handle_interrupt' INT TERM

    # Check requirements
    check_requirements

    # Validate alert file format
    if ! validate_alert_file "$log_file"; then
        exit 1
    fi

    log_info "Starting dataset generation..."
    log_info "Input: $log_file"
    log_info "Output: $output_file"
    log_info "Model: $model"

    # Test LLM connectivity before processing all alerts
    log_info "Testing LLM connectivity..."
    if ! echo "test" | python3 "$SCRIPT_DIR/$LLM_TOOL" --prompt /dev/stdin --model "$model" --base_url "$base_url" >/dev/null 2>&1; then
        log_error "Cannot connect to LLM model at $base_url"
        log_error "Please check API key and endpoint configuration"
        exit 1
    fi
    log_success "LLM connection successful"

    # Generate DAG analysis using alert_dag_parser.py
    log_info "Generating incident analysis..."
    local dag_cmd="python3 $SCRIPT_DIR/alert_dag_parser.py $log_file"

    local dag_output
    if ! dag_output=$(eval "$dag_cmd" 2>&1); then
        log_error "Alert DAG generation failed:"
        echo "$dag_output"
        exit 1
    fi

    if [[ -z "$dag_output" ]]; then
        log_warning "No security incidents found in alert file"
        echo '{"dataset": []}' > "$output_file"
        log_success "Empty dataset created: $output_file"
        exit 0
    fi

    log_success "Incident analysis completed"

    # Parse individual alerts from DAG output
    log_info "Parsing individual incidents..."

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
    log_info "Found $alert_count incidents to analyze"

    if [[ $alert_count -eq 0 ]]; then
        log_warning "No incidents found in DAG output"
        echo '{"dataset": []}' > "$output_file"
        log_success "Empty dataset created: $output_file"
        exit 0
    fi

    # Initialize JSON output
    echo '{"dataset": [' > "$output_file"
    local first_entry=true

    # Process each alert with LLM analysis
    local current_alert=1
    local failed_alerts=0

    for alert in "${alerts[@]}"; do
        # Skip empty alerts
        if [[ -z "$alert" || "$alert" =~ ^[[:space:]]*$ ]]; then
            continue
        fi

        log_info "Processing incident $current_alert/$alert_count..."

        # Generate behavior analysis
        log_info "  Generating behavior analysis..."
        local behavior_prompt
        behavior_prompt=$(create_behavior_prompt "$alert")
        local behavior_analysis

        if ! behavior_analysis=$(query_llm "$behavior_prompt" "$model" "$base_url"); then
            log_error "Failed to generate behavior analysis for incident $current_alert - SKIPPING"
            ((failed_alerts++))
            ((current_alert++))
            continue
        fi

        # Clean unwanted content
        behavior_analysis=$(echo "$behavior_analysis" | sed 's/^AI: //g' | sed '/🧠 Stats:/,$ d')

        # Generate cause analysis
        log_info "  Generating cause analysis..."
        local cause_prompt
        cause_prompt=$(create_cause_prompt "$alert")
        local cause_analysis

        if ! cause_analysis=$(query_llm "$cause_prompt" "$model" "$base_url"); then
            log_error "Failed to generate cause analysis for incident $current_alert - SKIPPING"
            ((failed_alerts++))
            ((current_alert++))
            continue
        fi

        # Clean unwanted content
        cause_analysis=$(echo "$cause_analysis" | sed 's/^AI: //g' | sed '/🧠 Stats:/,$ d')

        # Generate risk assessment
        log_info "  Generating risk assessment..."
        local risk_prompt
        risk_prompt=$(create_risk_prompt "$alert")
        local risk_assessment

        if ! risk_assessment=$(query_llm "$risk_prompt" "$model" "$base_url"); then
            log_error "Failed to generate risk assessment for incident $current_alert - SKIPPING"
            ((failed_alerts++))
            ((current_alert++))
            continue
        fi

        # Clean unwanted content
        risk_assessment=$(echo "$risk_assessment" | sed 's/^AI: //g' | sed '/🧠 Stats:/,$ d')

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
    log_success "Generated dataset with $((current_alert-1-failed_alerts)) incidents: $output_file"

    if [[ $failed_alerts -gt 0 ]]; then
        log_warning "Completed with $failed_alerts failed incidents (skipped)"
    fi

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
            echo "Total Alerts: $((current_alert-1-failed_alerts))"
            echo ""

            # Process each alert from the JSON
            local alert_id=1
            while jq -e ".dataset[$((alert_id-1))]" "$output_file" >/dev/null 2>&1; do
                local evidence behavior cause risk

                evidence=$(jq -r ".dataset[$((alert_id-1))].evidence" "$output_file")
                behavior=$(jq -r ".dataset[$((alert_id-1))].behavior_explanation" "$output_file")
                cause=$(jq -r ".dataset[$((alert_id-1))].cause_analysis" "$output_file")
                risk=$(jq -r ".dataset[$((alert_id-1))].risk_assessment" "$output_file")

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

    # Generate CSV output if requested
    if [[ -n "$csv_output" ]]; then
        log_info "Generating CSV output: $csv_output"

        # Generate CSV format
        {
            # CSV header
            echo '"alert_id","evidence","behavior_explanation","cause_analysis","risk_assessment"'

            # Process each alert from the JSON
            local alert_id=1
            while jq -e ".dataset[$((alert_id-1))]" "$output_file" >/dev/null 2>&1; do
                local evidence behavior cause risk

                evidence=$(jq -r ".dataset[$((alert_id-1))].evidence" "$output_file")
                behavior=$(jq -r ".dataset[$((alert_id-1))].behavior_explanation" "$output_file")
                cause=$(jq -r ".dataset[$((alert_id-1))].cause_analysis" "$output_file")
                risk=$(jq -r ".dataset[$((alert_id-1))].risk_assessment" "$output_file")

                # Escape CSV fields
                local csv_evidence csv_behavior csv_cause csv_risk
                csv_evidence=$(escape_csv "$evidence")
                csv_behavior=$(escape_csv "$behavior")
                csv_cause=$(escape_csv "$cause")
                csv_risk=$(escape_csv "$risk")

                # Output CSV row
                echo "$alert_id,\"$csv_evidence\",\"$csv_behavior\",\"$csv_cause\",\"$csv_risk\""

                ((alert_id++))
            done
        } > "$csv_output"

        log_success "CSV output generated: $csv_output"
    fi

    # Report error log if it has content
    if [[ -f "$ERROR_LOG" && -s "$ERROR_LOG" ]]; then
        log_warning "Errors were logged to: $ERROR_LOG"
    else
        # Remove empty error log
        rm -f "$ERROR_LOG"
    fi
}

# Run main function with all arguments
main "$@"

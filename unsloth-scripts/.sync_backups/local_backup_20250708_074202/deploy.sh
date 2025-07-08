#!/bin/bash 

# Rsync deployment script for Unsloth Qwen Fine-tuning Project
# This script synchronizes the project to a remote server

# Configuration Variables - MODIFY THESE
REMOTE_HOST="200.12.137.13"
REMOTE_PORT="22036"
REMOTE_USER="harpo"
REMOTE_DIR="/home/harpo/unsloth-ex"
LOCAL_DIR="$(pwd)"

# Optional: SSH key path (leave empty to use default)
SSH_KEY=""

# Rsync options
RSYNC_OPTIONS="-avz --delete --progress"

# Files and directories to exclude
EXCLUDE_PATTERNS=(
    ".git/"
    "*.pyc"
    "__pycache__/"
    ".pytest_cache/"
    "*.egg-info/"
    "build/"
    "dist/"
    ".venv/"
    "venv/"
    "*.log"
    ".DS_Store"
    "Thumbs.db"
    "qwen_finetuned/"
    "qwen_finetuned_*/"
    "*.model"
    "*.bin"
    "*.safetensors"
    "mixed_dataset.json"
    "prepared_dataset.json"
    "wandb/"
    ".wandb/"
    "checkpoints/"
    "*.tmp"
    "*.swp"
    "*.swo"
    "*~"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST       Remote host (default: $REMOTE_HOST)"
    echo "  -p, --port PORT       SSH port (default: $REMOTE_PORT)"
    echo "  -u, --user USER       Remote user (default: $REMOTE_USER)"
    echo "  -d, --dir DIR         Remote directory (default: $REMOTE_DIR)"
    echo "  -k, --key KEY         SSH key path (optional)"
    echo "  -n, --dry-run         Show what would be transferred without doing it"
    echo "  -v, --verbose         Verbose output"
    echo "  --delete              Delete files on remote that don't exist locally"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -h server.com -u deploy -d /opt/unsloth-ex"
    echo "  $0 --dry-run --verbose"
    echo "  $0 -k ~/.ssh/deploy_key -h 192.168.1.100"
}

# Function to validate configuration
validate_config() {
    if [[ -z "$REMOTE_HOST" ]]; then
        print_color $RED "Error: Remote host is required"
        exit 1
    fi
    
    if [[ -z "$REMOTE_USER" ]]; then
        print_color $RED "Error: Remote user is required"
        exit 1
    fi
    
    if [[ -z "$REMOTE_DIR" ]]; then
        print_color $RED "Error: Remote directory is required"
        exit 1
    fi
    
    if [[ ! -d "$LOCAL_DIR" ]]; then
        print_color $RED "Error: Local directory does not exist: $LOCAL_DIR"
        exit 1
    fi
}

# Function to build rsync command
build_rsync_command() {
    local rsync_cmd="rsync $RSYNC_OPTIONS"
    
    # Add SSH options
    local ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    if [[ -n "$SSH_KEY" ]]; then
        ssh_opts="$ssh_opts -i $SSH_KEY"
    fi
    ssh_opts="$ssh_opts -p $REMOTE_PORT"
    
    rsync_cmd="$rsync_cmd -e 'ssh $ssh_opts'"
    
    # Add exclude patterns
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        rsync_cmd="$rsync_cmd --exclude='$pattern'"
    done
    
    # Add source and destination
    rsync_cmd="$rsync_cmd $LOCAL_DIR/ $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"
    
    echo "$rsync_cmd"
}

# Function to test SSH connection
test_ssh_connection() {
    print_color $BLUE "Testing SSH connection..."
    
    local ssh_cmd="ssh"
    if [[ -n "$SSH_KEY" ]]; then
        ssh_cmd="$ssh_cmd -i $SSH_KEY"
    fi
    ssh_cmd="$ssh_cmd -p $REMOTE_PORT -o ConnectTimeout=10 -o BatchMode=yes"
    ssh_cmd="$ssh_cmd $REMOTE_USER@$REMOTE_HOST 'echo \"SSH connection successful\"'"
    
    if eval $ssh_cmd &>/dev/null; then
        print_color $GREEN "SSH connection successful"
        return 0
    else
        print_color $RED "SSH connection failed"
        return 1
    fi
}

# Function to create remote directory
create_remote_dir() {
    print_color $BLUE "Creating remote directory if it doesn't exist..."
    
    local ssh_cmd="ssh"
    if [[ -n "$SSH_KEY" ]]; then
        ssh_cmd="$ssh_cmd -i $SSH_KEY"
    fi
    ssh_cmd="$ssh_cmd -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
    ssh_cmd="$ssh_cmd 'mkdir -p $REMOTE_DIR'"
    
    if eval $ssh_cmd; then
        print_color $GREEN "Remote directory ready"
    else
        print_color $RED "Failed to create remote directory"
        exit 1
    fi
}

# Function to show file summary
show_file_summary() {
    print_color $BLUE "Files to be synchronized:"
    find "$LOCAL_DIR" -type f | while read -r file; do
        local relative_path=${file#$LOCAL_DIR/}
        local skip=false
        
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            if [[ "$relative_path" =~ ${pattern%/} ]]; then
                skip=true
                break
            fi
        done
        
        if [[ "$skip" = false ]]; then
            echo "  $relative_path"
        fi
    done
}

# Main deployment function
deploy() {
    print_color $YELLOW "Starting deployment to $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
    print_color $YELLOW "Local directory: $LOCAL_DIR"
    
    # Test SSH connection
    if ! test_ssh_connection; then
        exit 1
    fi
    
    # Create remote directory
    create_remote_dir
    
    # Show file summary if verbose
    if [[ "$VERBOSE" = true ]]; then
        show_file_summary
    fi
    
    # Build and execute rsync command
    local rsync_cmd=$(build_rsync_command)
    
    print_color $BLUE "Executing rsync command:"
    if [[ "$VERBOSE" = true ]]; then
        echo "$rsync_cmd"
    fi
    
    if eval $rsync_cmd; then
        print_color $GREEN "Deployment completed successfully!"
        print_color $GREEN "Files synchronized to $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
    else
        print_color $RED "Deployment failed!"
        exit 1
    fi
}

# Parse command line arguments
DRY_RUN=false
VERBOSE=false
DELETE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            REMOTE_HOST="$2"
            shift 2
            ;;
        -p|--port)
            REMOTE_PORT="$2"
            shift 2
            ;;
        -u|--user)
            REMOTE_USER="$2"
            shift 2
            ;;
        -d|--dir)
            REMOTE_DIR="$2"
            shift 2
            ;;
        -k|--key)
            SSH_KEY="$2"
            shift 2
            ;;
        -n|--dry-run)
            DRY_RUN=true
            RSYNC_OPTIONS="$RSYNC_OPTIONS --dry-run"
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --delete)
            DELETE=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_color $RED "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_color $BLUE "Unsloth Qwen Fine-tuning Project Deployment Script"
    print_color $BLUE "================================================="
    
    # Validate configuration
    validate_config
    
    # Show configuration
    print_color $YELLOW "Configuration:"
    echo "  Remote Host: $REMOTE_HOST"
    echo "  Remote Port: $REMOTE_PORT"
    echo "  Remote User: $REMOTE_USER"
    echo "  Remote Directory: $REMOTE_DIR"
    echo "  Local Directory: $LOCAL_DIR"
    if [[ -n "$SSH_KEY" ]]; then
        echo "  SSH Key: $SSH_KEY"
    fi
    echo "  Dry Run: $DRY_RUN"
    echo "  Verbose: $VERBOSE"
    echo ""
    
    # Confirm deployment
    if [[ "$DRY_RUN" = false ]]; then
        read -p "Continue with deployment? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_color $YELLOW "Deployment cancelled"
            exit 0
        fi
    fi
    
    # Start deployment
    deploy
}

# Run main function
main "$@"

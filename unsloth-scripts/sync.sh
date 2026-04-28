#!/bin/bash 

# Bidirectional Rsync sync script for Unsloth Qwen Fine-tuning Project
# This script provides bidirectional synchronization between local and remote directories

# Configuration Variables - MODIFY THESE
REMOTE_HOST="1.1.1.1"
REMOTE_PORT="22"
REMOTE_USER="user"
REMOTE_DIR="/your/path"
LOCAL_DIR="$(pwd)"

# Optional: SSH key path (leave empty to use default)
SSH_KEY=""

# Rsync options
RSYNC_OPTIONS="-avz --progress"

# Sync direction
SYNC_DIRECTION="push"  # push, pull, both

# Backup options
BACKUP_ENABLED=true
BACKUP_DIR=".sync_backups"

# Files and directories to exclude
EXCLUDE_PATTERNS=(
    ".git/"
    "unsloth_compiled_cache"
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
    ".sync_backups/"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [DIRECTION]"
    echo ""
    echo "Sync Directions:"
    echo "  --push                Push changes from local to remote (default)"
    echo "  --pull                Pull changes from remote to local"
    echo "  --both                Bidirectional sync (experimental)"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST       Remote host (default: $REMOTE_HOST)"
    echo "  -p, --port PORT       SSH port (default: $REMOTE_PORT)"
    echo "  -u, --user USER       Remote user (default: $REMOTE_USER)"
    echo "  -d, --dir DIR         Remote directory (default: $REMOTE_DIR)"
    echo "  -k, --key KEY         SSH key path (optional)"
    echo "  -n, --dry-run         Show what would be transferred without doing it"
    echo "  -v, --verbose         Verbose output"
    echo "  --delete              Delete files that don't exist in source"
    echo "  --no-backup           Disable backup before sync"
    echo "  --backup-dir DIR      Backup directory (default: $BACKUP_DIR)"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --push                                    # Push local changes to remote"
    echo "  $0 --pull                                    # Pull remote changes to local"
    echo "  $0 --both --dry-run                          # Preview bidirectional sync"
    echo "  $0 --push -h server.com -u deploy -d /opt/unsloth-ex"
    echo "  $0 --pull --verbose --no-backup"
    echo "  $0 --both -k ~/.ssh/deploy_key -h 192.168.1.100"
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

# Function to create backup
create_backup() {
    local source_dir=$1
    local backup_name=$2
    
    if [[ "$BACKUP_ENABLED" = false ]]; then
        return 0
    fi
    
    print_color $BLUE "Creating backup: $backup_name"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$source_dir/$BACKUP_DIR/${backup_name}_${timestamp}"
    
    mkdir -p "$backup_path"
    
    # Create backup using rsync
    local rsync_cmd="rsync -av --exclude='$BACKUP_DIR/'"
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        rsync_cmd="$rsync_cmd --exclude='$pattern'"
    done
    rsync_cmd="$rsync_cmd $source_dir/ $backup_path/"
    
    if eval $rsync_cmd &>/dev/null; then
        print_color $GREEN "Backup created: $backup_path"
        
        # Keep only last 5 backups
        find "$source_dir/$BACKUP_DIR" -maxdepth 1 -type d -name "${backup_name}_*" | sort -r | tail -n +6 | xargs -r rm -rf
    else
        print_color $YELLOW "Warning: Backup creation failed"
    fi
}

# Function to create remote backup
create_remote_backup() {
    if [[ "$BACKUP_ENABLED" = false ]]; then
        return 0
    fi
    
    print_color $BLUE "Creating remote backup..."
    
    local ssh_cmd="ssh"
    if [[ -n "$SSH_KEY" ]]; then
        ssh_cmd="$ssh_cmd -i $SSH_KEY"
    fi
    ssh_cmd="$ssh_cmd -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_script="
        mkdir -p $REMOTE_DIR/$BACKUP_DIR
        cd $REMOTE_DIR
        rsync -av --exclude='$BACKUP_DIR/' ./ $BACKUP_DIR/remote_backup_${timestamp}/
        find $BACKUP_DIR -maxdepth 1 -type d -name 'remote_backup_*' | sort -r | tail -n +6 | xargs -r rm -rf
    "
    
    if eval "$ssh_cmd '$backup_script'" &>/dev/null; then
        print_color $GREEN "Remote backup created"
    else
        print_color $YELLOW "Warning: Remote backup creation failed"
    fi
}

# Function to build rsync command
build_rsync_command() {
    local source=$1
    local dest=$2
    local rsync_cmd="rsync $RSYNC_OPTIONS"
    
    # Add SSH options for remote connections
    if [[ "$source" == *"@"* || "$dest" == *"@"* ]]; then
        local ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        if [[ -n "$SSH_KEY" ]]; then
            ssh_opts="$ssh_opts -i $SSH_KEY"
        fi
        ssh_opts="$ssh_opts -p $REMOTE_PORT"
        rsync_cmd="$rsync_cmd -e 'ssh $ssh_opts'"
    fi
    
    # Add exclude patterns
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        rsync_cmd="$rsync_cmd --exclude='$pattern'"
    done
    
    # Add source and destination
    rsync_cmd="$rsync_cmd $source $dest"
    
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

# Function to sync local to remote (push)
sync_push() {
    print_color $PURPLE "Syncing local to remote (PUSH)..."
    
    # Create remote backup if enabled
    create_remote_backup
    
    # Build and execute rsync command
    local rsync_cmd=$(build_rsync_command "$LOCAL_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/")
    
    print_color $BLUE "Executing rsync command:"
    if [[ "$VERBOSE" = true ]]; then
        echo "$rsync_cmd"
    fi
    
    if eval $rsync_cmd; then
        print_color $GREEN "Push sync completed successfully!"
        print_color $GREEN "Local files synchronized to $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
    else
        print_color $RED "Push sync failed!"
        exit 1
    fi
}

# Function to sync remote to local (pull)
sync_pull() {
    print_color $PURPLE "Syncing remote to local (PULL)..."
    
    # Create local backup if enabled
    create_backup "$LOCAL_DIR" "local_backup"
    
    # Build and execute rsync command
    local rsync_cmd=$(build_rsync_command "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/" "$LOCAL_DIR/")
    
    print_color $BLUE "Executing rsync command:"
    if [[ "$VERBOSE" = true ]]; then
        echo "$rsync_cmd"
    fi
    
    if eval $rsync_cmd; then
        print_color $GREEN "Pull sync completed successfully!"
        print_color $GREEN "Remote files synchronized to $LOCAL_DIR"
    else
        print_color $RED "Pull sync failed!"
        exit 1
    fi
}

# Function to perform bidirectional sync
sync_both() {
    print_color $PURPLE "Performing bidirectional sync (EXPERIMENTAL)..."
    print_color $YELLOW "Warning: This feature is experimental. Use with caution!"
    
    # Create backups
    create_backup "$LOCAL_DIR" "local_backup"
    create_remote_backup
    
    # First, sync newer files from remote to local
    print_color $BLUE "Step 1: Pulling newer files from remote..."
    local pull_cmd=$(build_rsync_command "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/" "$LOCAL_DIR/")
    pull_cmd="$pull_cmd --update"
    
    if eval $pull_cmd; then
        print_color $GREEN "Pull phase completed"
    else
        print_color $RED "Pull phase failed"
        exit 1
    fi
    
    # Then, sync newer files from local to remote
    print_color $BLUE "Step 2: Pushing newer files to remote..."
    local push_cmd=$(build_rsync_command "$LOCAL_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/")
    push_cmd="$push_cmd --update"
    
    if eval $push_cmd; then
        print_color $GREEN "Push phase completed"
    else
        print_color $RED "Push phase failed"
        exit 1
    fi
    
    print_color $GREEN "Bidirectional sync completed successfully!"
}

# Main sync function
sync() {
    local direction=$1
    
    print_color $YELLOW "Starting $direction sync between $LOCAL_DIR and $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
    
    # Test SSH connection
    if ! test_ssh_connection; then
        exit 1
    fi
    
    # Create remote directory
    create_remote_dir
    
    # Perform sync based on direction
    case $direction in
        "push")
            sync_push
            ;;
        "pull")
            sync_pull
            ;;
        "both")
            sync_both
            ;;
        *)
            print_color $RED "Invalid sync direction: $direction"
            exit 1
            ;;
    esac
}

# Parse command line arguments
DRY_RUN=false
VERBOSE=false
DELETE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            SYNC_DIRECTION="push"
            shift
            ;;
        --pull)
            SYNC_DIRECTION="pull"
            shift
            ;;
        --both)
            SYNC_DIRECTION="both"
            shift
            ;;
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
            RSYNC_OPTIONS="$RSYNC_OPTIONS --delete"
            shift
            ;;
        --no-backup)
            BACKUP_ENABLED=false
            shift
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
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
    print_color $BLUE "Unsloth Qwen Fine-tuning Project Sync Script"
    print_color $BLUE "============================================"
    
    # Validate configuration
    validate_config
    
    # Show configuration
    print_color $YELLOW "Configuration:"
    echo "  Sync Direction: $SYNC_DIRECTION"
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
    echo "  Delete: $DELETE"
    echo "  Backup Enabled: $BACKUP_ENABLED"
    if [[ "$BACKUP_ENABLED" = true ]]; then
        echo "  Backup Directory: $BACKUP_DIR"
    fi
    echo ""
    
    # Confirm sync
    if [[ "$DRY_RUN" = false ]]; then
        read -p "Continue with $SYNC_DIRECTION sync? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_color $YELLOW "Sync cancelled"
            exit 0
        fi
    fi
    
    # Start sync
    sync "$SYNC_DIRECTION"
}

# Run main function
main "$@"

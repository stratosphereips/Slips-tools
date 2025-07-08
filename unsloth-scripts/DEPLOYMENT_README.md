# Deployment Scripts Documentation

This document provides comprehensive documentation for the deployment and synchronization scripts in the Unsloth Qwen Fine-tuning Project.

## Overview

This project includes two deployment scripts:

- **`deploy.sh`**: One-way deployment script that syncs local files to a remote server
- **`sync.sh`**: Bidirectional synchronization script that can sync in both directions

Both scripts use `rsync` over SSH and share common configuration options and exclude patterns.

## deploy.sh - One-Way Deployment

### Purpose
The `deploy.sh` script is designed for traditional deployment workflows where you want to push your local development environment to a remote server. It performs a one-way sync from local to remote.

### Key Features
- One-way synchronization (local → remote)
- SSH-based secure transfer
- Configurable exclude patterns
- Dry-run capability
- Progress reporting
- Automatic remote directory creation

### Configuration

Edit the configuration variables at the top of `deploy.sh`:

```bash
REMOTE_HOST="200.12.137.13"     # Target server hostname/IP
REMOTE_PORT="22036"             # SSH port
REMOTE_USER="harpo"             # Remote username
REMOTE_DIR="/home/harpo/unsloth-ex"  # Remote directory path
LOCAL_DIR="$(pwd)"              # Local directory (current by default)
SSH_KEY=""                      # Optional SSH key path
```

### Usage

```bash
# Basic deployment
./deploy.sh

# Deploy with custom settings
./deploy.sh -h server.com -u deploy -d /opt/unsloth-ex

# Dry run to preview changes
./deploy.sh --dry-run --verbose

# Use custom SSH key
./deploy.sh -k ~/.ssh/deploy_key -h 192.168.1.100
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `-h, --host HOST` | Remote host (overrides config) |
| `-p, --port PORT` | SSH port (overrides config) |
| `-u, --user USER` | Remote user (overrides config) |
| `-d, --dir DIR` | Remote directory (overrides config) |
| `-k, --key KEY` | SSH key path |
| `-n, --dry-run` | Show what would be transferred without doing it |
| `-v, --verbose` | Verbose output |
| `--delete` | Delete files on remote that don't exist locally |
| `--help` | Show help message |

## sync.sh - Bidirectional Synchronization

### Purpose
The `sync.sh` script provides flexible bidirectional synchronization capabilities. It can push changes to remote, pull changes from remote, or perform two-way synchronization.

### Key Features
- Three sync directions: push, pull, bidirectional
- Automatic backup creation before sync operations
- Conflict resolution using file timestamps
- All features of deploy.sh plus bidirectional capabilities
- Experimental two-way sync with safety measures

### Sync Directions

#### Push Mode (`--push`)
- Syncs local files to remote server
- Equivalent to `deploy.sh` functionality
- Creates remote backup before sync

#### Pull Mode (`--pull`)
- Syncs remote files to local directory
- Creates local backup before sync
- Useful for pulling updates from remote development

#### Bidirectional Mode (`--both`)
- **Experimental feature**
- Performs two-phase sync using `--update` flag
- Newer files win in case of conflicts
- Creates backups on both sides

### Configuration

Same configuration variables as `deploy.sh`, plus:

```bash
SYNC_DIRECTION="push"    # Default sync direction
BACKUP_ENABLED=true      # Enable/disable backups
BACKUP_DIR=".sync_backups"  # Backup directory name
```

### Usage

```bash
# Push local changes to remote (default)
./sync.sh --push

# Pull remote changes to local
./sync.sh --pull

# Bidirectional sync (experimental)
./sync.sh --both

# Preview bidirectional sync
./sync.sh --both --dry-run

# Pull without creating backup
./sync.sh --pull --no-backup

# Use custom backup directory
./sync.sh --push --backup-dir .my_backups
```

### Command-Line Options

All options from `deploy.sh` plus:

| Option | Description |
|--------|-------------|
| `--push` | Push changes from local to remote (default) |
| `--pull` | Pull changes from remote to local |
| `--both` | Bidirectional sync (experimental) |
| `--no-backup` | Disable backup before sync |
| `--backup-dir DIR` | Custom backup directory |

## Common Configuration

### SSH Setup

Both scripts require SSH access to the remote server. Ensure:

1. SSH key authentication is configured (recommended)
2. The remote server is accessible on the specified port
3. The remote user has write permissions to the target directory

### Exclude Patterns

Both scripts exclude the following patterns by default:

```bash
# Version control and build artifacts
.git/
*.pyc
__pycache__/
build/
dist/

# Virtual environments
.venv/
venv/

# Model files and datasets
qwen_finetuned/
*.model
*.bin
*.safetensors
mixed_dataset.json
prepared_dataset.json

# ML experiment tracking
wandb/
checkpoints/

# Temporary files
*.tmp
*.swp
*.log
```

### Security Considerations

1. **SSH Keys**: Use SSH key authentication instead of passwords
2. **Backup Verification**: Always verify backups before performing destructive operations
3. **Dry Run**: Use `--dry-run` to preview changes before actual sync
4. **Host Key Verification**: Scripts disable strict host key checking for automation

## Backup System (sync.sh only)

### Local Backups
- Created in `LOCAL_DIR/.sync_backups/`
- Timestamped directories: `local_backup_YYYYMMDD_HHMMSS`
- Automatically keeps last 5 backups
- Excludes files matching the exclude patterns

### Remote Backups
- Created in `REMOTE_DIR/.sync_backups/`
- Timestamped directories: `remote_backup_YYYYMMDD_HHMMSS`
- Automatically keeps last 5 backups
- Created via SSH commands before sync operations

### Backup Management
```bash
# Disable backups
./sync.sh --pull --no-backup

# Custom backup directory
./sync.sh --push --backup-dir .my_backups

# Backups are automatically cleaned up (keeps last 5)
```

## Examples

### Development Workflow with deploy.sh

```bash
# Deploy to staging
./deploy.sh -h staging.example.com -u deploy -d /var/www/unsloth-ex

# Deploy to production with dry run first
./deploy.sh -h prod.example.com --dry-run
./deploy.sh -h prod.example.com
```

### Bidirectional Development with sync.sh

```bash
# Work on local machine, push changes
./sync.sh --push

# Pull updates from remote development
./sync.sh --pull

# Sync both ways (experimental)
./sync.sh --both --dry-run  # Preview first
./sync.sh --both            # Execute
```

### Multi-Environment Setup

```bash
# Deploy to multiple environments
./deploy.sh -h dev.example.com -u deploy -d /opt/unsloth-ex
./deploy.sh -h staging.example.com -u deploy -d /opt/unsloth-ex
./deploy.sh -h prod.example.com -u deploy -d /opt/unsloth-ex
```

## Troubleshooting

### SSH Connection Issues

**Problem**: SSH connection failed
```bash
# Test SSH connection manually
ssh -p 22036 harpo@200.12.137.13

# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

**Problem**: Permission denied
```bash
# Add SSH key to ssh-agent
ssh-add ~/.ssh/id_rsa

# Verify SSH key is added to remote authorized_keys
ssh-copy-id -p 22036 harpo@200.12.137.13
```

### Rsync Issues

**Problem**: Files not syncing as expected
```bash
# Use dry-run with verbose output
./sync.sh --pull --dry-run --verbose

# Check exclude patterns
./sync.sh --pull --verbose | grep "excluding"
```

**Problem**: Large files causing timeouts
```bash
# Use rsync with resume capability
# Edit RSYNC_OPTIONS in the script to add --partial
RSYNC_OPTIONS="-avz --partial --progress"
```

### Remote Directory Issues

**Problem**: Remote directory doesn't exist
- Scripts automatically create remote directories
- Ensure remote user has write permissions to parent directory

**Problem**: Insufficient disk space
```bash
# Check remote disk space
ssh -p 22036 harpo@200.12.137.13 'df -h'

# Check local disk space
df -h
```

### Backup Issues

**Problem**: Backup creation fails
```bash
# Check disk space in backup directory
du -sh .sync_backups/

# Manually clean old backups
rm -rf .sync_backups/old_backup_*

# Disable backups temporarily
./sync.sh --pull --no-backup
```

## Best Practices

1. **Always test with --dry-run first** before actual deployment
2. **Use version control** for your local files
3. **Verify backups** before destructive operations
4. **Use SSH keys** instead of password authentication
5. **Monitor disk space** on both local and remote systems
6. **Keep exclude patterns updated** to avoid syncing unnecessary files
7. **Test scripts** in a development environment first

## Script Maintenance

To customize the scripts for your environment:

1. Edit configuration variables at the top of each script
2. Modify exclude patterns as needed
3. Adjust rsync options for your specific requirements
4. Add environment-specific validation or preprocessing steps

For advanced customization, refer to the rsync and SSH manual pages:
- `man rsync`
- `man ssh`
- `man ssh-keygen`
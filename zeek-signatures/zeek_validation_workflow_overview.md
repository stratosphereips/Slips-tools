# Zeek Signature Validation Workflow

## Overview

The Zeek signature validation workflow provides a comprehensive Docker-based environment for testing and validating Zeek network security signatures. The system combines containerized Zeek deployment with automated validation scripts to ensure signature syntax correctness and functional testing against network traffic.

## Architecture

### Docker Environment
- **Base Image**: Ubuntu 22.04 with official Zeek installation
- **Repository**: Uses OpenSUSE security repository for latest Zeek builds
- **Environment**: Isolated container with Zeek binaries in PATH (`/opt/zeek/bin`)
- **Volumes**: Bind-mounted signature directory and test data for seamless workflow

### Validation Components

#### Core Validation Script (`validate_zeek_sig.sh`)
- **Syntax Validation**: Uses `zeek --parse-only` for signature syntax verification
- **Traffic Testing**: Tests signatures against PCAP files with `zeek -r`
- **Temporary Workspace**: Creates isolated working directory for each validation run
- **Comprehensive Logging**: Reports parsing results, log generation, and signature matches

#### Docker Configuration
```yaml
services:
  zeek-validator:
    volumes:
      - .:/signatures        # Current directory as signature workspace  
      - ./test_data:/test_data:ro  # Read-only PCAP test data
    working_dir: /signatures
    environment:
      - TERM=xterm-256color   # Enhanced terminal support
```

## Validation Workflow

### Phase 1: Environment Setup
1. **Container Initialization**: `docker-compose up -d` starts the Zeek validator service
2. **Zeek Installation**: Automated installation of latest Zeek from official repository
3. **Path Configuration**: Zeek binaries available globally in container environment
4. **Volume Mounting**: Signature files and test data accessible from container

### Phase 2: Syntax Validation
1. **Signature Loading**: Creates temporary Zeek script with `@load-sigs` directive
2. **Parse-Only Check**: Executes `zeek --parse-only` to validate signature syntax
3. **Error Reporting**: Captures and displays detailed parsing errors if validation fails
4. **Immediate Feedback**: Returns validation status with clear ✓/✗ indicators

### Phase 3: Functional Testing (Optional)
1. **PCAP Processing**: Tests signature against provided network traffic capture
2. **Zeek Execution**: Runs full Zeek analysis with `zeek -r <pcap> <signature>`
3. **Log Analysis**: Examines generated log files for signature effectiveness
4. **Match Reporting**: Displays signature matches from `signatures.log` if present

### Phase 4: Results Analysis
1. **Log File Summary**: Reports all generated log files with line counts
2. **Match Detection**: Highlights successful signature triggers in traffic
3. **Performance Feedback**: Indicates if signature processed without errors
4. **Cleanup**: Automatic temporary file cleanup after validation

## Usage Patterns

### Basic Syntax Validation
```bash
# Enter validation environment
docker-compose exec zeek-validator bash

# Validate signature syntax only  
./validate_zeek_sig.sh test_signature.sig
```

### Traffic-Based Testing
```bash
# Test signature against network capture
./validate_zeek_sig.sh malware_sig.sig test_data/sample.pcap

# Test with multiple PCAP files
for pcap in test_data/*.pcap; do
    ./validate_zeek_sig.sh signature.sig "$pcap"
done
```

### Direct Command Usage
```bash
# External validation without entering container
docker-compose exec -T zeek-validator /signatures/validate_zeek_sig.sh /signatures/test_signature.sig
```

## Validation Outputs

### Success Indicators
- **✓ Signature syntax is valid**: Signature parses correctly without errors
- **✓ Signature processed successfully**: Signature executed against traffic without issues
- **Generated log files**: Lists all Zeek log files created during processing
- **Signature matches found**: Displays actual matches from `signatures.log`

### Error Indicators
- **✗ Signature syntax error**: Detailed parsing error messages from Zeek
- **✗ Error processing signature with traffic**: Runtime errors during PCAP analysis
- **File not found errors**: Missing signature or PCAP files
- **No signature matches**: Signature loaded but no matches in provided traffic

## Directory Structure

```
zeek-signatures/
├── validate_zeek_sig.sh          # Main validation script
├── docker-compose.yml            # Container orchestration
├── Dockerfile                    # Zeek environment definition  
├── test_signature.sig            # Example signature for testing
├── test_data/                    # PCAP files for functional testing
│   ├── sample.pcap              
│   └── malware_traffic.pcap
├── README.md                     # Usage documentation
└── signatures/                   # Generated or user signatures
    ├── generated_sigs.json
    └── variations.sig
```

## Integration Points

### With Signature Generators
- **Dataset Generator**: Validate generated signatures from `generate_zeek_signature_dataset.py`
- **Variation Generator**: Test signature variations from `vary_zeek_signature.py`
- **Batch Validation**: Process multiple signatures efficiently in containerized environment

### Development Workflow
1. **Generate** signatures using LLM-based tools
2. **Validate** syntax using Docker environment  
3. **Test** against representative traffic samples
4. **Iterate** based on validation feedback
5. **Deploy** validated signatures to production systems

## Quality Assurance Features

### Comprehensive Error Handling
- **File Existence Checks**: Validates signature and PCAP file availability
- **Syntax Error Capture**: Detailed Zeek parser error messages
- **Runtime Error Detection**: Catches processing failures during traffic analysis
- **Graceful Cleanup**: Ensures temporary files are removed regardless of outcome

### Automated Reporting
- **Structured Output**: Clear success/failure indicators with detailed context
- **Log File Analysis**: Automatic inspection of generated Zeek logs
- **Match Visualization**: Displays signature detection results from traffic
- **Performance Metrics**: Reports on signature processing efficiency

### Isolation Benefits
- **Clean Environment**: Each validation runs in pristine Zeek installation
- **No Side Effects**: Temporary workspace prevents interference between tests
- **Reproducible Results**: Consistent validation environment across different systems
- **Version Control**: Pinned Zeek version ensures consistent behavior
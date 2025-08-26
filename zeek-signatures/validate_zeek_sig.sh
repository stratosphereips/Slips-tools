#!/bin/bash

# Simple Zeek signature validator
# Usage: validate_zeek_sig.sh <signature_file> [pcap_file] [--keep-temp]

set -e

KEEP_TEMP=false

if [ $# -lt 1 ]; then
    echo "Usage: $0 <signature_file> [pcap_file] [--keep-temp]"
    echo "Examples:"
    echo "  $0 my_signature.sig                    # syntax check only"
    echo "  $0 my_signature.sig sample.pcap        # test against traffic"
    echo "  $0 my_signature.sig --keep-temp        # keep temporary files"
    echo "  $0 my_signature.sig sample.pcap --keep-temp  # test and keep files"
    exit 1
fi

# Parse arguments
for arg in "$@"; do
    case $arg in
        --keep-temp)
            KEEP_TEMP=true
            shift
            ;;
    esac
done

SIGNATURE_FILE="$1"
PCAP_FILE="$2"

if [ ! -f "$SIGNATURE_FILE" ]; then
    echo "Error: Signature file '$SIGNATURE_FILE' not found"
    exit 1
fi

echo "Validating signature: $SIGNATURE_FILE"

# Create temporary working directory
WORK_DIR=$(mktemp -d)
cd "$WORK_DIR"

# Copy signature file
cp "$SIGNATURE_FILE" ./signature.sig

# Create Zeek script to load the signature
cat > load_sig.zeek << 'EOF'
@load base/frameworks/signatures
@load-sigs ./signature.sig
EOF

# Syntax check
echo "Checking syntax..."
if zeek --parse-only load_sig.zeek >/dev/null 2>&1; then
    echo "✓ Signature syntax is valid"
else
    echo "✗ Signature syntax error:"
    zeek --parse-only load_sig.zeek
    cd - >/dev/null
    if [ "$KEEP_TEMP" = false ]; then
        rm -rf "$WORK_DIR"
    else
        echo "Temporary files kept in: $WORK_DIR"
    fi
    exit 1
fi

# Test with PCAP if provided
if [ -n "$PCAP_FILE" ]; then
    if [ ! -f "$PCAP_FILE" ]; then
        echo "Error: PCAP file '$PCAP_FILE' not found"
        cd - >/dev/null
        if [ "$KEEP_TEMP" = false ]; then
            rm -rf "$WORK_DIR"
        else
            echo "Temporary files kept in: $WORK_DIR"
        fi
        exit 1
    fi
    
    echo "Testing signature against traffic: $PCAP_FILE"
    
    if zeek -r "$PCAP_FILE" load_sig.zeek >/dev/null 2>&1; then
        echo "✓ Signature processed successfully"
        
        # Show generated log files
        if ls *.log >/dev/null 2>&1; then
            echo ""
            echo "Generated log files:"
            for log in *.log; do
                if [ -s "$log" ]; then
                    echo "  $log ($(wc -l < "$log") lines)"
                else
                    echo "  $log (empty)"
                fi
            done
        fi
        
        # Show signature matches
        if [ -f "signatures.log" ] && [ -s "signatures.log" ]; then
            echo ""
            echo "Signature matches found:"
            cat signatures.log
        else
            echo "No signature matches in the traffic"
        fi
    else
        echo "✗ Error processing signature with traffic:"
        zeek -r "$PCAP_FILE" load_sig.zeek
        cd - >/dev/null
        if [ "$KEEP_TEMP" = false ]; then
            rm -rf "$WORK_DIR"
        else
            echo "Temporary files kept in: $WORK_DIR"
        fi
        exit 1
    fi
else
    echo "No PCAP file provided - syntax check only"
fi

# Cleanup
cd - >/dev/null
if [ "$KEEP_TEMP" = true ]; then
    echo "Temporary files kept in: $WORK_DIR"
else
    rm -rf "$WORK_DIR"
fi

echo "Validation complete!"
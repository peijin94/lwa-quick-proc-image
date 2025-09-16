#!/bin/bash
# Minimal script to run DP3 gain calibration
# Usage: ./gaincal.sh input.ms [output.ms] [solint] [caltype]

INPUT_MS="$1"
OUTPUT_MS="$2"
SOLINT="${3:-0}"
CALTYPE="${4:-gain}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_ms> [output_ms] [solint] [caltype]"
    echo "Examples:"
    echo "  $0 /path/to/data.ms"
    echo "  $0 /path/to/data.ms calibrated.ms"
    echo "  $0 /path/to/data.ms calibrated.ms 0 gain"
    echo ""
    echo "Parameters:"
    echo "  solint: Solution interval (0=per scan, 1=per timestep, default: 0)"
    echo "  caltype: gain, phase, or bandpass (default: gain)"
    exit 1
fi

if [ ! -d "$INPUT_MS" ]; then
    echo "Error: Input measurement set not found: $INPUT_MS"
    exit 1
fi

# Set output MS name if not provided
if [ -z "$OUTPUT_MS" ]; then
    OUTPUT_MS="$(dirname "$INPUT_MS")/$(basename "$INPUT_MS" .ms)_cal.ms"
fi

echo "Running DP3 gain calibration..."
echo "Input: $INPUT_MS"
echo "Output: $OUTPUT_MS"
echo "Solution interval: $SOLINT (0=per scan)"
echo "Calibration type: $CALTYPE"

# Create temporary parset file
PARSET_FILE="gaincal_$$.parset"

cat > "$PARSET_FILE" << EOF
msin = /data/$(basename "$INPUT_MS")
msout = /data/$(basename "$OUTPUT_MS")
msout.writefullresflag = true

steps = [cal]

cal.type = gaincal
cal.solint = $SOLINT
cal.caltype = diagonal
cal.uvlambdamin = 10
cal.applysmoothness = true
cal.smoothnessconstraint = 0.1
cal.soltype = LBFGS
cal.maxiter = 100
cal.tolerance = 1e-3
cal.usemodelcolumn = true
cal.modelcolumn = MODEL_DATA
EOF

echo "Running DP3 gain calibration..."

# Run DP3 via podman
podman run --rm \
    -v "$(dirname "$INPUT_MS"):/data" \
    -v "$(pwd):/config" \
    -w "/config" \
    astronrd/linc:latest \
    DP3 "/config/$PARSET_FILE"

if [ $? -eq 0 ]; then
    echo "DP3 gain calibration completed successfully!"
    # Check for output MS in the same directory as input
    FULL_OUTPUT_PATH="$(dirname "$INPUT_MS")/$(basename "$OUTPUT_MS")"
    if [ -d "$FULL_OUTPUT_PATH" ]; then
        echo "Calibrated MS created: $FULL_OUTPUT_PATH"
    else
        echo "Warning: Output MS not found at $FULL_OUTPUT_PATH"
    fi
else
    echo "DP3 gain calibration failed!"
    rm -f "$PARSET_FILE"
    exit 1
fi

# Clean up
rm -f "$PARSET_FILE"
echo "Done!"

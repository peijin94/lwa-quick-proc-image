#!/bin/bash
# Minimal script to run DP3 with aoflagger and frequency averaging
# Usage: ./dp3_flag_avg.sh input.ms output.ms

INPUT_MS="$1"
OUTPUT_MS="$2"

if [ $# -ne 2 ]; then
    echo "Usage: $0 <input_ms> <output_ms>"
    echo "Example: $0 /path/to/input.ms /path/to/output.ms"
    exit 1
fi

if [ ! -d "$INPUT_MS" ]; then
    echo "Error: Input measurement set not found: $INPUT_MS"
    exit 1
fi

# Create temporary parset file
PARSET_FILE="dp3_flag_avg_$$.parset"

cat > "$PARSET_FILE" << EOF
msin.type = ms
msin.name = /data/$(basename "$INPUT_MS")

msout.type = ms
msout.name = /data/$(basename "$OUTPUT_MS")
msout.writefullresflag = true

steps = [flag, avg]

# Aoflagger step with default strategy
flag.type = aoflagger
flag.strategy = /usr/local/share/linc/rfistrategies/lofar-default.lua

# Frequency averaging step - average every 3 channels
avg.type = averager
avg.freqstep = 3
EOF

echo "Running DP3 with aoflagger and frequency averaging..."
echo "Input: $INPUT_MS"
echo "Output: $OUTPUT_MS"

# Run DP3 via podman
podman run --rm \
    -v "$(dirname "$INPUT_MS"):/data" \
    -v "$(dirname "$OUTPUT_MS"):/data" \
    -v "$(pwd):/config" \
    astronrd/linc:latest \
    DP3 "/config/$PARSET_FILE"

# Clean up
rm -f "$PARSET_FILE"

echo "Done!"

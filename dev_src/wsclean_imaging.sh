#!/bin/bash
# Minimal script to run wsclean imaging with optimized LWA parameters
# Usage: ./wsclean_imaging.sh input.ms [output_prefix]

INPUT_MS="$1"
OUTPUT_PREFIX="${2:-image}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_ms> [output_prefix]"
    echo "Example: $0 /fast/peijinz/agile_proc/testdata/slow/flagged_avg.ms lwa_image"
    exit 1
fi

if [ ! -d "$INPUT_MS" ]; then
    echo "Error: Input measurement set not found: $INPUT_MS"
    exit 1
fi

echo "Running wsclean imaging..."
echo "Input: $INPUT_MS"
echo "Output prefix: $OUTPUT_PREFIX"
echo "Image size: 4096x4096"

# Run wsclean via podman with optimized LWA parameters
podman run --rm \
    -v "$(dirname "$INPUT_MS"):/data" \
    -w "/data" \
    astronrd/linc:latest \
    wsclean \
    -size 4096 4096 \
    -scale 2arcmin \
    -name "$OUTPUT_PREFIX" \
    -j 8 \
    -mem 2 \
    -weight uniform \
    -no-dirty \
    -no-update-model-required \
    -no-negative \
    -niter 1000 \
    -mgain 0.9 \
    -auto-threshold 3 \
    -auto-mask 8 \
    -pol I \
    -minuv-l 10 \
    -intervals-out 1 \
    -no-reorder \
    -beam-fitting-size 2 \
    -horizon-mask 2deg \
    -quiet \
    "/data/$(basename "$INPUT_MS")"

if [ $? -eq 0 ]; then
    echo "WSClean imaging completed successfully!"
    echo ""
    echo "Generated files in $(dirname "$INPUT_MS"):"
    ls -la "$(dirname "$INPUT_MS")/${OUTPUT_PREFIX}"*.fits 2>/dev/null | awk '{print "  " $9}'
else
    echo "WSClean imaging failed!"
    exit 1
fi

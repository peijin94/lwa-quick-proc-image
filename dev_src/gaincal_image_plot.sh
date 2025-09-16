#!/bin/bash
# Complete pipeline: gain calibration -> imaging -> plotting
# Usage: ./gaincal_image_plot.sh input.ms [output_prefix]

INPUT_MS="$1"
OUTPUT_PREFIX="${2:-calibrated}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_ms> [output_prefix]"
    echo "Examples:"
    echo "  $0 /path/to/data.ms"
    echo "  $0 /path/to/data.ms my_result"
    echo ""
    echo "This script runs the complete pipeline:"
    echo "  1. Gain calibration (assumes MODEL_DATA is filled)"
    echo "  2. WSClean imaging on calibrated data"
    echo "  3. Plotting of resulting FITS images"
    exit 1
fi

if [ ! -d "$INPUT_MS" ]; then
    echo "Error: Input measurement set not found: $INPUT_MS"
    exit 1
fi

# Check if required scripts exist
REQUIRED_SCRIPTS=("gaincal.sh" "wsclean_imaging.sh" "plot_fits.py" "plot_solutions.py")
for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        echo "Error: Missing required script: $script"
        exit 1
    fi
done

echo "============================================================"
echo "STEP 1: Running gain calibration..."
echo "============================================================"

# Step 1: Run gain calibration
CAL_MS="$(dirname "$INPUT_MS")/${OUTPUT_PREFIX}_cal.ms"

./gaincal.sh "$INPUT_MS" "$CAL_MS"

if [ $? -ne 0 ]; then
    echo "✗ Gain calibration failed!"
    exit 1
fi

echo "✓ Gain calibration completed: $CAL_MS"

echo ""
echo "============================================================"
echo "STEP 2: Running wsclean imaging..."
echo "============================================================"

# Step 2: Run wsclean imaging on calibrated data
IMAGE_PREFIX="${OUTPUT_PREFIX}_image"

./wsclean_imaging.sh "$CAL_MS" "$IMAGE_PREFIX"

if [ $? -ne 0 ]; then
    echo "✗ WSClean imaging failed!"
    exit 1
fi

echo "✓ WSClean imaging completed with prefix: $IMAGE_PREFIX"

echo ""
echo "============================================================"
echo "STEP 3: Plotting gain solutions..."
echo "============================================================"

# Step 3a: Plot gain solutions if solution.h5 exists
SOLUTION_FILE="$(dirname "$INPUT_MS")/solution.h5"
if [ -f "$SOLUTION_FILE" ]; then
    python3 plot_solutions.py "$SOLUTION_FILE"
    
    if [ $? -ne 0 ]; then
        echo "✗ Gain solution plotting failed"
    else
        echo "✓ Gain solution plotting completed"
    fi
else
    echo "ℹ️  No solution.h5 file found, skipping gain solution plots"
fi

echo ""
echo "============================================================"
echo "STEP 4: Plotting FITS images..."
echo "============================================================"

# Step 4: Plot the resulting FITS images
python3 plot_fits.py "$(dirname "$INPUT_MS")/$IMAGE_PREFIX"

if [ $? -ne 0 ]; then
    echo "✗ FITS plotting failed (may require matplotlib/astropy)"
else
    echo "✓ FITS plotting completed"
fi

echo ""
echo "============================================================"
echo "PIPELINE COMPLETED SUCCESSFULLY!"
echo "============================================================"

# Show generated files
echo ""
echo "Generated files in $(dirname "$INPUT_MS"):"

# List calibrated MS
if [ -d "$CAL_MS" ]; then
    echo "  📁 Calibrated MS: $(basename "$CAL_MS")"
fi

# List FITS and PNG files
ls -1 "$(dirname "$INPUT_MS")/${IMAGE_PREFIX}"*.fits 2>/dev/null | while read file; do
    echo "  🖼️  FITS: $(basename "$file")"
done

ls -1 "$(dirname "$INPUT_MS")/${IMAGE_PREFIX}"*.png 2>/dev/null | while read file; do
    echo "  📊 Plot: $(basename "$file")"
done

echo ""
echo "Pipeline completed successfully!"

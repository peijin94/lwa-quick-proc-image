#!/bin/bash
# Simple GNU Parallel script to process MS files
# This version uses a more direct approach

# Set up paths
DATA_DIR="/fast/peijinz/agile_proc/testdata_v4"
SLOW_DIR="${DATA_DIR}/slow"
CALTABLE_DIR="${DATA_DIR}/caltables"

# Create logs directory
mkdir -p "${DATA_DIR}/logs"

# Create a function that parallel can call
process_ms() {
    local ms_file="$1"
    local freq=$(echo "$ms_file" | grep -o '[0-9]\+MHz' | head -1)
    local base_name=$(basename "$ms_file" .ms)
    local start_time=$(date +%s)
    
    echo "Processing $ms_file (${freq})..."
    
    podman run --rm \
        -v /fast/peijinz/agile_proc/lwa-quick-proc-image:/lwasoft:ro \
        -v /fast/peijinz/agile_proc/testdata_v4:/data:rw \
        -w /data \
        peijin/lwa-solar-pipehost:v202510 \
        python3 /lwasoft/pipeline_quick_proc_img.py \
            "/data/slow/$ms_file" \
            "/data/caltables/20250920_041508_${freq}.bcal" \
        >> "${DATA_DIR}/logs/${base_name}.log" 2>&1
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Add completion timestamp to log file
    echo "=================================" >> "${DATA_DIR}/logs/${base_name}.log"
    echo "=== Processing completed at $(date) ===" >> "${DATA_DIR}/logs/${base_name}.log"
    echo "=== Duration: ${duration}s ===" >> "${DATA_DIR}/logs/${base_name}.log"
    echo "Completed $ms_file in ${duration}s"
}

# Export function for parallel
export -f process_ms
export DATA_DIR SLOW_DIR CALTABLE_DIR

# Record overall start time
SCRIPT_START_TIME=$(date +%s)

# Get list of MS files and run in parallel
ls "${SLOW_DIR}" | grep "\.ms$" | \
parallel -j 12 --progress --line-buffer process_ms {}

# Calculate total execution time
SCRIPT_END_TIME=$(date +%s)
SCRIPT_DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))

echo "---------------------------------"
echo "Total time: ${SCRIPT_DURATION}s"
echo "Logs: ${DATA_DIR}/logs/"

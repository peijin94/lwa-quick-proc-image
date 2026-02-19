#!/bin/bash
# Simple GNU Parallel script to process MS files
# This version uses a more direct approach

set -euo pipefail

# Set up paths
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPEDEV_DIR="$(cd "${REPO_DIR}/.." && pwd)"
SLOW_DIR="${PIPEDEV_DIR}/slow_data"
CALTABLE_DIR="${PIPEDEV_DIR}/caltables_latest"
LOG_DIR="${PIPEDEV_DIR}/runtime_dir/parallel_logs"

# Create logs directory
mkdir -p "${LOG_DIR}"

if ! command -v podman >/dev/null 2>&1; then
    echo "podman is required but not found in PATH"
    exit 1
fi

if ! command -v parallel >/dev/null 2>&1; then
    echo "GNU parallel is required but not found in PATH"
    exit 1
fi

if command -v conda >/dev/null 2>&1; then
    if ! conda env list | awk '{print $1}' | grep -qx "lwa"; then
        echo "conda environment 'lwa' not found"
        exit 1
    fi
fi

if [ ! -d "${SLOW_DIR}" ] || [ ! -d "${CALTABLE_DIR}" ]; then
    echo "Expected directories not found: ${SLOW_DIR} and/or ${CALTABLE_DIR}"
    exit 1
fi

# Create a function that parallel can call
process_ms() {
    local ms_file="$1"
    local freq=$(echo "$ms_file" | grep -o '[0-9]\+MHz' | head -1)
    local base_name=$(basename "$ms_file" .ms)
    local caltable_file=$(ls "${CALTABLE_DIR}"/*_"${freq}".bcal 2>/dev/null | sort | tail -1)
    local start_time=$(date +%s)
    
    if [ -z "${caltable_file}" ]; then
        echo "No caltable found for ${freq}, skipping ${ms_file}"
        return 0
    fi

    echo "Processing $ms_file (${freq})..."
    
    podman run --rm \
        -v "${REPO_DIR}:/lwasoft:ro" \
        -v "${PIPEDEV_DIR}:/workspace:rw" \
        -w /workspace \
        peijin/lwa-solar-pipehost:v202510 \
        python3 /lwasoft/pipeline_quick_proc_img.py \
            "/workspace/slow_data/$ms_file" \
            "/workspace/caltables_latest/$(basename "${caltable_file}")" \
        >> "${LOG_DIR}/${base_name}.log" 2>&1
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Add completion timestamp to log file
    echo "=================================" >> "${LOG_DIR}/${base_name}.log"
    echo "=== Processing completed at $(date) ===" >> "${LOG_DIR}/${base_name}.log"
    echo "=== Duration: ${duration}s ===" >> "${LOG_DIR}/${base_name}.log"
    echo "Completed $ms_file in ${duration}s"
}

# Export function for parallel
export -f process_ms
export REPO_DIR PIPEDEV_DIR SLOW_DIR CALTABLE_DIR LOG_DIR

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
echo "Logs: ${LOG_DIR}/"

#!/bin/bash
# Simple wrapper script to run the self-calibration pipeline

# Default values
MS_PATH="/fast/peijinz/agile_proc/testdata/slow/20240519_173002_55MHz.ms"
OUTPUT_DIR="./selfcal_output"
ITERATIONS=""
LOG_LEVEL="INFO"
CONFIG_FILE="selfcal_config.yml"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ms-path)
            MS_PATH="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --ms-path PATH      Path to measurement set (default: $MS_PATH)"
            echo "  --output-dir DIR    Output directory (default: $OUTPUT_DIR)"
            echo "  --iterations N      Number of self-cal iterations (overrides config file)"
            echo "  --log-level LEVEL  Log level: DEBUG, INFO, WARNING, ERROR (default: $LOG_LEVEL)"
            echo "  --config FILE      Path to YAML configuration file (default: $CONFIG_FILE)"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1. Use --help for usage information."
            exit 1
            ;;
    esac
done

# Check if MS file exists
if [[ ! -d "$MS_PATH" ]]; then
    echo "Error: Measurement set not found: $MS_PATH"
    exit 1
fi

# Check if podman is available
if ! command -v podman &> /dev/null; then
    echo "Error: podman is not installed. Please install podman first."
    exit 1
fi

echo "Starting self-calibration pipeline..."
echo "Input MS: $MS_PATH"
echo "Output directory: $OUTPUT_DIR"
echo "Iterations: ${ITERATIONS:-from config file}"
echo "Log level: $LOG_LEVEL"
echo "Config file: $CONFIG_FILE"
echo ""

# Run the Python pipeline
PYTHON_CMD="python3 selfcal_pipeline.py \"$MS_PATH\" --output-dir \"$OUTPUT_DIR\" --log-level \"$LOG_LEVEL\" --config \"$CONFIG_FILE\""

# Add iterations parameter only if specified
if [[ -n "$ITERATIONS" ]]; then
    PYTHON_CMD="$PYTHON_CMD --iterations \"$ITERATIONS\""
fi

eval $PYTHON_CMD

# Check exit status
if [[ $? -eq 0 ]]; then
    echo "Self-calibration pipeline completed successfully!"
    echo "Results are available in: $OUTPUT_DIR"
else
    echo "Self-calibration pipeline failed!"
    exit 1
fi

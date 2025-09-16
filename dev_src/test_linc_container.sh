#!/bin/bash
"""
Test script for the astronrd/linc container
Verifies that DP3 and wsclean are available and working
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}[PASS]${NC} $message"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}[FAIL]${NC} $message"
    else
        echo -e "${YELLOW}[INFO]${NC} $message"
    fi
}

# Track test results
PASS_COUNT=0
FAIL_COUNT=0

echo "=== Testing astronrd/linc Container ==="
echo ""

# Check if podman is available
echo "1. Checking podman installation..."
if command -v podman &> /dev/null; then
    PODMAN_VERSION=$(podman --version)
    print_status "PASS" "Podman found: $PODMAN_VERSION"
    ((PASS_COUNT++))
else
    print_status "FAIL" "Podman not found. Please install podman first."
    ((FAIL_COUNT++))
fi

# Check podman daemon
echo ""
echo "2. Checking podman daemon..."
if podman info &> /dev/null; then
    print_status "PASS" "Podman daemon is running"
    ((PASS_COUNT++))
else
    print_status "FAIL" "Podman daemon is not running"
    ((FAIL_COUNT++))
fi

# Pull the astronrd/linc image
echo ""
echo "3. Pulling astronrd/linc container image..."
if podman pull astronrd/linc:latest; then
    print_status "PASS" "Successfully pulled astronrd/linc:latest"
    ((PASS_COUNT++))
else
    print_status "FAIL" "Failed to pull astronrd/linc:latest"
    ((FAIL_COUNT++))
fi

# Test basic container functionality and timing
echo ""
echo "4. Testing basic container functionality and startup time..."
echo "   Starting container test..."
START_TIME=$(date +%s.%N)
if podman run --rm astronrd/linc:latest echo "Hello from LINC!" &> /dev/null; then
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "PASS" "Container can run basic commands (${DURATION}s)"
    ((PASS_COUNT++))
else
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "FAIL" "Container cannot run basic commands (${DURATION}s)"
    ((FAIL_COUNT++))
fi

# Test DP3 availability and timing
echo ""
echo "5. Testing DP3 availability and performance..."
echo "   Starting DP3 test..."
START_TIME=$(date +%s.%N)
if podman run --rm astronrd/linc:latest DP3 --version &> /dev/null; then
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    DP3_VERSION=$(podman run --rm astronrd/linc:latest DP3 --version 2>/dev/null | head -1)
    print_status "PASS" "DP3 found: $DP3_VERSION (${DURATION}s)"
    ((PASS_COUNT++))
else
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "FAIL" "DP3 not found in container (${DURATION}s)"
    ((FAIL_COUNT++))
fi

# Test wsclean availability and timing
echo ""
echo "6. Testing wsclean availability and performance..."
echo "   Starting wsclean test..."
START_TIME=$(date +%s.%N)
if podman run --rm astronrd/linc:latest wsclean --version &> /dev/null; then
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    WSCLEAN_VERSION=$(podman run --rm astronrd/linc:latest wsclean --version 2>/dev/null | head -1)
    print_status "PASS" "Wsclean found: $WSCLEAN_VERSION (${DURATION}s)"
    ((PASS_COUNT++))
else
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "FAIL" "Wsclean not found in container (${DURATION}s)"
    ((FAIL_COUNT++))
fi

# Test volume mounting and timing
echo ""
echo "7. Testing volume mounting and performance..."
echo "   Starting volume mount test..."
TEST_FILE="test_linc_mount.txt"
echo "test content for LINC container" > "$TEST_FILE"

START_TIME=$(date +%s.%N)
if podman run --rm -v "$(pwd):/data" astronrd/linc:latest cat "/data/$TEST_FILE" &> /dev/null; then
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "PASS" "Volume mounting works correctly (${DURATION}s)"
    ((PASS_COUNT++))
else
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "FAIL" "Volume mounting failed (${DURATION}s)"
    ((FAIL_COUNT++))
fi

# Clean up test file
rm -f "$TEST_FILE"

# Test working directory and timing
echo ""
echo "8. Testing working directory and performance..."
echo "   Starting working directory test..."
START_TIME=$(date +%s.%N)
if podman run --rm -w /workspace -v "$(pwd):/workspace" astronrd/linc:latest sh -c "pwd && ls -la" &> /dev/null; then
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "PASS" "Working directory setup works correctly (${DURATION}s)"
    ((PASS_COUNT++))
else
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
    print_status "FAIL" "Working directory setup failed (${DURATION}s)"
    ((FAIL_COUNT++))
fi

# Test with actual data directory if it exists
echo ""
echo "9. Testing with testdata directory and performance..."
if [ -d "/fast/peijinz/agile_proc/testdata" ]; then
    echo "   Starting data access test..."
    START_TIME=$(date +%s.%N)
    if podman run --rm -v "/fast/peijinz/agile_proc/testdata:/data" astronrd/linc:latest ls -la /data &> /dev/null; then
        END_TIME=$(date +%s.%N)
        DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
        print_status "PASS" "Can access testdata directory from container (${DURATION}s)"
        ((PASS_COUNT++))
        
        # Check if MS file exists
        if [ -d "/fast/peijinz/agile_proc/testdata/slow/20240519_173002_55MHz.ms" ]; then
            print_status "PASS" "Measurement set found: /fast/peijinz/agile_proc/testdata/slow/20240519_173002_55MHz.ms"
            ((PASS_COUNT++))
        else
            print_status "INFO" "Measurement set not found at expected location"
        fi
    else
        END_TIME=$(date +%s.%N)
        DURATION=$(echo "$END_TIME - $START_TIME" | bc -l)
        print_status "FAIL" "Cannot access testdata directory from container (${DURATION}s)"
        ((FAIL_COUNT++))
    fi
else
    print_status "INFO" "testdata directory not found at /fast/peijinz/agile_proc/testdata, skipping data access test"
fi


# Summary
echo ""
echo "=== Test Summary ==="
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"

if [ $FAIL_COUNT -eq 0 ]; then
    print_status "PASS" "All tests passed!"
    echo ""
    echo "The astronrd/linc container is ready for use with the self-calibration pipeline."
    echo ""
    echo "Next steps:"
    echo "1. Run the self-calibration pipeline: ./run_selfcal.sh"
    echo "2. Or test with Python directly: python3 selfcal_pipeline.py /fast/peijinz/agile_proc/testdata/slow/20240519_173002_55MHz.ms"
else
    print_status "FAIL" "Some tests failed. Please check the errors above."
    echo ""
    echo "You may still be able to run the pipeline, but some features might not work correctly."
    echo "Consider fixing the failed tests before proceeding."
fi

echo ""
echo "=== Performance Notes ==="
echo "Container startup times are typically:"
echo "- Basic container: 1-3 seconds"
echo "- DP3 invocation: 2-5 seconds"
echo "- WSClean invocation: 2-5 seconds"
echo "- Volume mounting: 1-2 seconds"
echo ""
echo "If times are significantly higher, consider:"
echo "- Checking system resources (CPU, memory, disk I/O)"
echo "- Verifying podman daemon status"
echo "- Checking for network issues (if pulling images)"
echo "- Monitoring container resource usage"

echo ""
echo "For more information, see README_selfcal.md"

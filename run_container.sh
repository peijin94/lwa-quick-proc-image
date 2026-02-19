#!/bin/bash
# Run LWA solar pipeline in container

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPEDEV_DIR="$(cd "${REPO_DIR}/.." && pwd)"
MS_PATH="${1:-${PIPEDEV_DIR}/slow_data/20260209_210309_69MHz.ms}"
BCAL_PATH="${2:-${PIPEDEV_DIR}/caltables_latest/20251223_030331_69MHz.bcal}"

if ! command -v podman >/dev/null 2>&1; then
  echo "podman is required but not found in PATH"
  exit 1
fi

if command -v conda >/dev/null 2>&1; then
  if ! conda env list | awk '{print $1}' | grep -qx "lwa"; then
    echo "conda environment 'lwa' not found"
    exit 1
  fi
fi

if [ ! -e "${MS_PATH}" ] || [ ! -e "${BCAL_PATH}" ]; then
  echo "Missing input path(s):"
  echo "  MS_PATH=${MS_PATH}"
  echo "  BCAL_PATH=${BCAL_PATH}"
  exit 1
fi

podman run --rm -it \
  -v "${REPO_DIR}:/lwasoft:ro" \
  -v "${PIPEDEV_DIR}:/workspace:rw" \
  -w /workspace \
  peijin/lwa-solar-pipehost:v202510 \
  python3 /lwasoft/pipeline_quick_proc_img.py \
    "/workspace/slow_data/$(basename "${MS_PATH}")" \
    "/workspace/caltables_latest/$(basename "${BCAL_PATH}")" \
  > "${REPO_DIR}/proc.log"

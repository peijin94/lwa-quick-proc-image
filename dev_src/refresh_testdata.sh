#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIPEDEV_DIR="$(cd "${REPO_DIR}/.." && pwd)"
OUTPUT_DIR="${PIPEDEV_DIR}/runtime_dir"

mkdir -p "${OUTPUT_DIR}"

for v in v2 v4; do
    DIR_DATA="${OUTPUT_DIR}/testdata_${v}"
    DIR_DATA_SRC="${OUTPUT_DIR}/testdata_${v}.tar"

    if [ ! -f "${DIR_DATA_SRC}" ]; then
        echo "Skipping ${v}: archive not found at ${DIR_DATA_SRC}"
        continue
    fi

    rm -rf "${DIR_DATA}"
    tar -xvf "${DIR_DATA_SRC}" -C "${OUTPUT_DIR}"
done

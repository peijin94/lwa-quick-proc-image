#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./run_allband.sh <data_dir> <gaintable_dir> <runtime_dir> <params_json> [max_jobs]

Arguments:
  data_dir       Directory containing input MS files (*.ms)
  gaintable_dir  Directory containing gaintable directories/files (*_<band>.bcal)
  runtime_dir    Runtime root passed to run_worker.py
  params_json    params_input.json path passed to run_worker.py
  max_jobs       Optional parallel job limit (default: 4)

Example:
  ./run_allband.sh \
    /home/pjzhang/dev/pipedev/slow_data \
    /home/pjzhang/dev/pipedev/caltables_latest \
    /home/pjzhang/dev/pipedev/runtime_dir \
    /home/pjzhang/dev/pipedev/lwa-quick-proc-image/params_input.json \
    13
EOF
}

if [[ $# -lt 4 || $# -gt 5 ]]; then
  usage
  exit 1
fi

DATA_DIR="$1"
GAINTABLE_DIR="$2"
RUNTIME_DIR="$3"
PARAMS_JSON="$4"
MAX_JOBS="${5:-4}"

if [[ ! -d "$DATA_DIR" ]]; then
  echo "data_dir not found: $DATA_DIR"
  exit 1
fi
if [[ ! -d "$GAINTABLE_DIR" ]]; then
  echo "gaintable_dir not found: $GAINTABLE_DIR"
  exit 1
fi
if [[ ! -f "$PARAMS_JSON" ]]; then
  echo "params json not found: $PARAMS_JSON"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found in PATH"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${SCRIPT_DIR}/run_worker.py"
if [[ ! -f "$RUNNER" ]]; then
  echo "run_worker.py not found at: $RUNNER"
  exit 1
fi

mkdir -p "$RUNTIME_DIR"
shopt -s nullglob
MS_FILES=("$DATA_DIR"/*.ms)
shopt -u nullglob

if [[ ${#MS_FILES[@]} -eq 0 ]]; then
  echo "No .ms files found in $DATA_DIR"
  exit 1
fi

echo "Found ${#MS_FILES[@]} MS files"
echo "Running with max_jobs=$MAX_JOBS"

run_one() {
  local ms_file="$1"
  local ms_base
  ms_base="$(basename "$ms_file")"

  if [[ "$ms_base" =~ ([0-9]+MHz)\.ms$ ]]; then
    local band="${BASH_REMATCH[1]}"
  else
    echo "[SKIP] Cannot parse band from $ms_base"
    return 0
  fi

  shopt -s nullglob
  local matches=("$GAINTABLE_DIR"/*_"$band".bcal)
  shopt -u nullglob
  if [[ ${#matches[@]} -eq 0 ]]; then
    echo "[SKIP] No gaintable found for $band ($ms_base)"
    return 0
  fi

  IFS=$'\n' read -r -d '' -a sorted < <(printf '%s\n' "${matches[@]}" | sort && printf '\0')
  local gaintable="${sorted[-1]}"

  echo "[RUN ] $ms_base  band=$band  gaintable=$(basename "$gaintable")"
  python3 "$RUNNER" \
    --data-file "$ms_file" \
    --gaintable-file "$gaintable" \
    --runtime-dir "$RUNTIME_DIR" \
    --params "$PARAMS_JSON"
}

running=0
for ms in "${MS_FILES[@]}"; do
  run_one "$ms" &
  ((running+=1))
  if (( running >= MAX_JOBS )); then
    wait -n
    ((running-=1))
  fi
done

wait
echo "All submitted jobs finished."

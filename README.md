# solarpipeworker

Refactored LWA quick processing pipeline with a sandboxed runtime workflow.

## What Changed

The repository now exposes a real Python package, `solarpipeworker`, with a stable API:

- `solarpipeworker.main_worker.run_job(...)`
- `solarpipeworker.main_worker.load_params(...)`

Each run executes in a dedicated UUID sandbox directory:

- `<runtime_dir>/<uuid4>/`

The input MS and calibration table are copied into that job directory and processing runs only there.

## Repository Layout

- `solarpipeworker/`
  - `main_worker.py` (main orchestration)
  - `utils.py` (job dir, copy, logging, subprocess helpers)
  - `visualization.py` (FITS plotting)
  - `source_list.py` (Sun/source utilities)
  - `lua/LWA_sun_PZ.lua`
- `run_worker.py` (recommended CLI harness)
- `params_input.json` (default worker parameters)
- `pipeline_quick_proc_img.py` (legacy compatibility wrapper)

## Requirements

- Python 3.10+
- CASA/DP3/WSClean runtime dependencies available in environment/container
- Python packages listed in `pyproject.toml`

Optional dev tools:

- `pytest`
- `ruff`

## Install (editable)

```bash
python3 -m pip install -e .
```

## Run Worker (Recommended)

```bash
python3 run_worker.py \
  --data-file /home/pjzhang/dev/pipedev/slow_data/20260209_210309_64MHz.ms \
  --runtime-dir /home/pjzhang/dev/pipedev/runtime_dir \
  --params params_input.json
```

Outputs:

- `job_dir/job.log`
- `job_dir/summary.json`
- Pipeline artifacts (`.ms`, `.fits`, `.png`, `.h5`, `.txt`) in `job_dir`

## Public API Example

```python
from solarpipeworker import load_params, run_job

params = load_params("params_input.json")
result = run_job(
    data_file="/home/pjzhang/dev/pipedev/slow_data/20260209_210309_64MHz.ms",
    runtime_dir="/home/pjzhang/dev/pipedev/runtime_dir",
    params=params,
)

print(result.success, result.job_dir)
```

## Legacy Compatibility CLI

`pipeline_quick_proc_img.py` remains as a compatibility wrapper and forwards execution to `run_job`.

```bash
python3 pipeline_quick_proc_img.py \
  /path/to/raw.ms \
  /path/to/bandpass.bcal \
  output_prefix \
  --mfs-img
```

## Parameters

`params_input.json` fields:

- `gaintable_file` (required)
- `container_image` (default: `peijin/lwa-solar-pipehost:v202510`)
- `output_prefix`
- `keep_ms_tmp`
- `fch_img`
- `mfs_img`
- `debug`
- `plot_mid_steps`
- `cleanup_on_success`
- `strategy_file`

## Tests

```bash
python3 -m pytest -q tests/test_worker_basics.py
```

## Notes

- Original input MS is never modified in-place.
- All intermediate and output files are isolated per job.
- `summary.json` is always written, including failure details when a run fails.

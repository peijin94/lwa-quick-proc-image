#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import replace

from solarpipeworker import load_params, run_job


def main() -> int:
    parser = argparse.ArgumentParser(description="Run solarpipeworker job")
    parser.add_argument("--data-file", required=True, help="Input measurement set (.ms) path")
    parser.add_argument(
        "--gaintable-file",
        default=None,
        help="Calibration table (.bcal) path. Overrides params file when provided.",
    )
    parser.add_argument("--runtime-dir", required=True, help="Root runtime directory")
    parser.add_argument("--params", default="params_input.json", help="Path to params JSON")
    parser.add_argument(
        "--cleanup-on-success",
        action="store_true",
        help="Delete UUID job directory after successful completion",
    )
    args = parser.parse_args()

    params = load_params(args.params)
    if args.gaintable_file:
        params = replace(params, gaintable_file=args.gaintable_file)
    if args.cleanup_on_success:
        params = replace(params, cleanup_on_success=True)

    result = run_job(
        data_file=args.data_file,
        runtime_dir=args.runtime_dir,
        params=params,
    )

    concise_summary = {
        "job_id": result.job_id,
        "success": result.success,
        "job_dir": str(result.job_dir),
        "artifact_count": len(result.artifacts),
        "flist_fch": [str(p) for p in result.flist_fch],
        "fname_mfs": str(result.fname_mfs) if result.fname_mfs else None,
        "errors": result.errors,
    }
    print(json.dumps(concise_summary, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())

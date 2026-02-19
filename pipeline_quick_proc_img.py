#!/usr/bin/env python3
"""Compatibility wrapper for the legacy pipeline entrypoint.

This script preserves the historical CLI shape and forwards execution to
`solarpipeworker.run_job`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from solarpipeworker import Params, run_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compatibility wrapper: raw MS -> solarpipeworker.run_job sandbox workflow"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("raw_ms", type=str, help="Input raw measurement set path")
    parser.add_argument("gaintable", type=str, help="Calibration table path (.bcal)")
    parser.add_argument(
        "output_prefix",
        type=str,
        nargs="?",
        default=None,
        help="Output file prefix (default: derived from input MS filename)",
    )
    parser.add_argument(
        "--keep-ms-tmp",
        action="store_true",
        default=False,
        help="Keep temporary measurement sets (legacy behavior)",
    )
    parser.add_argument(
        "--fch-img",
        action="store_true",
        default=False,
        help="Generate per-channel images",
    )
    parser.add_argument(
        "--mfs-img",
        action="store_true",
        default=False,
        help="Generate multi-frequency synthesis image",
    )
    parser.add_argument(
        "--runtime-dir",
        type=str,
        default=None,
        help=(
            "Runtime root for UUID job dirs. Default: <raw_ms parent>/runtime_dir_compat"
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    raw_ms = Path(args.raw_ms).resolve()
    gaintable = Path(args.gaintable).resolve()

    if not raw_ms.exists():
        print(f"Error: Raw MS not found: {raw_ms}", file=sys.stderr)
        return 1
    if not gaintable.exists():
        print(f"Error: Gaintable not found: {gaintable}", file=sys.stderr)
        return 1

    output_prefix = args.output_prefix or raw_ms.stem.split(".")[0]
    runtime_dir = (
        Path(args.runtime_dir).resolve()
        if args.runtime_dir
        else (raw_ms.parent / "runtime_dir_compat").resolve()
    )

    params = Params(
        gaintable_file=str(gaintable),
        output_prefix=output_prefix,
        keep_ms_tmp=args.keep_ms_tmp,
        fch_img=args.fch_img,
        mfs_img=args.mfs_img,
        debug=False,
        plot_mid_steps=False,
        cleanup_on_success=False,
        strategy_file=None,
    )

    result = run_job(data_file=raw_ms, runtime_dir=runtime_dir, params=params)

    summary = {
        "job_id": result.job_id,
        "job_dir": str(result.job_dir),
        "success": result.success,
        "errors": result.errors,
        "artifact_count": len(result.artifacts),
        "flist_fch": [str(p) for p in result.flist_fch],
        "fname_mfs": str(result.fname_mfs) if result.fname_mfs else None,
        "elapsed_seconds": result.metrics.get("elapsed_seconds"),
    }
    print(json.dumps(summary, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())

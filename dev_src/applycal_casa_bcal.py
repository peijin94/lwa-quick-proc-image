#!/usr/bin/env python3
import argparse
from pathlib import Path

import casatasks


def main():
    repo_dir = Path(__file__).resolve().parents[1]
    pipedev_dir = repo_dir.parent

    parser = argparse.ArgumentParser(description="Apply CASA bandpass calibration table.")
    parser.add_argument(
        "--ms",
        default=str(pipedev_dir / "slow_data" / "20260209_210309_55MHz.ms"),
        help="Path to input measurement set (.ms)",
    )
    parser.add_argument(
        "--bcal",
        default=str(pipedev_dir / "caltables_latest" / "20251223_030331_55MHz.bcal"),
        help="Path to CASA bandpass table (.bcal)",
    )
    args = parser.parse_args()

    ms_path = Path(args.ms)
    bcal_path = Path(args.bcal)
    if not ms_path.exists():
        raise FileNotFoundError(f"Measurement set not found: {ms_path}")
    if not bcal_path.exists():
        raise FileNotFoundError(f"Bandpass table not found: {bcal_path}")

    casatasks.applycal(vis=str(ms_path), gaintable=str(bcal_path), applymode="calflag")


if __name__ == "__main__":
    main()

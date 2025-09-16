#!/usr/bin/env python3
"""
Minimal script to run wsclean imaging using podman
Uses default parameters optimized for LWA data processing
"""

import subprocess
import sys
import os
from pathlib import Path

def run_wsclean_imaging(input_ms, output_prefix="image"):
    """
    Run wsclean imaging with specified parameters
    
    Args:
        input_ms: Path to input measurement set
        output_prefix: Prefix for output image files
    """
    
    input_path = Path(input_ms)
    
    if not input_path.exists():
        print(f"Error: Input measurement set not found: {input_ms}")
        sys.exit(1)
    
    # Default parameters
    default_kwargs = {
        'j': '8',                           # number of threads
        'mem': '2',                         # fraction of memory usage
        'weight': 'uniform',                # weighting scheme
        'no-dirty': '',                     # don't save dirty image
        'no-update-model-required': '',     # don't update model required
        'no-negative': '',                  # no negative gain for CLEAN
        'niter': '1000',                    # number of iterations (override)
        'mgain': '0.9',                     # maximum gain in each cycle (override)
        'auto-threshold': '3',              # auto threshold
        'auto-mask': '8',                   # auto mask
        'pol': 'I',                         # polarization
        'minuv-l': '10',                    # minimum uv distance in lambda
        'intervals-out': '1',               # number of output images
        'no-reorder': '',                   # don't reorder the channels
        'beam-fitting-size': '2',           # beam fitting size
        'horizon-mask': "2deg",             # horizon mask distance
        'quiet': '',                        # stop printing to stdout
    }
    
    # Image size and pixel scale
    size = 4096
    pixel_scale = "2arcmin"  # Pixel scale for LWA data
    
    # Build wsclean command
    wsclean_cmd = ["wsclean"]
    
    # Add size parameters
    wsclean_cmd.extend(["-size", str(size), str(size)])
    
    # Add pixel scale
    wsclean_cmd.extend(["-scale", pixel_scale])
    
    # Add output name
    wsclean_cmd.extend(["-name", output_prefix])
    
    # Add all default parameters
    for key, value in default_kwargs.items():
        if value == '':  # Boolean flags
            wsclean_cmd.append(f"-{key}")
        else:
            wsclean_cmd.extend([f"-{key}", value])
    
    # Add input MS
    wsclean_cmd.append(str(input_path))
    
    print(f"Running wsclean imaging...")
    print(f"Input: {input_ms}")
    print(f"Output prefix: {output_prefix}")
    print(f"Image size: {size}x{size}")
    
    # Prepare podman command
    input_dir = input_path.parent
    output_dir = input_dir  # Output to same directory as MS file
    
    podman_cmd = [
        "podman", "run", "--rm",
        "-v", f"{input_dir}:/data",
        "-w", "/data",
        "astronrd/linc:latest"
    ] + wsclean_cmd
    
    # Update the MS path in the command to use container path
    podman_cmd[-1] = f"/data/{input_path.name}"
    
    print(f"Command: {' '.join(wsclean_cmd)}")
    
    try:
        # Run wsclean
        result = subprocess.run(podman_cmd, check=True, text=True)
        print("WSClean imaging completed successfully!")
        
        # List generated files
        print("\nGenerated files:")
        for file in output_dir.glob(f"{output_prefix}*"):
            print(f"  {file.name}")
        
    except subprocess.CalledProcessError as e:
        print(f"WSClean failed with exit code {e.returncode}")
        sys.exit(1)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 run_wsclean_imaging.py <input_ms> [output_prefix]")
        print("Example: python3 run_wsclean_imaging.py /fast/peijinz/agile_proc/testdata/slow/flagged_avg.ms")
        sys.exit(1)
    
    input_ms = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else "image"
    
    run_wsclean_imaging(input_ms, output_prefix)

if __name__ == "__main__":
    main()

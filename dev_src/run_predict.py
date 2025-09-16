#!/usr/bin/env python3
"""
Minimal script to run wsclean in predict mode to fill MODEL_DATA column
Uses an existing CLEAN model from previous imaging
"""

import subprocess
import sys
import os
from pathlib import Path

def run_predict(input_ms, model_prefix, output_ms=None):
    """
    Run wsclean in predict mode to fill MODEL_DATA column
    
    Args:
        input_ms: Path to input measurement set
        model_prefix: Prefix of model files (e.g., "image" for image-model.fits)
        output_ms: Path to output MS (optional, defaults to input_ms_model.ms)
    """
    
    input_path = Path(input_ms)
    
    if not input_path.exists():
        print(f"Error: Input measurement set not found: {input_ms}")
        sys.exit(1)
    
    # Check for model file
    model_dir = input_path.parent
    model_file = model_dir / f"{model_prefix}-model.fits"
    
    if not model_file.exists():
        print(f"Error: Model file not found: {model_file}")
        print(f"Make sure you have run imaging first to create the model")
        sys.exit(1)
    
    # Set output MS name if not provided
    if output_ms is None:
        output_ms = input_path.parent / f"{input_path.stem}_model.ms"
    else:
        output_ms = Path(output_ms)
    
    print(f"Running wsclean predict mode...")
    print(f"Input: {input_ms}")
    print(f"Model: {model_file}")
    print(f"Output: {output_ms}")
    
    # Build wsclean predict command
    wsclean_cmd = [
        "wsclean",
        "-predict",                    # Predict mode - fills MODEL_DATA
        "-name", model_prefix,         # Use existing model
        "-channels-out", "1",          # Single channel output
        str(input_path)
    ]
    
    # Prepare podman command
    input_dir = input_path.parent
    
    podman_cmd = [
        "podman", "run", "--rm",
        "-v", f"{input_dir}:/data",
        "-w", "/data",
        "astronrd/linc:latest"
    ] + wsclean_cmd
    
    # Update paths for container
    podman_cmd[-1] = f"/data/{input_path.name}"  # Input MS path
    # Find the -name argument and update model prefix path
    for i, arg in enumerate(podman_cmd):
        if arg == "-name":
            podman_cmd[i+1] = model_prefix  # Keep relative path
            break
    
    print(f"Command: {' '.join(wsclean_cmd)}")
    
    try:
        # Run wsclean predict
        result = subprocess.run(podman_cmd, check=True, text=True)
        print("WSClean predict completed successfully!")
        print(f"MODEL_DATA column filled in: {input_ms}")
        
    except subprocess.CalledProcessError as e:
        print(f"WSClean predict failed with exit code {e.returncode}")
        sys.exit(1)

def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python3 run_predict.py <input_ms> <model_prefix> [output_ms]")
        print("Examples:")
        print("  python3 run_predict.py /path/to/data.ms image")
        print("  python3 run_predict.py /path/to/data.ms test_model /path/to/output.ms")
        print("")
        print("Note: This requires existing model files (model_prefix-model.fits)")
        print("      from previous wsclean imaging run")
        sys.exit(1)
    
    input_ms = sys.argv[1]
    model_prefix = sys.argv[2]
    output_ms = sys.argv[3] if len(sys.argv) > 3 else None
    
    run_predict(input_ms, model_prefix, output_ms)

if __name__ == "__main__":
    main()

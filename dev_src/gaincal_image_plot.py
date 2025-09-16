#!/usr/bin/env python3
"""
Complete pipeline script: gain calibration -> imaging -> plotting
Runs the full sequence on measurement set data
"""

import subprocess
import sys
import os
from pathlib import Path

def run_pipeline(input_ms, output_prefix="calibrated"):
    """
    Run complete pipeline: gaincal -> imaging -> plotting
    
    Args:
        input_ms: Path to input measurement set (with MODEL_DATA filled)
        output_prefix: Prefix for output files
    """
    
    input_path = Path(input_ms)
    
    if not input_path.exists():
        print(f"Error: Input measurement set not found: {input_ms}")
        sys.exit(1)
    
    print("="*60)
    print("STEP 1: Running gain calibration...")
    print("="*60)
    
    # Step 1: Run gain calibration
    cal_ms = input_path.parent / f"{output_prefix}_cal.ms"
    
    gaincal_cmd = [
        "python3", "run_gaincal.py",
        str(input_ms),
        str(cal_ms)
    ]
    
    try:
        result = subprocess.run(gaincal_cmd, check=True, text=True)
        print(f"✓ Gain calibration completed: {cal_ms}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Gain calibration failed with exit code {e.returncode}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("STEP 2: Running wsclean imaging...")
    print("="*60)
    
    # Step 2: Run wsclean imaging on calibrated data
    image_prefix = f"{output_prefix}_image"
    
    wsclean_cmd = [
        "python3", "run_wsclean_imaging.py",
        str(cal_ms),
        image_prefix
    ]
    
    try:
        result = subprocess.run(wsclean_cmd, check=True, text=True)
        print(f"✓ WSClean imaging completed with prefix: {image_prefix}")
    except subprocess.CalledProcessError as e:
        print(f"✗ WSClean imaging failed with exit code {e.returncode}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("STEP 3: Plotting gain solutions...")
    print("="*60)
    
    # Step 3a: Plot gain solutions if solution.h5 exists
    solution_file = input_path.parent / "solution.h5"
    if solution_file.exists():
        solution_cmd = [
            "python3", "plot_solutions.py",
            str(solution_file)
        ]
        
        try:
            result = subprocess.run(solution_cmd, check=True, text=True)
            print(f"✓ Gain solution plotting completed")
        except subprocess.CalledProcessError as e:
            print(f"✗ Gain solution plotting failed with exit code {e.returncode}")
    else:
        print("ℹ️  No solution.h5 file found, skipping gain solution plots")
    
    print("\n" + "="*60)
    print("STEP 4: Plotting FITS images...")
    print("="*60)
    
    # Step 4: Plot the resulting FITS images
    plot_cmd = [
        "python3", "plot_fits.py",
        str(input_path.parent / image_prefix)
    ]
    
    try:
        result = subprocess.run(plot_cmd, check=True, text=True)
        print(f"✓ FITS plotting completed")
    except subprocess.CalledProcessError as e:
        print(f"✗ FITS plotting failed with exit code {e.returncode}")
        print("Note: This may fail if matplotlib/astropy are not installed")
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*60)
    
    # Show generated files
    print("\nGenerated files:")
    cal_dir = input_path.parent
    
    # List calibrated MS
    if cal_ms.exists():
        print(f"  📁 Calibrated MS: {cal_ms}")
    
    # List FITS files
    fits_files = list(cal_dir.glob(f"{image_prefix}*.fits"))
    for fits_file in sorted(fits_files):
        print(f"  🖼️  FITS: {fits_file.name}")
    
    # List PNG files
    png_files = list(cal_dir.glob(f"{image_prefix}*.png"))
    for png_file in sorted(png_files):
        print(f"  📊 Plot: {png_file.name}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 gaincal_image_plot.py <input_ms> [output_prefix]")
        print("Examples:")
        print("  python3 gaincal_image_plot.py /path/to/data.ms")
        print("  python3 gaincal_image_plot.py /path/to/data.ms my_result")
        print("")
        print("This script runs the complete pipeline:")
        print("  1. Gain calibration (assumes MODEL_DATA is filled)")
        print("  2. WSClean imaging on calibrated data")
        print("  3. Plotting of resulting FITS images")
        print("")
        print("Required scripts in current directory:")
        print("  - run_gaincal.py")
        print("  - run_wsclean_imaging.py") 
        print("  - plot_fits.py")
        print("  - plot_solutions.py")
        sys.exit(1)
    
    input_ms = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else "calibrated"
    
    # Check if required scripts exist
    required_scripts = ["run_gaincal.py", "run_wsclean_imaging.py", "plot_fits.py", "plot_solutions.py"]
    missing_scripts = []
    
    for script in required_scripts:
        if not Path(script).exists():
            missing_scripts.append(script)
    
    if missing_scripts:
        print(f"Error: Missing required scripts: {', '.join(missing_scripts)}")
        print("Make sure all pipeline scripts are in the current directory.")
        sys.exit(1)
    
    run_pipeline(input_ms, output_prefix)

if __name__ == "__main__":
    main()

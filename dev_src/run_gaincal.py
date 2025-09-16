#!/usr/bin/env python3
"""
Minimal script to run gain calibration using DP3
Assumes MODEL_DATA column has been filled by wsclean imaging
"""

import subprocess
import sys
import os
from pathlib import Path

def run_gaincal(input_ms, output_ms=None, solint=0, caltype="gain"):
    """
    Run DP3 gain calibration
    
    Args:
        input_ms: Path to input measurement set (with MODEL_DATA)
        output_ms: Path to output measurement set (optional, defaults to input_ms_cal.ms)
        solint: Solution interval in timesteps (0 = per scan)
        caltype: Calibration type (gain, phase, bandpass)
    """
    
    input_path = Path(input_ms)
    
    if not input_path.exists():
        print(f"Error: Input measurement set not found: {input_ms}")
        sys.exit(1)
    
    # Set output MS name if not provided
    if output_ms is None:
        output_ms = input_path.parent / f"{input_path.stem}_cal.ms"
    else:
        output_ms = Path(output_ms)
    
    print(f"Running DP3 gain calibration...")
    print(f"Input: {input_ms}")
    print(f"Output: {output_ms}")
    print(f"Solution interval: {solint} (0=per scan)")
    print(f"Calibration type: {caltype}")



    # Create DP3 parset for gain calibration
    parset_content = f"""msin = /data/{input_path.name}

msout = /data/{output_ms.name}

steps = [gaincal]

gaincal.solint = {solint}
gaincal.caltype = diagonalphase
gaincal.uvlambdamin = 10
gaincal.maxiter = 100
gaincal.tolerance = 1e-4
gaincal.usemodelcolumn = true
gaincal.modelcolumn = MODEL_DATA
gaincal.parmdb = /data/solution.h5


gaincal.applycal.parmdb = /data/solution.h5
gaincal.applycal.correction = phase
"""

#applycal.parmdb = /data/solution.h5
#applycal.correction = phase


    # Write parset to temporary file
    parset_file = Path("gaincal.parset")
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    # Prepare podman command
    input_dir = input_path.parent
    
    podman_cmd = [
        "podman", "run", "--rm",
        "-v", f"{input_dir}:/data",
        "-v", f"{Path.cwd()}:/config",
        "-w", "/config",
        "astronrd/linc:latest",
        "DP3", f"/config/{parset_file.name}"
    ]
    
    print(f"Running DP3 gain calibration...")
    
    try:
        # Run DP3
        result = subprocess.run(podman_cmd, check=True, capture_output=True, text=True)
        print("DP3 gain calibration completed successfully!")
        if result.stdout:
            print("STDOUT:", result.stdout)
        
        # Check if output MS was created
        if output_ms.exists():
            print(f"Calibrated MS created: {output_ms}")
        else:
            print("Warning: Output MS not found")
        
        # Clean up parset file
        parset_file.unlink()
        
    except subprocess.CalledProcessError as e:
        print(f"DP3 gain calibration failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        # Clean up parset file even on failure
        if parset_file.exists():
            parset_file.unlink()
        sys.exit(1)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 run_gaincal.py <input_ms> [output_ms] [solint] [caltype]")
        print("Examples:")
        print("  python3 run_gaincal.py /path/to/data.ms")
        print("  python3 run_gaincal.py /path/to/data.ms /path/to/calibrated.ms")
        print("  python3 run_gaincal.py /path/to/data.ms calibrated.ms 0 gain")
        print("")
        print("Parameters:")
        print("  solint: Solution interval (0=per scan, 1=per timestep)")
        print("  caltype: gain, phase, or bandpass")
        sys.exit(1)
    
    input_ms = sys.argv[1]
    output_ms = sys.argv[2] if len(sys.argv) > 2 else None
    solint = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    caltype = sys.argv[4] if len(sys.argv) > 4 else "gain"
    
    run_gaincal(input_ms, output_ms, solint, caltype)

if __name__ == "__main__":
    main()

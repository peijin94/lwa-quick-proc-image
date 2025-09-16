#!/usr/bin/env python3
"""
Apply gain calibration solutions using DP3
"""

import subprocess
import sys
import os
from pathlib import Path

def run_applycal(input_ms, solution_file, output_ms=None):
    """Apply gain calibration solutions using DP3"""
    
    input_path = Path(input_ms)
    solution_path = Path(solution_file)
    
    # Validate inputs
    if not input_path.exists():
        print(f"Error: Input MS not found: {input_ms}")
        sys.exit(1)
    if not solution_path.exists():
        print(f"Error: Solution file not found: {solution_file}")
        sys.exit(1)
    
    # Set output path
    if output_ms is None:
        output_ms = input_path.parent / f"{input_path.stem}_corrected.ms"
    else:
        output_ms = Path(output_ms)
        if not output_ms.is_absolute():
            output_ms = input_path.parent / output_ms
    
    print(f"Applying calibration: {input_ms} -> {output_ms}")
    
    # Find common parent for volume mounting
    common_parent = Path(os.path.commonpath([
        input_path.parent, solution_path.parent, output_ms.parent
    ]))
    
    # Create DP3 parset
    parset_content = f"""msin = /data/{input_path.relative_to(common_parent)}
msout = /data/{output_ms.relative_to(common_parent)}
steps = [applycal]
applycal.type = applycal
applycal.parmdb = /data/{solution_path.relative_to(common_parent)}
applycal.correction = phase000
"""
    
    # Write and run DP3
    parset_file = Path("applycal.parset")
    try:
        with open(parset_file, 'w') as f:
            f.write(parset_content)
        
        cmd = [
            "podman", "run", "--rm",
            "-v", f"{common_parent}:/data",
            "-v", f"{Path.cwd()}:/config",
            "-w", "/config",
            "astronrd/linc:latest",
            "DP3", f"/config/{parset_file.name}"
        ]
        
        subprocess.run(cmd, check=True)
        print(f"✓ Calibration applied: {output_ms}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ DP3 failed with exit code {e.returncode}")
        sys.exit(1)
    finally:
        parset_file.unlink(missing_ok=True)

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 applycal_dp3.py <input_ms> <solution_file> [output_ms]")
        print("Example: python3 applycal_dp3.py data.ms solution.h5")
        sys.exit(1)
    
    run_applycal(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)

if __name__ == "__main__":
    main()
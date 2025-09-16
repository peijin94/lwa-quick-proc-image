#!/usr/bin/env python3
"""
Minimal script to run DP3 with aoflagger and frequency averaging
Uses podman to run DP3 with default aoflagger strategy and averages every 3 channels
"""

import subprocess
import sys
import os
from pathlib import Path

def run_dp3_flag_avg(input_ms, output_ms, strategy_file=None):
    """
    Run DP3 with aoflagger and frequency averaging
    
    Args:
        input_ms: Path to input measurement set
        output_ms: Path to output measurement set
        strategy_file: Optional custom aoflagger strategy file
    """
    
    input_path = Path(input_ms)
    output_path = Path(output_ms)
    
    # Find common parent directory
    common_parent = Path(os.path.commonpath([input_path.parent, output_path.parent]))
    
    # Calculate relative paths from common parent
    input_rel_path = input_path.relative_to(common_parent)
    output_rel_path = output_path.relative_to(common_parent)
    
    # Create container paths
    input_container_path = f"/data/{input_rel_path}"
    output_container_path = f"/data/{output_rel_path}"
    
    # Create DP3 parset for flagging and averaging
    parset_content = f"""
msin.type = ms
msin.name = {input_container_path}

msout.type = ms
msout.name = {output_container_path}
msout.writefullresflag = true

steps = [flag, avg]

# Aoflagger step with default strategy
flag.type = aoflagger
flag.strategy = /usr/local/share/linc/rfistrategies/lofar-default.lua

# Frequency averaging step - average every 3 channels
avg.type = averager
avg.freqstep = 3
"""

    # Write parset to temporary file
    parset_file = Path("dp3_flag_avg.parset")
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    print(f"Running DP3 with aoflagger and frequency averaging...")
    print(f"Input: {input_ms}")
    print(f"Output: {output_ms}")
    
    # Prepare podman command
    # Mount the common parent directory that contains both input and output
    
    podman_cmd = [
        "podman", "run", "--rm",
        "-v", f"{common_parent}:/data",
        "-v", f"{Path(parset_file).parent}:/config",
        "astronrd/linc:latest",
        "DP3", f"/config/{parset_file.name}"
    ]
    
    print(f"Command: {' '.join(podman_cmd)}")
    
    try:
        # Run DP3
        result = subprocess.run(podman_cmd, check=True, capture_output=True, text=True)
        print("DP3 completed successfully!")
        print("STDOUT:", result.stdout)
        
        # Clean up parset file
        parset_file.unlink()
        
    except subprocess.CalledProcessError as e:
        print(f"DP3 failed with exit code {e.returncode}")
        print("STDERR:", e.stderr)
        sys.exit(1)

def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python3 run_dp3_flag_avg.py <input_ms> <output_ms>")
        print("Example: python3 run_dp3_flag_avg.py /path/to/input.ms /path/to/output.ms")
        sys.exit(1)
    
    input_ms = sys.argv[1]
    output_ms = sys.argv[2]
    
    # Check if input MS exists
    if not Path(input_ms).exists():
        print(f"Error: Input measurement set not found: {input_ms}")
        sys.exit(1)
    
    run_dp3_flag_avg(input_ms, output_ms)

if __name__ == "__main__":
    main()

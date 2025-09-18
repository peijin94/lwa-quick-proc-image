#!/usr/bin/env python3
"""
Simple script to phase shift MS to Sun's coordinates using DP3 PhaseShift step.
"""

import subprocess
import sys
from pathlib import Path
import tempfile
from source_list import get_Sun_RA_DEC, get_time_mjd

def phaseshift_to_sun(ms_file, output_ms=None):
    """
    Phase shift MS to Sun's coordinates using DP3 PhaseShift step.
    
    Args:
        ms_file (str): Path to input measurement set
        output_ms (str, optional): Path to output MS. If None, uses input_sun_shifted.ms
    
    Returns:
        str: Path to output measurement set
    """
    ms_path = Path(ms_file)
    
    # Validate input
    if not ms_path.exists():
        raise FileNotFoundError(f"MS file not found: {ms_path}")
    
    # Set output MS name
    if output_ms is None:
        output_ms = ms_path.parent / f"{ms_path.stem}_sun_shifted.ms"
    else:
        output_ms = Path(output_ms)
    
    # Get time from MS and calculate Sun position
    print(f"Getting observation time from MS: {ms_path}")
    time_mjd = get_time_mjd(str(ms_path))
    print(f"Observation time (MJD): {time_mjd}")
    
    # Get Sun RA/DEC
    sun_ra, sun_dec = get_Sun_RA_DEC(time_mjd)
    print(f"Sun position - RA: {sun_ra:.6f}°, DEC: {sun_dec:.6f}°")
    
    # Convert to absolute paths
    ms_abs = ms_path.resolve()
    output_abs = output_ms.resolve()
    
    # Find common parent directory for mounting
    common_parent = Path(*ms_abs.parts[:-1])  # MS parent directory
    if not str(output_abs).startswith(str(common_parent)):
        # If output is in different directory, use root
        common_parent = Path("/")
    
    print(f"Input MS: {ms_abs}")
    print(f"Output MS: {output_abs}")
    print(f"Mount directory: {common_parent}")
    
    # Calculate relative paths
    ms_rel = ms_abs.relative_to(common_parent)
    output_rel = output_abs.relative_to(common_parent)
    
    # Create DP3 parset for phase shift
    parset_content = f"""
msin = /data/{ms_rel}
msout = /data/{output_rel}

steps = [phaseshift]

phaseshift.type = phaseshift
phaseshift.phasecenter = [{sun_ra}deg, {sun_dec}deg]
"""
    
    # Write parset to temporary file in common parent
    parset_file = common_parent / "phaseshift_to_sun.parset"
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    try:
        print(f"\nDP3 Parset contents:")
        print(parset_content)
        
        # Run DP3 in container
        cmd = [
            "podman", "run", "--rm",
            "-v", f"{common_parent}:/data",
            "-w", "/data",
            "astronrd/linc:latest",
            "DP3", "phaseshift_to_sun.parset"
        ]
        
        print(f"Running DP3 command:")
        print(" ".join(cmd))
        print()
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("DP3 failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            raise RuntimeError(f"DP3 failed with exit code {result.returncode}")
        
        print("DP3 phase shift completed successfully!")
        print("STDOUT:", result.stdout)
        
        return str(output_abs)
        
    finally:
        # Clean up parset file
        if parset_file.exists():
            parset_file.unlink()

def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python phaseshift_to_sun.py <ms_file> [output_ms]")
        print("Example: python phaseshift_to_sun.py data.ms data_sun_shifted.ms")
        sys.exit(1)
    
    ms_file = sys.argv[1]
    output_ms = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        output_path = phaseshift_to_sun(ms_file, output_ms)
        print(f"\nPhase shift completed successfully!")
        print(f"Output MS: {output_path}")
        print(f"MS is now phase-shifted to Sun's coordinates")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

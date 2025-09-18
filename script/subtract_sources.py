#!/usr/bin/env python3
"""
Minimal script to subtract sources from MS using DP3 Predict step.
Uses the 'subtract' operation to remove model sources from visibilities.
"""

import subprocess
import sys
from pathlib import Path
import tempfile

def subtract_sources_dp3(ms_file, source_file, output_ms=None):
    """
    Subtract sources from MS using DP3 Predict step with 'subtract' operation.
    
    Args:
        ms_file (str): Path to input measurement set
        source_file (str): Path to source list file (WSClean format)
        output_ms (str, optional): Path to output MS. If None, uses input_subtracted.ms
    
    Returns:
        str: Path to output measurement set
    """
    ms_path = Path(ms_file)
    source_path = Path(source_file)
    
    # Validate inputs
    if not ms_path.exists():
        raise FileNotFoundError(f"MS file not found: {ms_path}")
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    # Set output MS name
    if output_ms is None:
        output_ms = ms_path.parent / f"{ms_path.stem}_subtracted.ms"
    else:
        output_ms = Path(output_ms)
    
    # Convert WSClean source list to makesourcedb format if needed
    # For simplicity, we'll assume the source file is already in the right format
    # or DP3 can handle WSClean format directly
    
    
    # Find common parent directory for mounting
    ms_abs = ms_path.resolve()
    source_abs = source_path.resolve()
    output_abs = output_ms.resolve()
    
    # Find common parent
    common_parts = []
    ms_parts = ms_abs.parts
    source_parts = source_abs.parts
    output_parts = output_abs.parts
    
    for i in range(min(len(ms_parts), len(source_parts), len(output_parts))):
        if ms_parts[i] == source_parts[i] == output_parts[i]:
            common_parts.append(ms_parts[i])
        else:
            break
    
    if not common_parts:
        # Fallback: use root directory
        common_parent = Path("/")
    else:
        common_parent = Path(*common_parts)
    
    print(f"Input MS: {ms_abs}")
    print(f"Source file: {source_abs}")
    print(f"Output MS: {output_abs}")
    print(f"Common parent for mounting: {common_parent}")
    
    # Calculate relative paths from common parent
    ms_rel = ms_abs.relative_to(common_parent)
    source_rel = source_abs.relative_to(common_parent)
    output_rel = output_abs.relative_to(common_parent)
    
    # Update parset with relative paths
    parset_content = f"""
msin = /data/{ms_rel}
msout = /data/{output_rel}

steps = [predict]

predict.type = predict
predict.sourcedb = /data/{source_rel}
predict.operation = subtract
"""
    
    # Write parset to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.parset', delete=False) as f:
        f.write(parset_content)
        parset_file = Path(f.name)
    
    try:
        print(f"\nDP3 Parset contents:")
        print(parset_content)
        
        # Copy parset to common parent for container access
        container_parset = common_parent / "subtract_sources.parset"
        with open(container_parset, 'w') as f:
            f.write(parset_content)
        
        # Run DP3 in container
        cmd = [
            "podman", "run", "--rm",
            "-v", f"{common_parent}:/data",
            "-w", "/data",
            "astronrd/linc:latest",
            "DP3", "subtract_sources.parset"
        ]
        
        print(f"\nRunning DP3 command:")
        print(" ".join(cmd))
        print()
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("DP3 failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            raise RuntimeError(f"DP3 failed with exit code {result.returncode}")
        
        print("DP3 completed successfully!")
        print("STDOUT:", result.stdout)
        
        # Clean up parset file
        container_parset.unlink()
        
        return str(output_abs)
        
    finally:
        # Clean up temporary parset
        if parset_file.exists():
            parset_file.unlink()

def main():
    """Main function for command line usage."""
    if len(sys.argv) < 3:
        print("Usage: python subtract_sources.py <ms_file> <source_file> [output_ms]")
        print("Example: python subtract_sources.py data.ms sources.txt data_subtracted.ms")
        sys.exit(1)
    
    ms_file = sys.argv[1]
    source_file = sys.argv[2]
    output_ms = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        output_path = subtract_sources_dp3(ms_file, source_file, output_ms)
        print(f"\nSubtraction completed successfully!")
        print(f"Output MS: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

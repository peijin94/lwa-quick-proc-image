#!/usr/bin/env python3
"""
Command-line tool to convert UVH5 file to MS format using pyuvdata.

Usage:
    python uvh5_to_ms.py <input_uvh5> [options]
    
Examples:
    python uvh5_to_ms.py data.uvh5
    python uvh5_to_ms.py data.uvh5 --output data.ms
    python uvh5_to_ms.py data.uvh5 --force

Requires conda environment: conda activate /opt/devel/peijin/solarml
"""

import os
import sys
import argparse
from pathlib import Path
from pyuvdata import UVData

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Convert UVH5 file to MS format")
    parser.add_argument('input_uvh5', help='Input UVH5 file path')
    parser.add_argument('--output', '-o', help='Output MS file path', default=None)
    parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    return parser.parse_args()

def uvh5_to_ms(in_uvh5, out_ms, verbose=False):
    """
    Convert UVH5 file to MS format using pyuvdata.
    
    Args:
        in_uvh5 (str): Input UVH5 file path
        out_ms (str): Output MS file path
        verbose (bool): Enable verbose output
    """
    try:
        # Load UVH5 file with pyuvdata
        uv = UVData()
        uv.read_uvh5(in_uvh5)
        
        # Convert to MS
        uv.write_ms(out_ms)
        
        return out_ms
        
    except Exception as e:
        print(f"Error during UVH5 to MS conversion: {e}")
        raise

def main():
    """Main function for command-line tool."""
    args = parse_arguments()
    
    # Validate input file
    input_uvh5 = Path(args.input_uvh5)
    if not input_uvh5.exists():
        print(f"Error: Input UVH5 file '{input_uvh5}' does not exist.")
        sys.exit(1)
    
    if not input_uvh5.suffix == '.uvh5':
        print(f"Error: Input file '{input_uvh5}' does not have .uvh5 extension.")
        sys.exit(1)
    
    # Set up output path
    if args.output:
        output_ms = Path(args.output)
    else:
        output_ms = input_uvh5.parent / f"{input_uvh5.stem}.ms"
    
    # Check for existing files
    if not args.force:
        if output_ms.exists():
            print(f"Error: Output MS file '{output_ms}' already exists. Use --force to overwrite.")
            sys.exit(1)
    
    # Clean up existing files if force is specified
    if args.force and output_ms.exists():
        import shutil
        shutil.rmtree(output_ms)
    
    try:
        uvh5_to_ms(str(input_uvh5), str(output_ms), verbose=args.verbose)
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

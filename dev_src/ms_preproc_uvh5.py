#!/usr/bin/env python3
"""
Command-line tool to convert MS file to UVH5 format using pyuvdata.

Usage:
    python ms_preproc_uvh5.py <input_ms> [options]
    
Examples:
    python ms_preproc_uvh5.py data.ms
    python ms_preproc_uvh5.py data.ms --output data.uvh5

Requires conda environment: conda activate /opt/devel/peijin/solarml
"""

import os
import sys
import argparse
from pathlib import Path
from pyuvdata import UVData

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Convert MS file to UVH5 format")
    parser.add_argument('input_ms', help='Input MS file path')
    parser.add_argument('--output', '-o', help='Output UVH5 file path', default=None)
    parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    return parser.parse_args()


def ms_to_uvh5(in_ms, out_uvh5, verbose=False):
    """
    Convert MS file to UVH5 format using pyuvdata.
    
    Args:
        in_ms (str): Input MS file path
        out_uvh5 (str): Output UVH5 file path
        verbose (bool): Enable verbose output
    """
    try:
        # Load MS file with pyuvdata
        uv = UVData()
        uv.read_ms(in_ms)
        
        # Convert to uvh5
        uv.write_uvh5(out_uvh5)
        
        return out_uvh5
        
    except Exception as e:
        print(f"Error during MS to UVH5 conversion: {e}")
        raise

def main():
    """Main function for command-line tool."""
    args = parse_arguments()
    
    # Validate input file
    input_ms = Path(args.input_ms)
    if not input_ms.exists():
        print(f"Error: Input MS file '{input_ms}' does not exist.")
        sys.exit(1)
    
    if not input_ms.suffix == '.ms':
        print(f"Error: Input file '{input_ms}' does not have .ms extension.")
        sys.exit(1)
    
    # Set up output path
    if args.output:
        output_uvh5 = Path(args.output)
    else:
        output_uvh5 = input_ms.parent / f"{input_ms.stem}.uvh5"
    
    # Check for existing files
    if not args.force:
        if output_uvh5.exists():
            print(f"Error: Output UVH5 file '{output_uvh5}' already exists. Use --force to overwrite.")
            sys.exit(1)
    
    # Clean up existing files if force is specified
    if args.force and output_uvh5.exists():
        output_uvh5.unlink()
    
    try:
        ms_to_uvh5(str(input_ms), str(output_uvh5), verbose=args.verbose)
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Minimal script to plot FITS images
Supports various FITS files from WSClean output
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def plot_fits(fits_file, output_png=None, vmin=None, vmax=None, cmap='viridis'):
    """
    Plot FITS image with automatic scaling
    
    Args:
        fits_file: Path to FITS file
        output_png: Output PNG file (optional, defaults to fits_file.png)
        vmin, vmax: Color scale limits (optional, auto-scaled if None)
        cmap: Colormap to use
    """
    
    try:
        from astropy.io import fits
    except ImportError:
        print("Error: astropy is required. Install with: pip install astropy")
        sys.exit(1)
    
    fits_path = Path(fits_file)
    if not fits_path.exists():
        print(f"Error: FITS file not found: {fits_file}")
        sys.exit(1)
    
    # Read FITS file
    print(f"Reading {fits_file}...")
    with fits.open(fits_file) as hdul:
        data = hdul[0].data
        header = hdul[0].header
    
    # Handle different FITS dimensions
    if data.ndim == 4:
        # Remove degenerate axes (frequency, polarization)
        data = np.squeeze(data)
    elif data.ndim == 3:
        data = np.squeeze(data)
    
    if data.ndim != 2:
        print(f"Error: Expected 2D image, got {data.ndim}D data")
        sys.exit(1)
    
    # Remove NaN values for scaling
    finite_data = data[np.isfinite(data)]
    if len(finite_data) == 0:
        print("Error: No finite values in image")
        sys.exit(1)
    
    # Auto-scale if not provided
    if vmin is None or vmax is None:
        # Use percentile-based scaling to avoid outliers
        vmin_auto = np.percentile(finite_data, 1)
        vmax_auto = np.percentile(finite_data, 99)
        
        if vmin is None:
            vmin = vmin_auto
        if vmax is None:
            vmax = vmax_auto
    
    # Create plot
    plt.figure(figsize=(10, 8))
    
    # Display image
    im = plt.imshow(data, origin='lower', cmap=cmap, vmin=vmin, vmax=vmax)
    
    # Add colorbar
    plt.colorbar(im, label='Intensity')
    
    # Add title with file info
    title = fits_path.name
    if 'OBJECT' in header:
        title += f" ({header['OBJECT']})"
    if 'CTYPE1' in header and 'CTYPE2' in header:
        title += f"\n{header['CTYPE1']} vs {header['CTYPE2']}"
    
    plt.title(title)
    plt.xlabel('X pixel')
    plt.ylabel('Y pixel')
    
    # Set output filename
    if output_png is None:
        output_png = fits_path.with_suffix('.png')
    
    # Save plot
    plt.tight_layout()
    plt.savefig(output_png, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_png}")
    
    # Show statistics
    print(f"Image shape: {data.shape}")
    print(f"Data range: {np.nanmin(data):.3e} to {np.nanmax(data):.3e}")
    print(f"Plot range: {vmin:.3e} to {vmax:.3e}")
    
    # Optional: show plot
    # plt.show()
    
    plt.close()

def plot_all_fits(prefix_or_dir, output_dir=None):
    """
    Plot all FITS files with a given prefix or in a directory
    
    Args:
        prefix_or_dir: Either a file prefix (e.g., "image") or directory path
        output_dir: Directory to save PNG files (optional)
    """
    
    path = Path(prefix_or_dir)
    
    if path.is_dir():
        # Plot all FITS files in directory
        fits_files = list(path.glob("*.fits"))
    else:
        # Treat as prefix and find matching files
        parent_dir = path.parent if path.parent != Path('.') else Path.cwd()
        pattern = f"{path.name}*.fits"
        fits_files = list(parent_dir.glob(pattern))
    
    if not fits_files:
        print(f"No FITS files found matching: {prefix_or_dir}")
        return
    
    print(f"Found {len(fits_files)} FITS files:")
    
    for fits_file in sorted(fits_files):
        print(f"  Processing: {fits_file.name}")
        
        # Determine output path
        if output_dir:
            output_png = Path(output_dir) / fits_file.with_suffix('.png').name
        else:
            output_png = fits_file.with_suffix('.png')
        
        # Choose colormap based on file type
        if 'psf' in fits_file.name.lower():
            cmap = 'hot'
        elif 'residual' in fits_file.name.lower():
            cmap = 'RdBu_r'
        else:
            cmap = 'viridis'
        
        try:
            plot_fits(fits_file, output_png, cmap=cmap)
        except Exception as e:
            print(f"  Error plotting {fits_file.name}: {e}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 plot_fits.py <fits_file_or_prefix> [output_png]")
        print("Examples:")
        print("  python3 plot_fits.py image-image.fits")
        print("  python3 plot_fits.py image  # plots all image*.fits files")
        print("  python3 plot_fits.py /path/to/fits/dir/  # plots all *.fits in directory")
        sys.exit(1)
    
    input_arg = sys.argv[1]
    
    # Check if it's a single file or pattern/directory
    if input_arg.endswith('.fits') and Path(input_arg).is_file():
        # Single FITS file
        output_png = sys.argv[2] if len(sys.argv) > 2 else None
        plot_fits(input_arg, output_png)
    else:
        # Multiple files (prefix or directory)
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        plot_all_fits(input_arg, output_dir)

if __name__ == "__main__":
    main()

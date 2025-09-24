#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
import sys
from pathlib import Path

def plot_solar_image(fits_file, output_plot=None):
    """
    Plot solar radio image with statistics from upper right corner.
    
    Args:
        fits_file (str): Path to FITS image file
        output_plot (str, optional): Output plot filename. If None, auto-generated
    
    Returns:
        str: Path to saved plot
    """
    fits_path = Path(fits_file)
    
    # Validate input
    if not fits_path.exists():
        raise FileNotFoundError(f"FITS file not found: {fits_path}")
    
    # Load the image
    with fits.open(fits_path) as hdul:
        data = hdul[0].data
    
    # Handle different data dimensions
    if data.ndim == 4:
        data = data[0, 0]  # Remove frequency and Stokes dimensions
    elif data.ndim == 3:
        data = data[0]     # Remove one extra dimension
    elif data.ndim != 2:
        raise ValueError(f"Unexpected data dimensions: {data.shape}")
    
    # Calculate statistics from upper right corner 20% × 20% area for RMS
    height, width = data.shape
    corner_size_y = int(height * 0.2)
    corner_size_x = int(width * 0.2)
    
    # Upper right corner region for RMS calculation
    corner_data = data[-corner_size_y:, -corner_size_x:]
    corner_rms = np.nanstd(corner_data)
    
    # Overall statistics using corner RMS
    peak_val = np.nanmax(data)
    rms_val = corner_rms  # Use corner RMS instead of overall RMS
    dynamic_range = peak_val / rms_val if rms_val > 0 else 0

    # Create single plot
    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    
    # Plot image
    im = ax.imshow(data, origin='lower', cmap='hot', aspect='equal')
    ax.contour(data, levels=[-0.05*np.nanmax(data),0.05*np.nanmax(data)], colors='white', linewidths=0.5)
    plt.setp(ax, xlabel='X pixels', ylabel='Y pixels')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, label='Brightness (Jy/beam)')

    # Add overall statistics text (using corner RMS for calculation)
    stats_text = f'Peak: {peak_val:.2e} Jy/beam\nRMS: {rms_val:.2e} Jy/beam\nDR: {dynamic_range:.1f} \nmax/(-min): {-peak_val/np.nanmin(data):.1f}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9), fontsize=10)
    
    plt.tight_layout()
    
    # Set output filename
    if output_plot is None:
        output_plot = fits_path.parent / f"{fits_path.stem}_plot.png"
    else:
        output_plot = Path(output_plot)
    
    # Save plot
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    plt.close()  # Close to free memory
    
    print(f"Solar image plot saved to: {output_plot}")
    return str(output_plot)

def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python plot_solar_image.py <fits_file> [output_plot]")
        print("Example: python plot_solar_image.py sun_img-image.fits sun_plot.png")
        sys.exit(1)
    
    fits_file = sys.argv[1]
    output_plot = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        plot_path = plot_solar_image(fits_file, output_plot)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

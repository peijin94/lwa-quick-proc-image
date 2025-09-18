#!/usr/bin/env python3
"""
Script to plot solar radio images from WSClean FITS files.
"""

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
import sys
from pathlib import Path

def plot_solar_image(fits_file, output_plot=None, zoom_size=200):
    """
    Plot solar radio image with full view and zoomed view.
    
    Args:
        fits_file (str): Path to FITS image file
        output_plot (str, optional): Output plot filename. If None, auto-generated
        zoom_size (int): Size of zoom region around center (default: 200 pixels)
    
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
        header = hdul[0].header
    
    # Handle different data dimensions
    if data.ndim == 4:
        data = data[0, 0]  # Remove frequency and Stokes dimensions
    elif data.ndim == 3:
        data = data[0]     # Remove one extra dimension
    elif data.ndim != 2:
        raise ValueError(f"Unexpected data dimensions: {data.shape}")
    
    print(f"Image shape: {data.shape}")
    print(f"Min value: {np.nanmin(data):.3e}")
    print(f"Max value: {np.nanmax(data):.3e}")
    print(f"RMS (std): {np.nanstd(data):.3e}")
    
    # Calculate statistics
    clean_data = data[~np.isnan(data)]
    if len(clean_data) > 0:
        peak_val = np.max(clean_data)
        rms_val = np.nanstd(data)
        dynamic_range = peak_val / rms_val if rms_val > 0 else 0
        
        print(f"Peak brightness: {peak_val:.3e}")
        print(f"Dynamic range: {dynamic_range:.1f}")
        
        # Find peak location
        peak_loc = np.unravel_index(np.nanargmax(data), data.shape)
        print(f"Peak location (pixels): {peak_loc}")
    
    # Create plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Full image
    im1 = ax1.imshow(data, origin='lower', cmap='hot', aspect='equal', vmin=0, vmax=np.nanmax(data))
    ax1.contour(data, levels=[-0.05*np.nanmax(data),0.05*np.nanmax(data)], colors='white', linewidths=0.5)
    ax1.set_title('Sun')
    ax1.set_xlabel('X pix')
    ax1.set_ylabel('Y pix')
    
    # Zoomed view around center
    center_y, center_x = data.shape[0] // 2, data.shape[1] // 2
    y_start = max(0, center_y - zoom_size)
    y_end = min(data.shape[0], center_y + zoom_size)
    x_start = max(0, center_x - zoom_size)
    x_end = min(data.shape[1], center_x + zoom_size)
    
    zoom_data = data[y_start:y_end, x_start:x_end]
    im2 = ax2.imshow(zoom_data, origin='lower', cmap='hot', aspect='equal', vmin=0, vmax=np.nanmax(zoom_data))
    ax2.contour(zoom_data, levels=[-0.05*np.nanmax(zoom_data),0.05*np.nanmax(zoom_data)], colors='white', linewidths=0.5)
    ax2.set_title(f'(Zoomed)')
    ax2.set_xlabel('X pix')
    ax2.set_ylabel('Y pix')
    
    # Add text with statistics
    stats_text = f'Peak: {peak_val:.2e} Jy/beam\nRMS: {rms_val:.2e} Jy/beam\nDR: {dynamic_range:.1f}'
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
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
        print("Usage: python plot_solar_image.py <fits_file> [output_plot] [zoom_size]")
        print("Example: python plot_solar_image.py sun_img-image.fits sun_plot.png 150")
        sys.exit(1)
    
    fits_file = sys.argv[1]
    output_plot = sys.argv[2] if len(sys.argv) > 2 else None
    zoom_size = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    
    try:
        plot_path = plot_solar_image(fits_file, output_plot, zoom_size)
        print(f"\nPlot created successfully: {plot_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

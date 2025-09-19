#!/usr/bin/env python3
"""
Plot FITS image with source positions overlaid from WSClean source list
"""
import argparse
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

def load_wsclean_sources(sourcelist_fname):
    """
    Load WSClean source list and return coordinates and properties
    
    Returns:
        dict: Dictionary with source information including RA, DEC, flux
    """
    sources = []
    
    with open(sourcelist_fname, 'r') as f:
        lines = f.readlines()
    
    # Skip header line
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # WSClean format: Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, ReferenceFrequency, MajorAxis, MinorAxis, Orientation
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 5:
            try:
                name = parts[0]
                source_type = parts[1]
                ra_str = parts[2]  # Could be HMS format or degrees
                dec_str = parts[3]  # Could be DMS format or degrees
                flux_jy = float(parts[4])  # Jy
                
                # Convert coordinates to decimal degrees
                # WSClean format: RA in HMS with colons, DEC in DMS with periods
                
                # Handle RA (always HMS format with colons)
                if ':' in ra_str:
                    ra_formatted = ra_str  # Already in correct format
                else:
                    # Convert decimal to string if needed
                    ra_deg = float(ra_str)
                    ra_formatted = None
                
                # Handle DEC (DMS with periods, needs conversion)
                if '.' in dec_str and dec_str.count('.') >= 2:
                    # Convert DD.MM.SS.sss to DD:MM:SS.sss
                    dec_parts = dec_str.split('.')
                    if len(dec_parts) >= 3:
                        dec_formatted = f"{dec_parts[0]}:{dec_parts[1]}:{'.'.join(dec_parts[2:])}"
                    else:
                        dec_formatted = None
                        dec_deg = float(dec_str)
                elif ':' in dec_str:
                    dec_formatted = dec_str  # Already in correct format
                else:
                    # Decimal degrees
                    dec_formatted = None
                    dec_deg = float(dec_str)
                
                # Parse using SkyCoord if we have formatted strings
                if ra_formatted and dec_formatted:
                    coord = SkyCoord(ra=ra_formatted, dec=dec_formatted, unit=(u.hourangle, u.deg))
                    ra_deg = coord.ra.deg
                    dec_deg = coord.dec.deg
                elif ra_formatted and not dec_formatted:
                    # Mixed format: HMS RA, decimal DEC
                    coord = SkyCoord(ra=ra_formatted, dec=dec_deg*u.deg, unit=(u.hourangle, u.deg))
                    ra_deg = coord.ra.deg
                    # dec_deg already set above
                elif not ra_formatted and dec_formatted:
                    # Mixed format: decimal RA, DMS DEC
                    coord = SkyCoord(ra=ra_deg*u.deg, dec=dec_formatted, unit=(u.deg, u.deg))
                    # ra_deg already set above
                    dec_deg = coord.dec.deg
                # else: both are decimal degrees, already set above
                
                sources.append({
                    'name': name,
                    'type': source_type,
                    'ra': ra_deg,
                    'dec': dec_deg,
                    'flux': flux_jy
                })
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse line: {line[:50]}... Error: {e}")
                continue
    
    return sources

def plot_fits_with_sources(fits_file, source_list_file, output_file=None, 
                          source_color='red', source_size=50, flux_scale=True):
    """
    Plot FITS image with source positions overlaid
    
    Args:
        fits_file (str): Path to FITS image file
        source_list_file (str): Path to WSClean source list
        output_file (str): Output plot filename (optional)
        source_color (str): Color for source markers
        source_size (float): Base size for source markers
        flux_scale (bool): Scale marker size by flux
    """
    
    # Load FITS image
    with fits.open(fits_file) as hdul:
        image_data = hdul[0].data
        header = hdul[0].header
        
        # Handle different FITS dimensions (remove extra axes)
        while image_data.ndim > 2:
            image_data = image_data[0]
    
    # Create WCS object
    wcs = WCS(header, naxis=2)
    
    # Load sources
    sources = load_wsclean_sources(source_list_file)
    print(f"Loaded {len(sources)} sources from {source_list_file}")
    
    if len(sources) == 0:
        print("Warning: No sources found in source list")
    
    # Create the plot
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection=wcs)
    
    # Plot the image
    image_data_clean = np.where(np.isfinite(image_data), image_data, 0)
    
    # Auto-scale for better contrast
    vmin = np.percentile(image_data_clean[image_data_clean != 0], 1)
    vmax = np.percentile(image_data_clean[image_data_clean != 0], 99)
    
    im = ax.imshow(image_data, origin='lower', cmap='gray', 
                   vmin=vmin, vmax=vmax, aspect='equal')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Brightness (Jy/beam)', rotation=270, labelpad=20)
    
    # Plot sources
    if sources:
        source_coords = SkyCoord(
            ra=[s['ra'] for s in sources] * u.deg,
            dec=[s['dec'] for s in sources] * u.deg
        )
        
        # Convert to pixel coordinates
        # world_to_pixel returns (x, y) where x=RA, y=DEC in pixel space
        pixel_coords = wcs.world_to_pixel(source_coords)
        x_pix, y_pix = pixel_coords
        
        # Calculate marker sizes
        if flux_scale and len(sources) > 0:
            fluxes = np.array([s['flux'] for s in sources])
            # Normalize flux to reasonable marker sizes
            flux_norm = (fluxes - fluxes.min()) / (fluxes.max() - fluxes.min() + 1e-10)
            marker_sizes = source_size * (0.5 + 1.5 * flux_norm)  # 0.5x to 2x base size
        else:
            marker_sizes = [source_size] * len(sources)
        
        # Plot source positions
        scatter = ax.scatter(x_pix, y_pix, s=marker_sizes, c=source_color, 
                           marker='o', alpha=0.8, edgecolors='white', 
                           linewidth=1, label=f'{len(sources)} sources')
        
        # Add text labels for bright sources
        bright_sources = [s for s in sources if s['flux'] > np.percentile([s['flux'] for s in sources], 90)]
        for i, source in enumerate(bright_sources[:10]):  # Limit to top 10 bright sources
            idx = sources.index(source)
            ax.annotate(f"{source['flux']:.2f} Jy", 
                       (x_pix[idx], y_pix[idx]), 
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=8, color='white', 
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))
    
    # Set labels and title
    ax.set_xlabel('RA (J2000)', fontsize=12)
    ax.set_ylabel('DEC (J2000)', fontsize=12)
    
    fits_name = Path(fits_file).stem
    sources_name = Path(source_list_file).stem
    ax.set_title(f'FITS: {fits_name}\nSources: {sources_name}', fontsize=14)
    
    # Add grid
    ax.grid(True, alpha=0.3)
    ax.coords.grid(True, color='white', alpha=0.3)
    
    # Add legend
    if sources:
        ax.legend(loc='upper right', bbox_to_anchor=(1, 1))
    
    # Add statistics
    stats_text = f"Image stats:\n"
    stats_text += f"Peak: {np.nanmax(image_data_clean):.2e} Jy/beam\n"
    stats_text += f"RMS: {np.nanstd(image_data_clean):.2e} Jy/beam\n"
    if len(sources) > 0:
        total_flux = sum(s['flux'] for s in sources)
        stats_text += f"Total source flux: {total_flux:.2f} Jy"
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            verticalalignment='top', fontsize=10,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # Save plot
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    else:
        # Auto-generate filename
        fits_path = Path(fits_file)
        auto_output = fits_path.parent / f"{fits_path.stem}_with_sources.png"
        plt.savefig(auto_output, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {auto_output}")
    
    plt.close()  # Close the figure to free memory

def main():
    parser = argparse.ArgumentParser(description='Plot FITS image with source positions overlaid')
    parser.add_argument('fits_file', help='Path to FITS image file')
    parser.add_argument('source_list', help='Path to WSClean source list file')
    parser.add_argument('-o', '--output', help='Output plot filename')
    parser.add_argument('--color', default='red', help='Source marker color (default: red)')
    parser.add_argument('--size', type=float, default=50, help='Base marker size (default: 50)')
    parser.add_argument('--no-flux-scale', action='store_true', 
                       help='Do not scale marker size by flux')
    
    args = parser.parse_args()
    
    # Check input files exist
    if not Path(args.fits_file).exists():
        print(f"Error: FITS file not found: {args.fits_file}")
        sys.exit(1)
    
    if not Path(args.source_list).exists():
        print(f"Error: Source list file not found: {args.source_list}")
        sys.exit(1)
    
    plot_fits_with_sources(
        args.fits_file, 
        args.source_list, 
        args.output,
        source_color=args.color,
        source_size=args.size,
        flux_scale=not args.no_flux_scale
    )

if __name__ == "__main__":
    main()

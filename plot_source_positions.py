#!/usr/bin/env python3
"""
Plot RA-DEC positions of sources from a WSClean source list file
"""

import sys
import argparse
from pathlib import Path
import numpy as np

# Add current directory to path to import source_list
sys.path.insert(0, str(Path(__file__).parent))

import source_list

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.colors import LogNorm
except ImportError:
    print("Error: matplotlib is required but not installed.")
    print("Please install it with: pip install matplotlib")
    sys.exit(1)

def plot_source_positions(sourcelist_file, output_file=None, show_flux=True, sun_position=None, sun_radius_deg=None):
    """
    Plot RA-DEC positions of sources from a source list file
    
    Args:
        sourcelist_file: Path to WSClean source list file
        output_file: Output plot filename (optional)
        show_flux: Whether to scale points by flux density
        sun_position: Tuple of (ra_deg, dec_deg) for Sun position (optional)
        sun_radius_deg: Radius in degrees to draw around Sun position (optional)
    """
    
    # Load sources
    try:
        sources = source_list.load_wsclean_sources(sourcelist_file)
        print(f"Loaded {len(sources)} sources from {sourcelist_file}")
    except Exception as e:
        print(f"Error loading sources: {e}")
        return False
    
    if len(sources) == 0:
        print("No sources found in file")
        return False
    
    # Extract coordinates and flux
    ra_list = [src['ra_deg'] for src in sources]
    dec_list = [src['dec_deg'] for src in sources]
    flux_list = [src['flux'] for src in sources]
    names = [src['name'] for src in sources]
    
    ra_array = np.array(ra_list)
    dec_array = np.array(dec_list)
    flux_array = np.array(flux_list)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Determine point sizes and colors
    if show_flux and np.any(flux_array > 0):
        # Scale point sizes by flux (with minimum size)
        flux_nonzero = flux_array[flux_array > 0]
        if len(flux_nonzero) > 0:
            flux_min, flux_max = np.min(flux_nonzero), np.max(flux_nonzero)
            sizes = np.where(flux_array > 0, 
                           20 + 100 * (flux_array - flux_min) / (flux_max - flux_min),
                           10)  # Minimum size for zero flux
            # Color by flux
            colors = np.where(flux_array > 0, flux_array, flux_min/10)
            scatter = ax.scatter(ra_array, dec_array, s=sizes, c=colors, 
                               cmap='viridis', alpha=0.7, norm=LogNorm(vmin=flux_min/10, vmax=flux_max))
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Flux Density (Jy)', fontsize=12)
        else:
            # All flux values are zero or negative
            ax.scatter(ra_array, dec_array, s=20, c='blue', alpha=0.7)
    else:
        # Uniform point sizes
        ax.scatter(ra_array, dec_array, s=30, c='blue', alpha=0.7)
    
    # Add Sun position if provided
    if sun_position is not None:
        sun_ra, sun_dec = sun_position
        ax.scatter(sun_ra, sun_dec, s=200, c='red', marker='*', 
                  label=f'Sun (RA={sun_ra:.2f}°, DEC={sun_dec:.2f}°)', 
                  edgecolors='black', linewidth=1)
        
        # Add circle around Sun if radius is provided
        if sun_radius_deg is not None:
            circle = patches.Circle((sun_ra, sun_dec), sun_radius_deg, 
                                  fill=False, color='red', linestyle='--', 
                                  linewidth=2, alpha=0.8, 
                                  label=f'Sun exclusion zone ({sun_radius_deg}°)')
            ax.add_patch(circle)
    
    # Formatting
    ax.set_xlabel('Right Ascension (degrees)', fontsize=12)
    ax.set_ylabel('Declination (degrees)', fontsize=12)
    ax.set_title(f'Source Positions: {Path(sourcelist_file).name}\n({len(sources)} sources)', fontsize=14)
    ax.grid(True, alpha=0.3)
    
    # Set coordinate limits to standard astronomical ranges
    ax.set_xlim(360, 0)  # RA 0-360°, inverted (standard astronomical convention)
    ax.set_ylim(-90, 90)  # DEC -90° to +90°
    
    # Set aspect ratio to be equal in sky coordinates (approximately)
    # Account for declination projection
    dec_center = np.mean(dec_array)
    ax.set_aspect(1.0 / np.cos(np.radians(dec_center)))
    
    # Add legend if Sun is shown
    if sun_position is not None:
        ax.legend(loc='upper right')
    
    # Add statistics text
    stats_text = f"RA range: {np.min(ra_array):.2f}° to {np.max(ra_array):.2f}°\n"
    stats_text += f"DEC range: {np.min(dec_array):.2f}° to {np.max(dec_array):.2f}°"
    if show_flux and np.any(flux_array > 0):
        flux_nonzero = flux_array[flux_array > 0]
        stats_text += f"\nFlux range: {np.min(flux_nonzero):.3f} to {np.max(flux_nonzero):.3f} Jy"
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()
    return True

def plot_with_sun_masking(sourcelist_file, time_mjd, distance_deg=8.0, observatory='OVRO', output_file=None):
    """
    Plot sources with Sun position and masking radius
    
    Args:
        sourcelist_file: Path to source list file
        time_mjd: Time in MJD to calculate Sun position
        distance_deg: Masking radius around Sun in degrees
        observatory: Observatory name for Sun position calculation
        output_file: Output plot filename (optional)
    """
    
    print(f"Plotting sources with Sun masking...")
    print(f"Time (MJD): {time_mjd}")
    print(f"Observatory: {observatory}")
    print(f"Masking radius: {distance_deg}°")
    
    try:
        # Get Sun position
        sun_ra, sun_dec = source_list.get_Sun_RA_DEC(time_mjd, observatory)
        print(f"Sun position: RA={sun_ra:.4f}°, DEC={sun_dec:.4f}°")
        
        # Plot with Sun position
        success = plot_source_positions(
            sourcelist_file, 
            output_file=output_file,
            show_flux=True,
            sun_position=(sun_ra, sun_dec),
            sun_radius_deg=distance_deg
        )
        
        if success:
            # Calculate and show masking statistics
            distances = source_list.distance_to_src_list(sourcelist_file, sun_ra, sun_dec)
            masked_sources = [src for src in distances if src['distance_deg'] <= distance_deg]
            total_sources = len(distances)
            masked_count = len(masked_sources)
            
            print(f"\nMasking statistics:")
            print(f"Total sources: {total_sources}")
            print(f"Sources within {distance_deg}° of Sun: {masked_count}")
            print(f"Percentage masked: {100*masked_count/total_sources:.1f}%")
            
        return success
        
    except Exception as e:
        print(f"Error in Sun masking plot: {e}")
        return False

def main():
    """Main function with command line interface"""
    
    parser = argparse.ArgumentParser(description='Plot RA-DEC positions of sources from WSClean source list')
    parser.add_argument('sourcelist', help='WSClean source list file')
    parser.add_argument('-o', '--output', help='Output plot filename')
    parser.add_argument('--no-flux', action='store_true', help='Do not scale points by flux')
    parser.add_argument('--sun-mjd', type=float, help='MJD time to show Sun position')
    parser.add_argument('--sun-radius', type=float, default=8.0, help='Sun masking radius in degrees (default: 8.0)')
    parser.add_argument('--observatory', default='OVRO', help='Observatory for Sun position (default: OVRO)')
    
    args = parser.parse_args()
    
    # Check if source list file exists
    sourcelist_path = Path(args.sourcelist)
    if not sourcelist_path.exists():
        print(f"Error: Source list file not found: {args.sourcelist}")
        sys.exit(1)
    
    # Plot with or without Sun
    if args.sun_mjd is not None:
        success = plot_with_sun_masking(
            args.sourcelist, 
            args.sun_mjd, 
            distance_deg=args.sun_radius,
            observatory=args.observatory,
            output_file=args.output
        )
    else:
        success = plot_source_positions(
            args.sourcelist,
            output_file=args.output,
            show_flux=not args.no_flux
        )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

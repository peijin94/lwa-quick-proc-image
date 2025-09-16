"""
Calculate angular distances between sources in a WSClean sources file
and a target RA/DEC position using astropy.
"""

from pathlib import Path
from astropy.coordinates import SkyCoord, EarthLocation, get_body
from astropy.time import Time
import astropy.units as u


def parse_wsclean_coordinates(ra_str, dec_str):
    """Parse WSClean coordinates to SkyCoord object."""
    # Convert DEC format DD.MM.SS to DD:MM:SS for astropy
    dec_str_astropy = dec_str.replace('.', ':', 2)
    return SkyCoord(ra_str, dec_str_astropy, unit=(u.hourangle, u.deg))


def load_wsclean_sources(filename):
    """Load sources from WSClean sources file."""
    sources = []
    with open(filename, 'r') as f:
        for line in f.readlines()[1:]:  # Skip header
            parts = line.strip().split(',')
            if len(parts) < 4:
                continue
            
            name, source_type, ra_str, dec_str = parts[:4]
            flux = float(parts[4]) if len(parts) > 4 else 0.0
            
            try:
                coord = parse_wsclean_coordinates(ra_str, dec_str)
                sources.append({
                    'name': name, 'coord': coord, 'flux': flux,
                    'ra_deg': coord.ra.deg, 'dec_deg': coord.dec.deg
                })
            except (ValueError, IndexError):
                continue
    return sources


def distance_to_src_list(sourcelist_fname, ra_deg, dec_deg):
    """Calculate distances from sources to target position.
    
    Args:
        sourcelist_fname: Path to WSClean sources file
        ra_deg, dec_deg: Target coordinates in degrees
    
    Returns:
        List of dicts with source info and distances
    """
    sourcelist_file = Path(sourcelist_fname)
    if not sourcelist_file.exists():
        raise FileNotFoundError(f"Sources file {sourcelist_file} not found")
    
    target_coord = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg)
    sources = load_wsclean_sources(sourcelist_file)
    
    results = []
    for source in sources:
        sep = source['coord'].separation(target_coord)
        results.append({
            **source,  # Include all source data
            'distance_deg': sep.deg,
            'distance_arcmin': sep.arcmin,
            'distance_arcsec': sep.arcsec
        })
    
    return results


def get_Sun_RA_DEC(time_mjd, observatory='OVRO'):
    """Get the RA and DEC of the Sun at a given time.
    
    Args:
        time_mjd (float): Time in Modified Julian Days
        observatory (str): Observatory name for astropy EarthLocation
    
    Returns:
        tuple: (ra_deg, dec_deg) Sun coordinates in degrees
    
    Example:
        >>> ra, dec = get_Sun_RA_DEC(59000.5)  # MJD
        >>> print(f"Sun at RA={ra:.4f}°, DEC={dec:.4f}°")
    """
    # Convert MJD to astropy Time object
    time = Time(time_mjd, format='mjd')
    
    # Get observatory location
    location = EarthLocation.of_site(observatory)
    
    # Get Sun position as seen from the observatory
    sun_coord = get_body('sun', time, location)
    
    # Extract RA and DEC in degrees
    ra_deg = sun_coord.ra.to(u.deg).value
    dec_deg = sun_coord.dec.to(u.deg).value
    
    return ra_deg, dec_deg




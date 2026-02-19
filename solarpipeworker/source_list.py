from __future__ import annotations

from pathlib import Path

import astropy.units as u
from astropy.coordinates import EarthLocation, SkyCoord, get_body
from astropy.time import Time

try:
    from casatools import table
except Exception:  # pragma: no cover - optional dependency in unit tests
    table = None


def parse_wsclean_coordinates(ra_str: str, dec_str: str) -> SkyCoord:
    dec_str_astropy = dec_str.replace(".", ":", 2)
    return SkyCoord(ra_str, dec_str_astropy, unit=(u.hourangle, u.deg))


def load_wsclean_sources(filename: str | Path) -> list[dict[str, float | str | SkyCoord]]:
    sources: list[dict[str, float | str | SkyCoord]] = []
    with Path(filename).open("r", encoding="utf-8") as f:
        for line in f.readlines()[1:]:
            parts = line.strip().split(",")
            if len(parts) < 4:
                continue
            name, source_type, ra_str, dec_str = parts[:4]
            flux = float(parts[4]) if len(parts) > 4 else 0.0
            try:
                coord = parse_wsclean_coordinates(ra_str, dec_str)
            except (ValueError, IndexError):
                continue
            sources.append(
                {
                    "name": name,
                    "type": source_type,
                    "coord": coord,
                    "flux": flux,
                    "ra_deg": coord.ra.deg,
                    "dec_deg": coord.dec.deg,
                }
            )
    return sources


def distance_to_src_list(
    sourcelist_fname: str | Path, ra_deg: float, dec_deg: float
) -> list[dict[str, float | str | SkyCoord]]:
    sourcelist_file = Path(sourcelist_fname)
    if not sourcelist_file.exists():
        raise FileNotFoundError(f"Sources file {sourcelist_file} not found")

    target_coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg)
    sources = load_wsclean_sources(sourcelist_file)

    result: list[dict[str, float | str | SkyCoord]] = []
    for source in sources:
        sep = source["coord"].separation(target_coord)  # type: ignore[index]
        out = dict(source)
        out["distance_deg"] = float(sep.deg)
        result.append(out)
    return result


def get_time_mjd(msname: str | Path) -> float:
    if table is None:
        raise RuntimeError("casatools is required for reading MS time")
    tb = table()
    tb.open(f"{msname}/OBSERVATION")
    start_mjd = tb.getcol("TIME_RANGE")[0][0] / 86400.0
    tb.close()
    return float(start_mjd)


def get_sun_ra_dec(time_mjd: float, observatory: str = "OVRO") -> tuple[float, float]:
    obs_time = Time(time_mjd, format="mjd")
    location = EarthLocation.of_site(observatory)
    sun_coord = get_body("sun", obs_time, location)
    return float(sun_coord.ra.to(u.deg).value), float(sun_coord.dec.to(u.deg).value)


def mask_far_sun_sources(
    sourcelist_fname: str | Path,
    fname_out: str | Path,
    ra_deg: float,
    dec_deg: float,
    distance_deg: float = 8.0,
) -> Path:
    dist_to_sun = distance_to_src_list(sourcelist_fname, ra_deg, dec_deg)
    sources_to_remove = {s["name"] for s in dist_to_sun if s["distance_deg"] <= distance_deg}

    in_path = Path(sourcelist_fname)
    out_path = Path(fname_out)
    with in_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    with out_path.open("w", encoding="utf-8") as f:
        for i, line in enumerate(lines):
            if i == 0:
                f.write(line)
                continue
            name = line.split(",")[0]
            if name not in sources_to_remove:
                f.write(line)

    return out_path

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits


def plot_solar_image(fits_file: str | Path, output_plot: str | Path | None = None) -> Path:
    fits_path = Path(fits_file)
    if not fits_path.exists():
        raise FileNotFoundError(f"FITS file not found: {fits_path}")

    with fits.open(fits_path) as hdul:
        data = hdul[0].data

    if data.ndim == 4:
        data = data[0, 0]
    elif data.ndim == 3:
        data = data[0]
    elif data.ndim != 2:
        raise ValueError(f"Unexpected data dimensions: {data.shape}")

    height, width = data.shape
    corner_size_y = int(height * 0.2)
    corner_size_x = int(width * 0.2)
    corner_data = data[-corner_size_y:, -corner_size_x:]

    peak_val = float(np.nanmax(data))
    rms_val = float(np.nanstd(corner_data))
    dynamic_range = peak_val / rms_val if rms_val > 0 else 0.0

    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    im = ax.imshow(data, origin="lower", cmap="hot", aspect="equal")
    ax.contour(
        data,
        levels=[-0.05 * np.nanmax(data), 0.05 * np.nanmax(data)],
        colors="white",
        linewidths=0.5,
    )
    ax.set(xlabel="X pixels", ylabel="Y pixels")
    plt.colorbar(im, ax=ax, shrink=0.8, label="Brightness (Jy/beam)")

    stats_text = (
        f"Peak: {peak_val:.2e} Jy/beam\n"
        f"RMS: {rms_val:.2e} Jy/beam\n"
        f"DR: {dynamic_range:.1f}\n"
        f"max/(-min): {-peak_val / np.nanmin(data):.1f}"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        verticalalignment="top",
        horizontalalignment="left",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
        fontsize=10,
    )
    plt.tight_layout()

    out_path = Path(output_plot) if output_plot is not None else fits_path.with_name(f"{fits_path.stem}_plot.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return out_path

# LWA Quick Processing Pipeline

A streamlined pipeline for processing LWA (Long Wavelength Array) radio astronomy data from raw measurement sets to calibrated solar images.

## Overview

This pipeline processes LWA measurement sets through the following steps:
1. **CASA bandpass calibration** - Apply pre-computed calibration tables
2. **DP3 flagging & averaging** - RFI flagging and frequency averaging  
3. **WSClean imaging** - Generate initial images and fill MODEL_DATA column
4. **DP3 gain calibration** - Phase and amplitude self-calibration
5. **Source subtraction** - Remove bright sources and phase-shift to Sun coordinates
6. **Solar imaging** - Generate final solar radio images

## Quick Start

```bash
python3 pipeline_quick_proc_img.py \
    /path/to/raw.ms \
    /path/to/bandpass.bcal \
    output_prefix
```

## Requirements

- **Podman** for containerized DP3/WSClean operations
- **astronrd/linc:latest** container image


## Output Files

The pipeline generates:
- **Calibrated MS**: `*_final.ms` - Final calibrated measurement set
- **Solution files**: `solution.h5` - DP3 calibration solutions  
- **FITS images**: `*image*.fits` - Radio images at various stages
- **Solar plots**: `*_plot.png` - Final solar image visualizations

## Configuration

Key parameters in `pipeline_quick_proc_img.py`:
- `niter=800` - WSClean iterations for initial imaging for selfcal
- `mgain=0.9` - Major cycle gain (must be < 1.0)
- `distance_deg=8.0` - Sun masking radius for source subtraction
- `horizon_mask=0.1` - Horizon masking in degrees

## Container Usage

All DP3 and WSClean operations use the `astronrd/linc:latest` container:

```bash
# Test container setup
podman pull astronrd/linc:latest

# Run individual steps
python3 script/run_dp3_flag_avg.py input.ms output.ms
python3 script/run_wsclean_imaging.py input.ms image_prefix
```

## Visualization Tools

```bash
# Plot solar image with statistics
python3 plot_solar_image.py solar_image.fits

# Overlay sources on FITS image  
python3 script/plot_fits_with_sources.py image.fits sources.txt

# Plot calibration solutions
python3 script/plot_solutions.py solution.h5
```

#!/usr/bin/env python3
"""
Minimal pipeline script for LWA data processing
Complete workflow: raw MS -> CASA applycal -> DP3 flag/avg -> wsclean -> gaincal -> applycal
"""
import subprocess
import sys
import os
import time
from pathlib import Path
import shutil
import wsclean_imaging
from source_list import get_time_mjd, get_Sun_RA_DEC, mask_far_Sun_sources

PIPELINE_SCRIPT_DIR = Path(__file__).parent
DEBUG = True

def base_DP3_cmd(common_parent):
    return ["podman", "run", "--rm",
        "-v", f"{common_parent}:/data",
        "-w", "/data", "astronrd/linc:latest"]

def run_casa_applycal(input_ms, gaintable):
    """Apply CASA bandpass calibration"""
    print(f"Step : CASA applycal - {input_ms}")
    start_time = time.time()
    
    casa_script = f"""
import casatools, casatasks
from ovrolwasolar import flagging
flagging.flag_bad_ants('{input_ms}')
casatasks.applycal( vis='{input_ms}',gaintable='{gaintable}', applymode='calflag' )
"""
    # Write and run CASA script
    script_file = Path("casa_applycal.py")
    with open(script_file, 'w') as f:
        f.write(casa_script)
    
    try:
        subprocess.run(["python3", str(script_file)], check=True)
        elapsed = time.time() - start_time
        print(f"✓ CASA applycal completed ({elapsed:.1f}s)")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ CASA applycal failed after {elapsed:.1f}s: {e}")
        sys.exit(1)
    finally:
        script_file.unlink(missing_ok=True)

def run_dp3_flag_avg(input_ms, output_ms, strategy_file=None):
    """DP3 flagging and frequency averaging"""
    print(f"Step : DP3 flag/avg - {input_ms} -> {output_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    output_path = Path(output_ms)

    # Find common parent directory
    common_parent = Path(os.path.commonpath([input_path.parent, output_path.parent]))
    
    if strategy_file is not None:
        strategy_file = Path(strategy_file)
        shutil.copy(strategy_file, common_parent / strategy_file.name)
        strategy_file = common_parent / strategy_file.name
        strategy_file_path_str = f"/data/{strategy_file.relative_to(common_parent)}" # inside the data dir
    else:
        strategy_file_path_str = "/usr/local/share/linc/rfistrategies/lofar-default.lua" # inside the container

    print(f"Strategy file: {strategy_file_path_str}")

    # Create DP3 parset in data directory
    parset_content = f"""msin = {input_path.relative_to(common_parent)}
msout = {output_path.relative_to(common_parent)}
msin.datacolumn=CORRECTED_DATA
steps = [flag, avg]
flag.type = aoflagger
flag.strategy = {strategy_file_path_str}
flag.keepstatistics = false
avg.type = averager
avg.freqstep = 4
"""
    
    parset_file = common_parent / "dp3_flag_avg.parset"
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    cmd = base_DP3_cmd(common_parent) + ["DP3", f"/data/{parset_file.name}"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        elapsed = time.time() - start_time
        print(f"✓ DP3 flag/avg completed ({elapsed:.1f}s): {output_ms}")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ DP3 flag/avg failed after {elapsed:.1f}s: {e}")
        sys.exit(1)
    finally:
        parset_file.unlink(missing_ok=True)

def run_wsclean_imaging(input_ms, output_prefix="image", auto_pix_fov=True, **kwargs):
    """WSClean imaging"""
    print(f"Step : WSClean imaging - {input_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    input_dir = input_path.parent
    
    # Generate WSClean command using utils
    wsclean_cmd_str = wsclean_imaging.make_wsclean_cmd(
        msfile=input_path,  imagename=output_prefix,
        auto_pix_fov=auto_pix_fov, **kwargs)
    
    # Split the command string into a list for subprocess
    wsclean_args = wsclean_cmd_str.split()[1:]  # Remove 'wsclean' from the beginning
    
    cmd = base_DP3_cmd(input_dir) + ["wsclean"] + wsclean_args + [f"/data/{input_path.name}"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        elapsed = time.time() - start_time
        print(f"✓ WSClean imaging completed ({elapsed:.1f}s): {output_prefix}*.fits")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ WSClean imaging failed after {elapsed:.1f}s: {e}")
        sys.exit(1)

def run_gaincal(input_ms, solution_fname="solution.h5", cal_type="diagonalphase"):
    """DP3 gain calibration"""
    print(f"Step : DP3 gaincal - {input_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    input_dir = input_path.parent
#msout = /data/{input_path.name}_cal.ms
    
    parset_content = f"""msin = {input_path.name}
steps = [gaincal]
msout = .
gaincal.solint = 0
gaincal.caltype = {cal_type}
gaincal.uvlambdamin = 20
gaincal.maxiter = 500
gaincal.tolerance = 1e-5
gaincal.usemodelcolumn = true
gaincal.modelcolumn = MODEL_DATA
gaincal.parmdb = {solution_fname}
"""
    
    parset_file = input_dir / "gaincal.parset"
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    cmd = base_DP3_cmd(input_dir) + ["DP3", f"/data/{parset_file.name}"]
    
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        elapsed = time.time() - start_time
        print(f"✓ DP3 gaincal completed ({elapsed:.1f}s): solution.h5")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ DP3 gaincal failed after {elapsed:.1f}s: {e}")
        sys.exit(1)
    finally:
        parset_file.unlink(missing_ok=True)

import h5py
import numpy as np

def reset_solution_outliers(h5fname, N_sigma=3, reset=True):
    start_time = time.time()
    with h5py.File(h5fname, 'r') as f:
        amp_val = f["sol000"]["amplitude000"]["val"][:]
        weight_val = f["sol000"]["amplitude000"]["weight"][:]
        
    for i in range(amp_val.shape[0]): # time
        for j in range(amp_val.shape[1]): # freq
            for k in range(amp_val.shape[3]): # pol
                outliers = np.where(
                    (amp_val[i,j,:,k] > np.nanmean(amp_val[i,j,:,k]) + N_sigma * np.nanstd(amp_val[i,j,:,k]))
                    | (amp_val[i,j,:,k] < np.nanmean(amp_val[i,j,:,k]) - N_sigma * np.nanstd(amp_val[i,j,:,k]))
                )[0]
                if reset:
                    amp_val[i,j,outliers,k] = np.nan
                    weight_val[i,j,outliers,k] = 0
                else:
                    amp_val[i,j,outliers,k] = 1
                    weight_val[i,j,outliers,k] = 0

    with h5py.File(h5fname ,'a') as f:
        f["sol000"]["amplitude000"]["val"][:] = amp_val
        f["sol000"]["amplitude000"]["weight"][:] = weight_val

    elapsed = time.time() - start_time
    print(f"✓ Reset solution outliers completed ({elapsed:.1f}s): {h5fname}")
    return h5fname

def run_applycal_dp3(input_ms,  output_ms, solution_fname="solution.h5", cal_entry_lst=["phase"]):
    """Apply DP3 calibration solutions"""
    print(f"Step : DP3 applycal - {input_ms} -> {output_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    output_path = Path(output_ms)
    
    # Find common parent directory
    common_parent = Path(os.path.commonpath([
        input_path.parent, output_path.parent
    ]))
    
    parset_content = f"""msin = {input_path.relative_to(common_parent)}
msout = {output_path.relative_to(common_parent)}
steps = [applycal]
applycal.parmdb = {solution_fname}
applycal.steps = [ {', '.join(cal_entry_lst)} ] \n
"""
    for cal_entry in cal_entry_lst:
        parset_content += f"applycal.{cal_entry}.correction={cal_entry}000 \n"
 
    parset_file = common_parent / "applycal.parset"
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    cmd = base_DP3_cmd(common_parent) + ["DP3", f"/data/{parset_file.name}"]
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - start_time
        print(f"✓ DP3 applycal completed ({elapsed:.1f}s): {output_ms}")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ DP3 applycal failed after {elapsed:.1f}s: {e}")
        sys.exit(1)
    finally:
        parset_file.unlink(missing_ok=True)


def run_dp3_subtract(input_ms, output_ms, source_list):
    """DP3 subtract"""
    print(f"Step : DP3 subtract - {input_ms} -> {output_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms).resolve()
    output_path = Path(output_ms).resolve()
    source_path = Path(source_list).resolve()
    
    # Find common parent directory
    common_parent = Path(os.path.commonpath([
        input_path.parent, output_path.parent, source_path.parent
    ]))
    
    parset_content = f"""msin = {input_path.relative_to(common_parent)}
msout = {output_path.relative_to(common_parent)}
steps = [predict]
predict.type = predict
predict.sourcedb = {source_path.relative_to(common_parent)}
predict.operation = subtract
"""
    
    parset_file = common_parent / "subtract.parset"
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    cmd = base_DP3_cmd(common_parent) + ["DP3", f"/data/{parset_file.name}"]
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - start_time
        print(f"✓ DP3 subtract completed ({elapsed:.1f}s): {output_ms}")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ DP3 subtract failed after {elapsed:.1f}s: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)
    finally:
        parset_file.unlink(missing_ok=True)

def phaseshift_to_sun(ms_file, output_ms):
    """Phase shift MS to Sun's coordinates using DP3 PhaseShift step."""
    ms_path = Path(ms_file)
    output_path = Path(output_ms)
    if not ms_path.exists():
        raise FileNotFoundError(f"MS file not found: {ms_path}")

    # Get Sun position
    time_mjd = get_time_mjd(str(ms_path))
    sun_ra, sun_dec = get_Sun_RA_DEC(time_mjd)
    
    # Use absolute paths and find common parent
    ms_abs = ms_path.resolve()
    output_abs = output_path.resolve()
    
    # Create parset content
    parset_content = f"""msin = {ms_abs.relative_to(ms_abs.parent)}
msout = {output_abs.relative_to(ms_abs.parent)}
steps = [phaseshift]
phaseshift.type = phaseshift
phaseshift.phasecenter = [{sun_ra}deg, {sun_dec}deg]
"""
    
    parset_file = ms_abs.parent / "phaseshift_to_sun.parset"
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    try:
        # Run DP3 in container
        cmd = base_DP3_cmd(ms_abs.parent) + ["DP3", f"/data/{parset_file.name}"]
        # wait until finish
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.returncode != 0:
            print("DP3 failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            raise RuntimeError(f"DP3 failed with exit code {result.returncode}")
        
        print("DP3 phase shift completed successfully!")
        return str(ms_abs)
        
    finally:
        parset_file.unlink(missing_ok=True)



def run_pipeline(raw_ms, gaintable, output_prefix="proc", plot_mid_steps=False):
    """Run complete processing pipeline"""
    
    pipeline_start = time.time()
    raw_path = Path(raw_ms)
    data_dir = raw_path.parent
    
    # Define intermediate file paths
    flagged_avg_ms = data_dir / f"{raw_path.stem}_flagged_avg.ms"
    caltmp_ms = data_dir / f"{raw_path.stem}_caltmp.ms"
    solution_file = data_dir / "solution.h5"
    final_ms = data_dir / f"{raw_path.stem}_{output_prefix}_final.ms"
    
    print("="*60)
    print("LWA Quick Processing Pipeline")
    print("="*60)
    print(f"Input: {raw_ms}")
    print(f"Gaintable: {gaintable}")
    print(f"Output prefix: {output_prefix}")
    print("="*60)

    # Step 1: casatools applycal
    run_casa_applycal(raw_ms, gaintable)
    
    # Step 2: DP3 flagging and averaging
    run_dp3_flag_avg(raw_ms, flagged_avg_ms)#, strategy_file=PIPELINE_SCRIPT_DIR / "lua" / "LWA_opt_GH1.lua")
    
    # selfcal:
    run_wsclean_imaging(flagged_avg_ms, f"{output_prefix}_image", niter=600, mgain=0.9,horizon_mask=5,
        save_source_list=False, auto_mask=False, auto_threshold=False)
    run_gaincal(flagged_avg_ms, solution_fname=solution_file.name, cal_type="diagonalphase")
    run_applycal_dp3(flagged_avg_ms,final_ms, solution_fname=solution_file.name, cal_entry_lst=["phase"])

    # selfcal2:
    #run_wsclean_imaging(caltmp_ms, f"{output_prefix}_selfcal2_image", niter=800, mgain=0.9,horizon_mask=5,
    #    save_source_list=False, auto_mask=False, auto_threshold=False)
    #run_gaincal(caltmp_ms, solution_fname=solution_file.name, cal_type="diagonalamplitude")
    #reset_solution_outliers( str(solution_file), N_sigma=3)
    #run_applycal_dp3(caltmp_ms,final_ms, solution_fname=solution_file.name, cal_entry_lst=["amplitude"])

    # selfcal3:
    #run_wsclean_imaging(caltmp_ms, f"{output_prefix}_image", niter=800, mgain=0.9,horizon_mask=5,
    #    save_source_list=False, auto_mask=False, auto_threshold=False)
    #run_gaincal(caltmp_ms, solution_fname=solution_file.name, cal_type="diagonal")
    #reset_solution_outliers( str(solution_file), N_sigma=3)
    #run_applycal_dp3(caltmp_ms,final_ms, solution_fname=solution_file.name, cal_entry_lst=["amplitude", "phase"])


    # Step 6: wsclean for source subtraction
    run_wsclean_imaging(final_ms, f"{output_prefix}_image_source", niter=1500, mgain=0.9,horizon_mask=0.1 )#, multiscale=True)
    
    # Step 7: mask far Sun sources
    time_mjd = get_time_mjd(str(final_ms))
    sun_ra, sun_dec = get_Sun_RA_DEC(time_mjd)
    mask_far_Sun_sources( data_dir / f"{output_prefix}_image_source-sources.txt" , 
        data_dir / f"{output_prefix}_image_source_masked-sources.txt", 
        sun_ra, sun_dec, distance_deg=6.0)

    # Step 8: DP3 subtract sources
    subtracted_ms = data_dir / f"{output_prefix}_image_source_masked_subtracted.ms"
    print(f"Subtracting sources from {final_ms} to {subtracted_ms}", str(data_dir / f"{output_prefix}_image_source_masked-sources.txt"))
    run_dp3_subtract(final_ms, subtracted_ms, str(data_dir / f"{output_prefix}_image_source_masked-sources.txt"))

    # step 9: phaseshift to sun
    shifted_ms = data_dir / f"{output_prefix}_image_source_sun_shifted.ms"
    print(f"Phaseshifting to sun from {subtracted_ms} to {shifted_ms}")
    phaseshift_to_sun(subtracted_ms, shifted_ms)

    # final image
    run_wsclean_imaging(shifted_ms, f"{output_prefix}_image_source_sun_shifted", auto_pix_fov=False, 
        niter=3000, mgain=0.8, size=512, scale='1.5arcmin', save_source_list=False, weight='briggs -0.5')
    total_elapsed = time.time() - pipeline_start
    
    print("="*60)
    print(f"Pipeline completed successfully! (Total time: {total_elapsed:.1f}s)")
    print("="*60)
    print(f"Images: {output_prefix}_image*.fits")

    if DEBUG:
        #run_wsclean_imaging(final_ms, f"{output_prefix}_image_final", niter=20000, mgain=0.9,horizon_mask=0.1,
        #    weight='briggs -0.5', auto_pix_fov=False, size=4096, scale='2arcmin', multiscale=True)
        run_wsclean_imaging(subtracted_ms, f"{output_prefix}_image_source_masked_subtracted", niter=5000, mgain=0.9,horizon_mask=0.1)


    if plot_mid_steps:
        from script.plot_fits import plot_fits
        plot_fits(data_dir / f"{output_prefix}_image-image.fits")
        plot_fits(data_dir / f"{output_prefix}_image_source-image.fits")
        plot_fits(data_dir / f"{output_prefix}_image_source_sun_shifted-image.fits")
        if DEBUG:
            plot_fits(data_dir / f"{output_prefix}_image_source_masked_subtracted-image.fits")
        from plot_solar_image import plot_solar_image
        plot_solar_image(data_dir / f"{output_prefix}_image_source_sun_shifted-image.fits")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 pipeline_quick_proc_img.py <raw_ms> <gaintable> [output_prefix]")
        print("Example:")
        print("  python3 pipeline_quick_proc_img.py \\")
        print("    /fast/peijinz/agile_proc/testdata/slow/20240519_173002_55MHz.ms \\")
        print("    /fast/peijinz/agile_proc/testdata/caltables/20240517_100405_55MHz.bcal \\")
        print("    lwa_proc")
        sys.exit(1)
    
    raw_ms = sys.argv[1]
    gaintable = sys.argv[2]
    output_prefix = sys.argv[3] if len(sys.argv) > 3 else "proc"
    
    # Validate inputs
    if not Path(raw_ms).exists():
        print(f"Error: Raw MS not found: {raw_ms}")
        sys.exit(1)
    
    if not Path(gaintable).exists():
        print(f"Error: Gaintable not found: {gaintable}")
        sys.exit(1)
    
    run_pipeline(raw_ms, gaintable, output_prefix, plot_mid_steps=True)

if __name__ == "__main__":
    main()
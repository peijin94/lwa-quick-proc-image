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
import wsclean_imaging

def run_casa_applycal(input_ms, gaintable):
    """Apply CASA bandpass calibration"""
    print(f"Step 1: CASA applycal - {input_ms}")
    start_time = time.time()
    
    casa_script = f"""
import casatools, casatasks

casatasks.applycal(
    vis='{input_ms}',
    gaintable='{gaintable}',
    applymode='calflag'
)
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

def run_dp3_flag_avg(input_ms, output_ms):
    """DP3 flagging and frequency averaging"""
    print(f"Step 2: DP3 flag/avg - {input_ms} -> {output_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    output_path = Path(output_ms)
    
    # Find common parent directory
    common_parent = Path(os.path.commonpath([input_path.parent, output_path.parent]))
    
    # Create DP3 parset
    parset_content = f"""msin = /data/{input_path.relative_to(common_parent)}
msout = /data/{output_path.relative_to(common_parent)}

steps = [flag, avg]

flag.type = aoflagger
flag.strategy = /usr/local/share/linc/rfistrategies/lofar-default.lua
flag.keepstatistics = false

avg.type = averager
avg.freqstep = 3
"""
    
    parset_file = Path("dp3_flag_avg.parset")
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    cmd = [
        "podman", "run", "--rm",
        "-v", f"{common_parent}:/data",
        "-v", f"{Path.cwd()}:/config",
        "-w", "/config",
        "astronrd/linc:latest",
        "DP3", f"/config/{parset_file.name}"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - start_time
        print(f"✓ DP3 flag/avg completed ({elapsed:.1f}s): {output_ms}")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ DP3 flag/avg failed after {elapsed:.1f}s: {e}")
        sys.exit(1)
    finally:
        parset_file.unlink(missing_ok=True)

def run_wsclean_imaging(input_ms, output_prefix="image"):
    """WSClean imaging"""
    print(f"Step 3: WSClean imaging - {input_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    input_dir = input_path.parent
    
    # Generate WSClean command using utils
    wsclean_cmd_str = wsclean_imaging.make_wsclean_cmd(
        msfile=input_path,  imagename=output_prefix,
        auto_pix_fov=True,
        niter=1000, mgain=0.9)
    
    # Split the command string into a list for subprocess
    wsclean_args = wsclean_cmd_str.split()[1:]  # Remove 'wsclean' from the beginning
    
    cmd = [
        "podman", "run", "--rm", "-v", f"{input_dir}:/data", "-w", "/data",
        "astronrd/linc:latest",
        "wsclean"
    ] + wsclean_args + [f"/data/{input_path.name}"]
    
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - start_time
        print(f"✓ WSClean imaging completed ({elapsed:.1f}s): {output_prefix}*.fits")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ WSClean imaging failed after {elapsed:.1f}s: {e}")
        sys.exit(1)

def run_gaincal(input_ms, solution_fname="solution.h5"):
    """DP3 gain calibration"""
    print(f"Step 4: DP3 gaincal - {input_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    input_dir = input_path.parent
    
    parset_content = f"""msin = /data/{input_path.name}
steps = [gaincal]

msout = /data/{input_path.name}_cal.ms

gaincal.solint = 0
gaincal.caltype = diagonal
gaincal.uvlambdamin = 10
gaincal.maxiter = 100
gaincal.tolerance = 1e-4
gaincal.usemodelcolumn = true
gaincal.modelcolumn = MODEL_DATA
gaincal.parmdb = /data/{solution_fname}
"""
    
    parset_file = Path("gaincal.parset")
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    cmd = [
        "podman", "run", "--rm",
        "-v", f"{input_dir}:/data",
        "-v", f"{Path.cwd()}:/config",
        "-w", "/config",
        "astronrd/linc:latest",
        "DP3", f"/config/{parset_file.name}"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - start_time
        print(f"✓ DP3 gaincal completed ({elapsed:.1f}s): solution.h5")
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"✗ DP3 gaincal failed after {elapsed:.1f}s: {e}")
        sys.exit(1)
    finally:
        parset_file.unlink(missing_ok=True)

def run_applycal_dp3(input_ms,  output_ms, solution_fname="solution.h5",):
    """Apply DP3 calibration solutions"""
    print(f"Step 5: DP3 applycal - {input_ms} -> {output_ms}")
    start_time = time.time()
    
    input_path = Path(input_ms)
    output_path = Path(output_ms)
    
    # Find common parent directory
    common_parent = Path(os.path.commonpath([
        input_path.parent, output_path.parent
    ]))
    
    parset_content = f"""msin = /data/{input_path.relative_to(common_parent)}
msout = /data/{output_path.relative_to(common_parent)}
steps = [applycal]
applycal.type = applycal
applycal.parmdb = /data/{solution_fname}
applycal.correction = phase000
"""
    
    parset_file = Path("applycal.parset")
    with open(parset_file, 'w') as f:
        f.write(parset_content)
    
    cmd = [
        "podman", "run", "--rm",
        "-v", f"{common_parent}:/data",
        "-v", f"{Path.cwd()}:/config",
        "-w", "/config",
        "astronrd/linc:latest",
        "DP3", f"/config/{parset_file.name}"
    ]
    
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

def run_pipeline(raw_ms, gaintable, output_prefix="proc"):
    """Run complete processing pipeline"""
    
    pipeline_start = time.time()
    
    raw_path = Path(raw_ms)
    data_dir = raw_path.parent
    
    # Define intermediate file paths
    flagged_avg_ms = data_dir / f"{raw_path.stem}_flagged_avg.ms"
    solution_file = data_dir / "solution.h5"
    final_ms = data_dir / f"{raw_path.stem}_{output_prefix}_final.ms"
    
    print("="*60)
    print("LWA Quick Processing Pipeline")
    print("="*60)
    print(f"Input: {raw_ms}")
    print(f"Gaintable: {gaintable}")
    print(f"Output prefix: {output_prefix}")
    print("="*60)
    
    # Step 1: CASA applycal
    run_casa_applycal(raw_ms, gaintable)
    
    # Step 2: DP3 flagging and averaging
    run_dp3_flag_avg(raw_ms, flagged_avg_ms)
    
    # Step 3: WSClean imaging (fills MODEL_DATA)
    run_wsclean_imaging(flagged_avg_ms, f"{output_prefix}_image")
    
    # Step 4: DP3 gain calibration
    run_gaincal(flagged_avg_ms, solution_fname=solution_file.name)
    
    # Step 5: Apply DP3 calibration solutions
    run_applycal_dp3(flagged_avg_ms,final_ms, solution_fname=solution_file.name )
    
    total_elapsed = time.time() - pipeline_start
    
    print("="*60)
    print(f"Pipeline completed successfully! (Total time: {total_elapsed:.1f}s)")
    print("="*60)
    print(f"Final calibrated MS: {final_ms}")
    print(f"Solution file: {solution_file}")
    print(f"Images: {output_prefix}_image*.fits")

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
    
    run_pipeline(raw_ms, gaintable, output_prefix)

if __name__ == "__main__":
    main()

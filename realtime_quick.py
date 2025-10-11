import os, shutil, time, subprocess
import config
import uuid
import glob

from plot_solar_image import plot_solar_image


def get_newest_file(data_dir="/lustre/pipeline/slow/69MHz"):
    """
    Get the newest file from the nested directory structure.
    
    Args:
        data_dir: Base directory path (default: "/lustre/pipeline/slow/69MHz")
    
    Returns:
        Full path to the newest file
    """
    # List and sort date directories (e.g., "2025-10-10"), get the largest (most recent)
    date_dirs = sorted([d for d in os.listdir(data_dir) 
                       if os.path.isdir(os.path.join(data_dir, d))])
    if not date_dirs:
        raise ValueError(f"No date directories found in {data_dir}")
    
    newest_date = date_dirs[-1]  # Get the largest (most recent date)
    date_path = os.path.join(data_dir, newest_date)
    
    # List and sort hour directories (e.g., "18"), get the largest
    hour_dirs = sorted([d for d in os.listdir(date_path) 
                       if os.path.isdir(os.path.join(date_path, d))])
    if not hour_dirs:
        raise ValueError(f"No hour directories found in {date_path}")
    
    hour_path = os.path.join(date_path, hour_dirs[-1])
    
    # List and sort files in the hour directory, get the largest
    files = sorted(os.listdir(hour_path))
    if not files:
        raise ValueError(f"No files found in {hour_path}")

    newest_file = files[-1]
    return os.path.join(hour_path, newest_file)


def get_caltable_by_freqname(caltable_dir, freq="69MHz"):
    """
    Get the caltable file by frequency name
    
    Args:
        caltable_dir: Directory containing calibration tables
        freq: Frequency name (e.g., "69MHz")
    
    Returns:
        Full path to the calibration table file
    """

    all_files = os.listdir(caltable_dir)
    matching_files = sorted([f for f in all_files if f.endswith(f"_{freq}.bcal")])
    
    if not matching_files:
        raise ValueError(f"No calibration table found for frequency {freq} in {caltable_dir}")
    
    return os.path.join(caltable_dir, matching_files[-1])


if __name__ == "__main__":

    print("realtime_quick.py started")
    while True:
        try:
        # prepare data and caltable
            fname_to_proc = get_newest_file(config.data_root)
            caltable_file = get_caltable_by_freqname(config.caltable_root, config.band_proc)
            print("data:", fname_to_proc, "caltable:", caltable_file)

            # make a very unique dir inside proc_root with uuid and fname_to_proc
            proc_dir = os.path.join(config.proc_root, str(uuid.uuid4().hex[:10]))
            os.makedirs(proc_dir)
            print("proc_dir:", proc_dir)

            # make proc_dir/caltable/ and proc_dir/slow/ dir
            os.makedirs(os.path.join(proc_dir, "caltable"))
            os.makedirs(os.path.join(proc_dir, "slow"))

            # wait for 5 seconds for the file to finish writing
            time.sleep(5)
            shutil.copytree(caltable_file, os.path.join(proc_dir, "caltable", os.path.basename(caltable_file)))
            shutil.copytree(fname_to_proc, os.path.join(proc_dir, "slow", os.path.basename(fname_to_proc)))
            print("copied files to proc_dir:", proc_dir)
        except Exception as e:
            print(e)
            time.sleep(5)
            continue

        try:
        # run the pipeline
            run_cmd = f"""podman run --rm -it \
                -v /fast/peijinz/agile_proc/lwa-quick-proc-image:/lwasoft:ro \
                -v {proc_dir}:/data:rw \
                -w /data \
                peijin/lwa-solar-pipehost:v202510 \
                python3 /lwasoft/pipeline_quick_proc_img.py \
                /data/slow/{os.path.basename(fname_to_proc)} \
                /data/caltable/{os.path.basename(caltable_file)} --mfs-img \
                > {proc_dir}/proc.log"""

            start_time = time.time()
            subprocess.run(run_cmd, shell=True, check=True)
            end_time = time.time()
            print(f"time taken: {end_time - start_time} seconds")

            # find proc_dir/slow/*mfs-image.fits
            mfs_image_file = glob.glob(os.path.join(proc_dir, "slow", "*mfs-image.fits"))[0]
            plt_name = plot_solar_image(mfs_image_file)

            # copy image to dest_dir
            shutil.copy(mfs_image_file, os.path.join(config.dest_dir, os.path.basename(mfs_image_file)))
            shutil.copy(plt_name, os.path.join(config.dest_dir, os.path.basename(plt_name)))

            print("processed:", mfs_image_file, " UT now:", time.strftime("%Y-%m-%d %H:%M:%S"))

            # remove tree proc_dir

        except Exception as e:
            print(e)
            time.sleep(5)
            continue

        # remove proc_dir
        #shutil.rmtree(proc_dir)
        #print("removed proc_dir:", proc_dir)
        
    exit(0)
    
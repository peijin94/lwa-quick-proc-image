#!/usr/bin/env python3
"""
Self-calibration Pipeline using DP3 and wsclean via astronrd/linc container
Processes ./testdata/slow/20240519_173002_55MHz.ms for self-calibration
"""

import os
import sys
import subprocess
import time
import json
import yaml
from pathlib import Path
import argparse
import logging


class SelfCalPipeline:
    """Self-calibration pipeline using DP3 and wsclean via astronrd/linc container"""
    
    def __init__(self, ms_path, output_dir="./selfcal_output", log_level="INFO", config_file="selfcal_config.yml"):
        self.ms_path = Path(ms_path)
        self.output_dir = Path(output_dir)
        self.log_level = log_level
        self.config_file = config_file
        
        # Load configuration from YAML file
        self.config = self.load_config()
        
        # Setup logging
        self.setup_logging()
        
        # Validate input
        if not self.ms_path.exists():
            raise FileNotFoundError(f"Measurement set not found: {self.ms_path}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract configuration parameters
        self.linc_image = self.config['container_images']['linc']
        self.selfcal_iterations = self.config['selfcal_params']['iterations']
        self.smoothness_constraint = self.config['selfcal_params']['smoothness_constraint']
        self.solver_type = self.config['selfcal_params']['solver_type']
    
    def load_config(self):
        """Load configuration from YAML file"""
        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration file: {e}")
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'selfcal_pipeline.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def run_linc_command(self, cmd, volumes=None, workdir=None):
        """Run a command in the astronrd/linc container"""
        podman_cmd = ["podman", "run", "--rm"]
        
        # Add volume mounts
        if volumes:
            for host_path, container_path in volumes.items():
                podman_cmd.extend(["-v", f"{host_path}:{container_path}"])
        
        # Add working directory
        if workdir:
            podman_cmd.extend(["-w", workdir])
        
        # Add container image and command
        podman_cmd.extend([self.linc_image] + cmd)
        
        self.logger.info(f"Running: {' '.join(podman_cmd)}")
        
        try:
            result = subprocess.run(
                podman_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Command completed successfully")
            if result.stdout:
                self.logger.debug(f"STDOUT: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed with exit code {e.returncode}")
            self.logger.error(f"STDERR: {e.stderr}")
            raise
    
    def check_podman(self):
        """Check if podman is available"""
        try:
            result = subprocess.run(["podman", "--version"], 
                                  capture_output=True, text=True, check=True)
            self.logger.info(f"Podman version: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("Podman not found. Please install podman first.")
            return False
    
    def pull_linc_image(self):
        """Pull the astronrd/linc container image"""
        self.logger.info("Pulling astronrd/linc container image...")
        
        try:
            subprocess.run(["podman", "pull", self.linc_image], check=True)
            self.logger.info("LINC image pulled successfully")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to pull LINC image: {e}")
            raise
    
    def test_linc_tools(self):
        """Test if DP3 and wsclean are available in the container"""
        self.logger.info("Testing LINC container tools...")
        
        try:
            # Test DP3
            self.logger.info("Testing DP3...")
            result = self.run_linc_command(["DP3", "--version"])
            self.logger.info("DP3 test successful")
            
            # Test wsclean
            self.logger.info("Testing wsclean...")
            result = self.run_linc_command(["wsclean", "--version"])
            self.logger.info("Wsclean test successful")
            
            self.logger.info("All LINC tools are working correctly")
            return True
            
        except Exception as e:
            self.logger.error(f"LINC tools test failed: {e}")
            return False
    
    def run_wsclean_imaging(self, image_name, input_ms, iteration=None):
        """Run wsclean imaging step"""
        if iteration is None:
            self.logger.info("Creating initial image...")
        else:
            self.logger.info(f"Running wsclean imaging iteration {iteration}...")
        
        # wsclean parameters for imaging from config
        # mgain < 1 enables major iterations and fills MODEL_DATA column
        img_params = self.config['imaging_params']
        wsclean_cmd = [
            "wsclean",
            "-name", image_name,
            "-size", str(img_params['image_size'][0]), str(img_params['image_size'][1]),
            "-scale", img_params['pixel_scale'],
            "-weight", img_params['weighting'], str(img_params['briggs_robust']),
            "-niter", str(img_params['clean_iterations']),
            "-mgain", str(img_params['mgain']),  # Less than 1 to enable major iterations and fill MODEL_DATA
            "-auto-threshold", str(img_params['auto_threshold']).lower(),
            "-auto-mask", str(img_params['auto_mask']).lower(),
            "-mem", str(img_params['mem_percentage']),
            str(input_ms)
        ]
        
        volumes = {
            str(self.ms_path.parent): "/data",
            str(self.output_dir): "/output"
        }
        
        self.run_linc_command(
            wsclean_cmd,
            volumes=volumes,
            workdir="/output"
        )
        
        if iteration is None:
            self.logger.info("Initial image created successfully")
        else:
            self.logger.info(f"Wsclean imaging iteration {iteration} completed")
    
    def run_dp3_calibration(self, iteration, input_ms, output_ms):
        """Run DP3 calibration step"""
        self.logger.info(f"Running DP3 calibration iteration {iteration}...")
        
        # DP3 calibration parset from config
        # Uses MODEL_DATA column that was filled by wsclean
        dp3_params = self.config['dp3_params']
        selfcal_params = self.config['selfcal_params']
        
        cal_parset = f"""
        msin.type = ms
        msin.name = /data/{input_ms.name}
        msin.ntime = {dp3_params['ntime']}
        
        msout.type = ms
        msout.name = /data/{output_ms.name}
        msout.writefullresflag = {str(dp3_params['write_full_res_flag']).lower()}
        
        steps = [cal]
        
        cal.type = gaincal
        cal.solint = {dp3_params['solution_interval']}
        cal.caltype = {dp3_params['calibration_type']}
        cal.applysmooth = {str(dp3_params['apply_smooth']).lower()}
        cal.smoothnessconstraint = {self.smoothness_constraint}
        cal.soltype = {self.solver_type}
        cal.maxiter = {selfcal_params['max_iterations']}
        cal.tolerance = {selfcal_params['tolerance']}
        cal.usemodelcolumn = {str(dp3_params['use_model_column']).lower()}
        cal.modelcolumn = {dp3_params['model_column']}
        """
        
        # Write parset to file
        parset_file = self.output_dir / f"cal_iter_{iteration}.parset"
        with open(parset_file, 'w') as f:
            f.write(cal_parset)
        
        # Run DP3
        dp3_cmd = ["DP3", str(parset_file)]
        
        volumes = {
            str(self.ms_path.parent): "/data",
            str(self.output_dir): "/output"
        }
        
        self.run_linc_command(
            dp3_cmd,
            volumes=volumes,
            workdir="/output"
        )
        
        self.logger.info(f"DP3 calibration iteration {iteration} completed")
    
    def run_selfcal_pipeline(self):
        """Run the complete self-calibration pipeline"""
        self.logger.info("Starting self-calibration pipeline...")
        
        # Check prerequisites
        if not self.check_podman():
            return False
        
        # Pull LINC image
        self.pull_linc_image()
        
        # Test LINC tools
        if not self.test_linc_tools():
            self.logger.error("LINC tools test failed. Cannot proceed.")
            return False
        
        # Create initial image
        self.run_wsclean_imaging("initial_image", self.ms_path)
        
        # Self-calibration iterations
        current_ms = self.ms_path
        
        for iteration in range(1, self.selfcal_iterations + 1):
            self.logger.info(f"Starting self-calibration iteration {iteration}")
            
            # Create output MS name
            output_ms = self.ms_path.parent / f"{self.ms_path.stem}_cal_iter_{iteration}.ms"
            
            # Run calibration
            self.run_dp3_calibration(iteration, current_ms, output_ms)
            
            # Run imaging - this will fill MODEL_DATA column for next iteration
            self.run_wsclean_imaging(f"image_iter_{iteration}", output_ms, iteration)
            
            # Update current MS for next iteration
            current_ms = output_ms
            
            self.logger.info(f"Self-calibration iteration {iteration} completed")
        
        self.logger.info("Self-calibration pipeline completed successfully!")
        return True
    
    def generate_report(self):
        """Generate a summary report of the pipeline run"""
        report_file = self.output_dir / "pipeline_report.json"
        
        report = {
            "input_ms": str(self.ms_path),
            "output_dir": str(self.output_dir),
            "selfcal_iterations": self.selfcal_iterations,
            "smoothness_constraint": self.smoothness_constraint,
            "solver_type": self.solver_type,
            "container_image": self.linc_image,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "completed"
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Pipeline report saved to {report_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Self-calibration pipeline using DP3 and wsclean via astronrd/linc")
    parser.add_argument("ms_path", help="Path to measurement set")
    parser.add_argument("--output-dir", default="./selfcal_output", help="Output directory")
    parser.add_argument("--iterations", type=int, help="Number of self-cal iterations (overrides config file)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--config", default="selfcal_config.yml", help="Path to YAML configuration file")
    
    args = parser.parse_args()
    
    try:
        # Create pipeline instance
        pipeline = SelfCalPipeline(
            ms_path=args.ms_path,
            output_dir=args.output_dir,
            log_level=args.log_level,
            config_file=args.config
        )
        
        # Override iterations if specified on command line
        if args.iterations is not None:
            pipeline.selfcal_iterations = args.iterations
        
        # Run pipeline
        success = pipeline.run_selfcal_pipeline()
        
        if success:
            pipeline.generate_report()
            print("Self-calibration pipeline completed successfully!")
        else:
            print("Self-calibration pipeline failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Pipeline failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

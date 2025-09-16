#!/usr/bin/env python3
"""
Script to plot gain solutions from DP3 solution.h5 files
Visualizes amplitude and phase solutions for each antenna
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

def plot_solutions(solution_file, output_dir=None, antennas=None):
    """
    Plot gain solutions from DP3 solution.h5 file
    
    Args:
        solution_file: Path to solution.h5 file
        output_dir: Directory to save plots (optional)
        antennas: List of antenna indices to plot (optional, plots all if None)
    """
    
    try:
        import h5py
    except ImportError:
        print("Error: h5py is required. Install with: pip install h5py")
        sys.exit(1)
    
    solution_path = Path(solution_file)
    if not solution_path.exists():
        print(f"Error: Solution file not found: {solution_file}")
        sys.exit(1)
    
    # Set output directory
    if output_dir is None:
        output_dir = solution_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading solution file: {solution_file}")
    
    try:
        with h5py.File(solution_file, 'r') as h5f:
            # Print file structure for debugging
            print("Solution file structure:")
            def print_structure(name, obj):
                print(f"  {name}: {type(obj)}")
                if hasattr(obj, 'shape'):
                    print(f"    Shape: {obj.shape}")
                if hasattr(obj, 'dtype'):
                    print(f"    Type: {obj.dtype}")
            
            h5f.visititems(print_structure)
            
            # Try to find gain solutions - common paths in DP3 solution files
            possible_paths = [
                'sol000/phase000/val',
                'sol000/amplitude000/val', 
                'sol000/gain000/val',
                'phase000/val',
                'amplitude000/val',
                'gain000/val',
                'val'
            ]
            
            # Find axes information
            possible_axis_paths = [
                'sol000/phase000/axis',
                'sol000/amplitude000/axis',
                'sol000/gain000/axis',
                'phase000/axis',
                'amplitude000/axis', 
                'gain000/axis',
                'axis'
            ]
            
            gains = None
            axes_info = None
            solution_type = None
            
            # Try to find gain data - check both amplitude and phase
            phase_gains = None
            amplitude_gains = None
            
            if 'sol000/phase000/val' in h5f:
                phase_gains = h5f['sol000/phase000/val'][:]
                print(f"Found phase solutions: {phase_gains.shape}")
            
            if 'sol000/amplitude000/val' in h5f:
                amplitude_gains = h5f['sol000/amplitude000/val'][:]
                print(f"Found amplitude solutions: {amplitude_gains.shape}")
            
            # Prefer complex gains if both are available
            if phase_gains is not None and amplitude_gains is not None:
                gains = amplitude_gains * np.exp(1j * phase_gains)
                solution_type = "complex_gain"
                print(f"Combined complex gains: {gains.shape}")
            elif phase_gains is not None:
                gains = phase_gains
                solution_type = "phase"
                print(f"Using phase solutions: {gains.shape}")
            elif amplitude_gains is not None:
                gains = amplitude_gains
                solution_type = "amplitude"
                print(f"Using amplitude solutions: {gains.shape}")
            else:
                # Fall back to original search
                for path in possible_paths:
                    if path in h5f:
                        gains = h5f[path][:]
                        solution_type = path.split('/')[-2] if '/' in path else 'unknown'
                        print(f"Found solutions at: {path}")
                        print(f"Solution shape: {gains.shape}")
                        print(f"Solution type: {solution_type}")
                        break
            
            # Try to find axes information
            for path in possible_axis_paths:
                if path in h5f:
                    axes_info = h5f[path][:]
                    print(f"Found axes at: {path}")
                    break
            
            if gains is None:
                print("Error: Could not find gain solutions in file")
                print("Available datasets:")
                for key in h5f.keys():
                    print(f"  {key}")
                return
            
            # Get antenna names if available
            antenna_names = None
            possible_ant_paths = [
                'sol000/phase000/ant',
                'sol000/amplitude000/ant',
                'sol000/gain000/ant',
                'phase000/ant',
                'amplitude000/ant',
                'gain000/ant',
                'ant'
            ]
            
            for path in possible_ant_paths:
                if path in h5f:
                    antenna_names = h5f[path][:]
                    if isinstance(antenna_names[0], bytes):
                        antenna_names = [name.decode() for name in antenna_names]
                    print(f"Found antenna names: {antenna_names[:5]}...")
                    break
            
            # Get time information if available
            times = None
            possible_time_paths = [
                'sol000/phase000/time',
                'sol000/amplitude000/time', 
                'sol000/gain000/time',
                'phase000/time',
                'amplitude000/time',
                'gain000/time',
                'time'
            ]
            
            for path in possible_time_paths:
                if path in h5f:
                    times = h5f[path][:]
                    print(f"Found times: {len(times)} timesteps")
                    break
    
    except Exception as e:
        print(f"Error reading solution file: {e}")
        return
    
    # Determine data dimensions
    print(f"Gain array shape: {gains.shape}")
    
    # DP3 H5Parm format is typically [time, freq, antenna, pol]
    if len(gains.shape) == 4:
        n_time, n_freq, n_ant, n_pol = gains.shape
        # Transpose to [time, antenna, freq, pol] for easier plotting
        gains = gains.transpose(0, 2, 1, 3)
        time_axis = True
    elif len(gains.shape) == 3:
        if gains.shape[1] == 1:  # [time, freq, antenna] - single pol
            n_time, n_freq, n_ant = gains.shape
            n_pol = 1
            gains = gains.transpose(0, 2, 1).reshape(n_time, n_ant, n_freq, 1)
            time_axis = True
        else:  # [freq, antenna, pol] - single time
            n_freq, n_ant, n_pol = gains.shape
            n_time = 1
            gains = gains.reshape(1, n_ant, n_freq, n_pol)
            time_axis = False
    elif len(gains.shape) == 2:
        # [antenna, pol] - single time and frequency
        n_ant, n_pol = gains.shape
        n_time = n_freq = 1
        gains = gains.reshape(1, n_ant, 1, n_pol)
        time_axis = False
    else:
        print(f"Unsupported gain array shape: {gains.shape}")
        return
    
    print(f"Interpreted as: time={n_time}, antenna={n_ant}, freq={n_freq}, pol={n_pol}")
    
    # Filter antennas if requested
    if antennas is not None:
        antennas = [ant for ant in antennas if 0 <= ant < n_ant]
        print(f"Plotting antennas: {antennas}")
    else:
        antennas = list(range(min(n_ant, 64)))  # Limit to first 64 antennas for readability
        if n_ant > 64:
            print(f"Note: Only plotting first 64 of {n_ant} antennas")
    
    # Create time axis
    if time_axis and times is not None:
        time_vals = times
        time_label = "Time (MJD)"
    else:
        time_vals = np.arange(n_time)
        time_label = "Time step"
    
    # Determine if solutions are complex (amplitude+phase) or real
    is_complex = np.iscomplexobj(gains)
    
    if is_complex:
        # Plot amplitude and phase separately
        amplitudes = np.abs(gains)
        phases = np.angle(gains)
        
        # Plot amplitudes
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Gain Solutions: {solution_path.name}', fontsize=14)
        
        # XX amplitude
        if n_pol >= 1:
            ax = axes[0, 0]
            for ant_idx in antennas[::max(1, len(antennas)//10)]:  # Plot every ~10th antenna
                ant_name = antenna_names[ant_idx] if antenna_names else f"Ant{ant_idx}"
                ax.plot(time_vals, amplitudes[:, ant_idx, 0, 0], label=ant_name, alpha=0.7)
            ax.set_xlabel(time_label)
            ax.set_ylabel('Amplitude')
            ax.set_title('XX Amplitude')
            ax.grid(True)
            if len(antennas) <= 10:
                ax.legend()
        
        # YY amplitude
        if n_pol >= 2:
            ax = axes[0, 1]
            for ant_idx in antennas[::max(1, len(antennas)//10)]:
                ant_name = antenna_names[ant_idx] if antenna_names else f"Ant{ant_idx}"
                ax.plot(time_vals, amplitudes[:, ant_idx, 0, -1], label=ant_name, alpha=0.7)
            ax.set_xlabel(time_label)
            ax.set_ylabel('Amplitude')
            ax.set_title('YY Amplitude')
            ax.grid(True)
            if len(antennas) <= 10:
                ax.legend()
        
        # XX phase
        if n_pol >= 1:
            ax = axes[1, 0]
            for ant_idx in antennas[::max(1, len(antennas)//10)]:
                ant_name = antenna_names[ant_idx] if antenna_names else f"Ant{ant_idx}"
                ax.plot(time_vals, np.degrees(phases[:, ant_idx, 0, 0]), label=ant_name, alpha=0.7)
            ax.set_xlabel(time_label)
            ax.set_ylabel('Phase (degrees)')
            ax.set_title('XX Phase')
            ax.grid(True)
            if len(antennas) <= 10:
                ax.legend()
        
        # YY phase
        if n_pol >= 2:
            ax = axes[1, 1]
            for ant_idx in antennas[::max(1, len(antennas)//10)]:
                ant_name = antenna_names[ant_idx] if antenna_names else f"Ant{ant_idx}"
                ax.plot(time_vals, np.degrees(phases[:, ant_idx, 0, -1]), label=ant_name, alpha=0.7)
            ax.set_xlabel(time_label)
            ax.set_ylabel('Phase (degrees)')
            ax.set_title('YY Phase')
            ax.grid(True)
            if len(antennas) <= 10:
                ax.legend()
        
        # Remove empty subplots
        if n_pol < 2:
            axes[0, 1].remove()
            axes[1, 1].remove()
    
    else:
        # Real solutions (amplitude or phase only)
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        fig.suptitle(f'Gain Solutions: {solution_path.name}', fontsize=14)
        
        # XX polarization
        if n_pol >= 1:
            ax = axes[0]
            for ant_idx in antennas[::max(1, len(antennas)//10)]:
                ant_name = antenna_names[ant_idx] if antenna_names else f"Ant{ant_idx}"
                ax.plot(time_vals, gains[:, ant_idx, 0, 0], label=ant_name, alpha=0.7)
            ax.set_xlabel(time_label)
            ax.set_ylabel(f'{solution_type.title()} Solutions')
            ax.set_title('XX Polarization')
            ax.grid(True)
            if len(antennas) <= 10:
                ax.legend()
        
        # YY polarization
        if n_pol >= 2:
            ax = axes[1]
            for ant_idx in antennas[::max(1, len(antennas)//10)]:
                ant_name = antenna_names[ant_idx] if antenna_names else f"Ant{ant_idx}"
                ax.plot(time_vals, gains[:, ant_idx, 0, -1], label=ant_name, alpha=0.7)
            ax.set_xlabel(time_label)
            ax.set_ylabel(f'{solution_type.title()} Solutions')
            ax.set_title('YY Polarization')
            ax.grid(True)
            if len(antennas) <= 10:
                ax.legend()
        
        # Remove empty subplot if only one polarization
        if n_pol < 2:
            axes[1].remove()
    
    plt.tight_layout()
    
    # Save plot
    output_file = output_dir / f"{solution_path.stem}_solutions.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Solutions plot saved to: {output_file}")
    
    # Show statistics
    print(f"\nSolution statistics:")
    if is_complex:
        print(f"  Amplitude range: {np.nanmin(amplitudes):.3f} to {np.nanmax(amplitudes):.3f}")
        print(f"  Phase range: {np.degrees(np.nanmin(phases)):.1f}° to {np.degrees(np.nanmax(phases)):.1f}°")
    else:
        print(f"  Value range: {np.nanmin(gains):.3e} to {np.nanmax(gains):.3e}")
    
    flagged_fraction = np.isnan(gains).sum() / gains.size
    print(f"  Flagged solutions: {flagged_fraction*100:.1f}%")
    
    plt.close()
    
    # Create antenna-based summary plot if many antennas
    if n_ant > 10:
        plot_antenna_summary(gains, antenna_names, solution_path, output_dir, is_complex)

def plot_antenna_summary(gains, antenna_names, solution_path, output_dir, is_complex):
    """Create a summary plot showing all antennas"""
    
    n_time, n_ant, n_freq, n_pol = gains.shape
    
    if is_complex:
        amplitudes = np.abs(gains)
        phases = np.angle(gains)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'All Antennas Summary: {solution_path.name}', fontsize=14)
        
        # XX amplitude summary
        ax = axes[0, 0]
        im = ax.imshow(amplitudes[:, :, 0, 0].T, aspect='auto', cmap='viridis', origin='lower')
        ax.set_xlabel('Time step')
        ax.set_ylabel('Antenna')
        ax.set_title('XX Amplitude')
        plt.colorbar(im, ax=ax)
        
        # YY amplitude summary
        if n_pol >= 2:
            ax = axes[0, 1]
            im = ax.imshow(amplitudes[:, :, 0, -1].T, aspect='auto', cmap='viridis', origin='lower')
            ax.set_xlabel('Time step')
            ax.set_ylabel('Antenna')
            ax.set_title('YY Amplitude')
            plt.colorbar(im, ax=ax)
        
        # XX phase summary
        ax = axes[1, 0]
        im = ax.imshow(np.degrees(phases[:, :, 0, 0]).T, aspect='auto', cmap='RdBu_r', origin='lower')
        ax.set_xlabel('Time step')
        ax.set_ylabel('Antenna')
        ax.set_title('XX Phase (degrees)')
        plt.colorbar(im, ax=ax)
        
        # YY phase summary
        if n_pol >= 2:
            ax = axes[1, 1]
            im = ax.imshow(np.degrees(phases[:, :, 0, -1]).T, aspect='auto', cmap='RdBu_r', origin='lower')
            ax.set_xlabel('Time step')
            ax.set_ylabel('Antenna')
            ax.set_title('YY Phase (degrees)')
            plt.colorbar(im, ax=ax)
        
        # Remove empty subplots
        if n_pol < 2:
            axes[0, 1].remove()
            axes[1, 1].remove()
    
    else:
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        fig.suptitle(f'All Antennas Summary: {solution_path.name}', fontsize=14)
        
        # XX summary
        ax = axes[0]
        im = ax.imshow(gains[:, :, 0, 0].T, aspect='auto', cmap='viridis', origin='lower')
        ax.set_xlabel('Time step')
        ax.set_ylabel('Antenna')
        ax.set_title('XX Polarization')
        plt.colorbar(im, ax=ax)
        
        # YY summary
        if n_pol >= 2:
            ax = axes[1]
            im = ax.imshow(gains[:, :, 0, -1].T, aspect='auto', cmap='viridis', origin='lower')
            ax.set_xlabel('Time step')
            ax.set_ylabel('Antenna')
            ax.set_title('YY Polarization')
            plt.colorbar(im, ax=ax)
        else:
            axes[1].remove()
    
    plt.tight_layout()
    
    # Save summary plot
    output_file = output_dir / f"{solution_path.stem}_antenna_summary.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Antenna summary plot saved to: {output_file}")
    
    plt.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Plot DP3 gain solutions from solution.h5 files")
    parser.add_argument("solution_file", help="Path to solution.h5 file")
    parser.add_argument("-o", "--output-dir", help="Output directory for plots")
    parser.add_argument("-a", "--antennas", nargs="+", type=int, 
                       help="Antenna indices to plot (default: first 64)")
    
    args = parser.parse_args()
    
    if not Path(args.solution_file).exists():
        print(f"Error: Solution file not found: {args.solution_file}")
        sys.exit(1)
    
    plot_solutions(args.solution_file, args.output_dir, args.antennas)

if __name__ == "__main__":
    main()

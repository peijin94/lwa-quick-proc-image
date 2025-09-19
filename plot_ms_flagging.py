#!/usr/bin/env python3
"""
Script to plot flagging statistics of a Measurement Set (MS) file.
Shows flagged data as a percentage across time, frequency, and antennas.
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from astropy.table import Table
import os

def load_ms_flagging_data(ms_file):
    """
    Load flagging data from MS file using casacore.
    Returns flagging statistics as dictionaries.
    """
    try:
        import casacore.tables as pt
        
        print(f"Loading flagging data from {ms_file}...")
        
        # Open the main MS table
        ms_table = pt.table(ms_file, readonly=True)
        
        # Get basic MS info
        nrows = ms_table.nrows()
        print(f"Total number of rows: {nrows:,}")
        
        # Get antenna information
        ant1 = ms_table.getcol('ANTENNA1')
        ant2 = ms_table.getcol('ANTENNA2')
        
        # Get time information
        times = ms_table.getcol('TIME')
        unique_times = np.unique(times)
        ntimes = len(unique_times)
        
        # Get data description IDs
        dd_ids = ms_table.getcol('DATA_DESC_ID')
        unique_dd = np.unique(dd_ids)
        
        # Get spectral window info for frequency
        spw_table = pt.table(ms_file + '/SPECTRAL_WINDOW', readonly=True)
        frequencies = spw_table.getcol('CHAN_FREQ')
        spw_table.close()
        
        # Get flag data
        flags = ms_table.getcol('FLAG')  # Shape: (nrows, nchan, npol)
        
        # Get data shape - casacore returns (nrows, nchan, npol)
        nvis, nchan, npol = flags.shape
        print(f"Data shape: {nvis:,} visibilities, {nchan} channels, {npol} polarizations")
        
        # Calculate flagging statistics
        flag_stats = {}
        
        # Overall flagging percentage
        total_flags = np.sum(flags)
        total_vis = flags.size
        flag_percent = (total_flags / total_vis) * 100
        flag_stats['overall'] = flag_percent
        
        print(f"Overall flagging: {flag_percent:.2f}%")
        
        # Flagging per antenna
        ant_flag_stats = {}
        ant_table = pt.table(ms_file + '/ANTENNA', readonly=True)
        ant_names = ant_table.getcol('NAME')
        ant_table.close()
        
        for i, ant_name in enumerate(ant_names):
            # Find visibilities involving this antenna
            ant1_mask = (ant1 == i)
            ant2_mask = (ant2 == i)
            ant_vis_mask = ant1_mask | ant2_mask
            
            if np.any(ant_vis_mask):
                ant_flags = flags[ant_vis_mask, :, :]  # Shape: (nvis_ant, nchan, npol)
                ant_flag_percent = (np.sum(ant_flags) / ant_flags.size) * 100
                ant_flag_stats[ant_name] = ant_flag_percent
        
        flag_stats['antenna'] = ant_flag_stats
        
        # Flagging per time
        time_flag_stats = {}
        for i, time in enumerate(unique_times):
            time_mask = (times == time)
            if np.any(time_mask):
                time_flags = flags[time_mask, :, :]  # Shape: (nvis_time, nchan, npol)
                time_flag_percent = (np.sum(time_flags) / time_flags.size) * 100
                time_flag_stats[time] = time_flag_percent
        
        flag_stats['time'] = time_flag_stats
        
        # Flagging per frequency channel
        chan_flag_stats = {}
        for i in range(nchan):
            chan_flags = flags[:, i, :]  # Shape: (nvis, npol)
            chan_flag_percent = (np.sum(chan_flags) / chan_flags.size) * 100
            chan_flag_stats[i] = chan_flag_percent
        
        flag_stats['frequency'] = chan_flag_stats
        flag_stats['frequencies'] = frequencies[0] if len(frequencies.shape) > 1 else frequencies
        
        # Close main table
        ms_table.close()
        
        return flag_stats
        
    except ImportError:
        print("Error: casacore not available. Please install casacore-py or ensure it's accessible.")
        print("Try: pip install casacore or conda install -c conda-forge casacore")
        return None
    except Exception as e:
        print(f"Error loading MS data: {e}")
        return None

def plot_flagging_statistics(flag_stats, output_file):
    """
    Plot flagging statistics in multiple subplots.
    """
    if flag_stats is None:
        print("No flagging data to plot.")
        return
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('MS Flagging Statistics', fontsize=16, fontweight='bold')
    
    # 1. Overall flagging summary
    ax1.bar(['Overall'], [flag_stats['overall']], color='red', alpha=0.7)
    ax1.set_ylabel('Flagged Percentage (%)')
    ax1.set_title(f'Overall Flagging: {flag_stats["overall"]:.2f}%')
    ax1.set_ylim(0, 100)
    
    # Add percentage text on bar
    ax1.text(0, flag_stats['overall'] + 1, f'{flag_stats["overall"]:.1f}%', 
             ha='center', va='bottom', fontweight='bold')
    
    # 2. Flagging per antenna
    if 'antenna' in flag_stats and flag_stats['antenna']:
        ant_names = list(flag_stats['antenna'].keys())
        ant_percentages = list(flag_stats['antenna'].values())
        
        # Sort by percentage for better visualization
        sorted_indices = np.argsort(ant_percentages)[::-1]
        sorted_names = [ant_names[i] for i in sorted_indices]
        sorted_percentages = [ant_percentages[i] for i in sorted_indices]
        
        bars = ax2.bar(range(len(sorted_names)), sorted_percentages, 
                      color='orange', alpha=0.7)
        ax2.set_xlabel('Antenna')
        ax2.set_ylabel('Flagged Percentage (%)')
        ax2.set_title('Flagging per Antenna')
        ax2.set_xticks(range(len(sorted_names)))
        ax2.set_xticklabels(sorted_names, rotation=45, ha='right')
        ax2.set_ylim(0, 100)
        
        # Add percentage text on top of bars
        for i, (bar, pct) in enumerate(zip(bars, sorted_percentages)):
            if pct > 5:  # Only show text if percentage is significant
                ax2.text(bar.get_x() + bar.get_width()/2, pct + 1, 
                        f'{pct:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # 3. Flagging per time
    if 'time' in flag_stats and flag_stats['time']:
        times = list(flag_stats['time'].keys())
        time_percentages = list(flag_stats['time'].values())
        
        # Convert MJD to hours from start
        times_array = np.array(times)
        times_hours = (times_array - times_array[0]) * 24.0
        
        ax3.plot(times_hours, time_percentages, 'b-', linewidth=1, alpha=0.7)
        ax3.fill_between(times_hours, time_percentages, alpha=0.3, color='blue')
        ax3.set_xlabel('Time (hours from start)')
        ax3.set_ylabel('Flagged Percentage (%)')
        ax3.set_title('Flagging vs Time')
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3)
    
    # 4. Flagging per frequency channel
    if 'frequency' in flag_stats and flag_stats['frequency']:
        channels = list(flag_stats['frequency'].keys())
        chan_percentages = list(flag_stats['frequency'].values())
        
        ax4.plot(channels, chan_percentages, 'g-', linewidth=1, alpha=0.7)
        ax4.fill_between(channels, chan_percentages, alpha=0.3, color='green')
        ax4.set_xlabel('Channel Number')
        ax4.set_ylabel('Flagged Percentage (%)')
        ax4.set_title('Flagging vs Frequency Channel')
        ax4.set_ylim(0, 100)
        ax4.grid(True, alpha=0.3)
        
        # Add frequency information to title if available
        if 'frequencies' in flag_stats and len(flag_stats['frequencies']) > 0:
            freqs = flag_stats['frequencies']
            if len(freqs) > 0:
                freq_min = np.min(freqs) / 1e6
                freq_max = np.max(freqs) / 1e6
                ax4.set_title(f'Flagging vs Frequency Channel\n({freq_min:.1f} - {freq_max:.1f} MHz)')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Flagging statistics plot saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Plot flagging statistics of an MS file')
    parser.add_argument('ms_file', help='Input Measurement Set file')
    parser.add_argument('-o', '--output', help='Output plot file (default: auto-generated)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Check if MS file exists
    ms_path = Path(args.ms_file)
    if not ms_path.exists():
        print(f"Error: MS file {ms_file} not found.")
        sys.exit(1)
    
    # Generate output filename if not provided
    if args.output:
        output_file = args.output
    else:
        output_file = ms_path.parent / f"{ms_path.stem}_flagging_stats.png"
    
    print(f"Processing MS file: {ms_path}")
    print(f"Output plot: {output_file}")
    print("="*60)
    
    # Load flagging data
    flag_stats = load_ms_flagging_data(str(ms_path))
    
    if flag_stats:
        # Plot flagging statistics
        plot_flagging_statistics(flag_stats, str(output_file))
        
        # Print summary
        print("\nFlagging Summary:")
        print(f"  Overall flagging: {flag_stats['overall']:.2f}%")
        
        if 'antenna' in flag_stats:
            ant_stats = flag_stats['antenna']
            worst_ant = max(ant_stats.items(), key=lambda x: x[1])
            best_ant = min(ant_stats.items(), key=lambda x: x[1])
            print(f"  Worst antenna: {worst_ant[0]} ({worst_ant[1]:.2f}%)")
            print(f"  Best antenna: {best_ant[0]} ({best_ant[1]:.2f}%)")
        
        if 'time' in flag_stats:
            time_stats = flag_stats['time']
            worst_time = max(time_stats.items(), key=lambda x: x[1])
            print(f"  Worst time: {worst_time[1]:.2f}% flagged")
        
        if 'frequency' in flag_stats:
            freq_stats = flag_stats['frequency']
            worst_chan = max(freq_stats.items(), key=lambda x: x[1])
            print(f"  Worst channel: {worst_chan[0]} ({worst_chan[1]:.2f}% flagged)")
        
        print(f"\nPlot saved to: {output_file}")
    else:
        print("Failed to load flagging data.")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate Verification Plots for Translated SPICE Models

This script runs ngspice simulations on translated model files and generates
publication-quality plots showing I-V characteristics and other device behavior.

Usage:
    python generate_verification_plots.py output/asap7_hspice-ngspice/tt.lib
    python generate_verification_plots.py output/  # Process all translated files
    
Output:
    Creates PNG figures in the same directory as the translated files.
"""

import sys
import re
import subprocess
import tempfile
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
import os

# Set matplotlib to use non-interactive backend before importing pyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class DeviceInfo:
    """Information about a device extracted from the library file"""
    name: str
    device_type: str  # 'nmos', 'pmos', 'npn', 'pnp', 'diode', 'resistor', 'capacitor'
    is_model: bool    # True if .model, False if .subckt
    level: Optional[int] = None


def extract_devices(lib_file: Path) -> List[DeviceInfo]:
    """Extract device information from a library file."""
    devices = []
    content = lib_file.read_text()
    
    # Find .model statements
    model_pattern = r'\.model\s+(\S+)\s+(\S+)'
    for match in re.finditer(model_pattern, content, re.IGNORECASE):
        name = match.group(1)
        model_type = match.group(2).lower()
        
        device_type = None
        if model_type in ['nmos', 'nmos4']:
            device_type = 'nmos'
        elif model_type in ['pmos', 'pmos4']:
            device_type = 'pmos'
        elif model_type == 'npn':
            device_type = 'npn'
        elif model_type == 'pnp':
            device_type = 'pnp'
        elif model_type == 'd':
            device_type = 'diode'
        elif model_type == 'r':
            device_type = 'resistor'
        elif model_type == 'c':
            device_type = 'capacitor'
        
        if device_type:
            # Try to extract level
            level_match = re.search(rf'\.model\s+{re.escape(name)}.*?level\s*=\s*(\d+)', 
                                   content, re.IGNORECASE | re.DOTALL)
            level = int(level_match.group(1)) if level_match else None
            devices.append(DeviceInfo(name, device_type, True, level))
    
    # Find .subckt statements
    subckt_pattern = r'\.subckt\s+(\S+)'
    for match in re.finditer(subckt_pattern, content, re.IGNORECASE):
        name = match.group(1)
        name_lower = name.lower()
        
        device_type = None
        if any(x in name_lower for x in ['nmos', 'nfet', 'nch']):
            device_type = 'nmos'
        elif any(x in name_lower for x in ['pmos', 'pfet', 'pch']):
            device_type = 'pmos'
        elif 'npn' in name_lower:
            device_type = 'npn'
        elif 'pnp' in name_lower:
            device_type = 'pnp'
        elif any(x in name_lower for x in ['diode', 'dio']):
            device_type = 'diode'
        elif any(x in name_lower for x in ['cap', 'mim']):
            device_type = 'capacitor'
        elif 'res' in name_lower:
            device_type = 'resistor'
        
        if device_type:
            devices.append(DeviceInfo(name, device_type, False))
    
    return devices


def run_ngspice_simulation(netlist: str, timeout: int = 60) -> Tuple[bool, str, str]:
    """Run ngspice simulation and return success, stdout, stderr."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
        f.write(netlist)
        netlist_file = f.name
    
    try:
        result = subprocess.run(
            ['ngspice', '-b', netlist_file],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return True, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, '', 'Simulation timed out'
    except Exception as e:
        return False, '', str(e)
    finally:
        Path(netlist_file).unlink(missing_ok=True)


def parse_wrdata_output(data_file: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Parse ngspice wrdata output file."""
    x_data = []
    y_data = []
    
    if not data_file.exists():
        return np.array([]), np.array([])
    
    with open(data_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('*'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x_data.append(float(parts[0]))
                    y_data.append(float(parts[1]))
                except ValueError:
                    continue
    
    return np.array(x_data), np.array(y_data)


def generate_mos_idvgs_plot(
    lib_file: Path,
    device: DeviceInfo,
    output_dir: Path
) -> Optional[Path]:
    """Generate MOS Id vs Vgs transfer characteristic plot."""
    
    data_file = output_dir / f"{device.name}_idvgs.dat"
    plot_file = output_dir / f"{device.name}_idvgs.png"
    
    # Determine voltage ranges based on level
    if device.level and device.level >= 70:
        # FinFET (BSIM-CMG) - lower voltages
        vgs_stop = 0.7
        vds = 0.7
    else:
        # Bulk CMOS - standard voltages
        vgs_stop = 1.8
        vds = 1.0
    
    is_pmos = device.device_type == 'pmos'
    
    if is_pmos:
        vgs_start, vgs_stop_actual = -vgs_stop, 0.0
        vds_actual = -vds
    else:
        vgs_start, vgs_stop_actual = 0.0, vgs_stop
        vds_actual = vds
    
    # Create netlist for MOS model
    if device.is_model:
        # Direct model instantiation
        netlist = f"""* MOS Id vs Vgs - {device.name}
.include '{lib_file}'

Vdd drain 0 DC {vds_actual}
Vgs gate 0 DC 0

M1 drain gate 0 0 {device.name}

.dc Vgs {vgs_start} {vgs_stop_actual} 0.01

.control
run
let id = -i(Vdd)
let vgs_data = v(gate)
set wr_singlescale
set wr_vecnames
wrdata {data_file} vgs_data id
quit
.endc

.end
"""
    else:
        # Subcircuit instantiation
        netlist = f"""* MOS Id vs Vgs - {device.name}
.include '{lib_file}'

Vdd drain 0 DC {vds_actual}
Vgs gate 0 DC 0

X1 drain gate 0 0 {device.name}

.dc Vgs {vgs_start} {vgs_stop_actual} 0.01

.control
run
let id = -i(Vdd)
let vgs_data = v(gate)
set wr_singlescale
set wr_vecnames
wrdata {data_file} vgs_data id
quit
.endc

.end
"""
    
    success, stdout, stderr = run_ngspice_simulation(netlist)
    
    if not success or not data_file.exists():
        print(f"    ⚠️  Simulation failed for {device.name}: {stderr[:100]}")
        return None
    
    # Parse data
    vgs, id_data = parse_wrdata_output(data_file)
    
    if len(vgs) < 5:
        print(f"    ⚠️  Insufficient data points for {device.name}")
        data_file.unlink(missing_ok=True)
        return None
    
    # Convert to mA
    id_ma = np.abs(id_data) * 1000
    vgs_plot = np.abs(vgs) if is_pmos else vgs
    
    # Create plot
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    
    ax.plot(vgs_plot, id_ma, 'b-', linewidth=2, label=f'{device.name}')
    
    ax.set_xlabel('$|V_{GS}|$ (V)', fontsize=12)
    ax.set_ylabel('$|I_D|$ (mA)', fontsize=12)
    ax.set_title(f'Transfer Characteristics: {device.name}\n({"PMOS" if is_pmos else "NMOS"}, $V_{{DS}}$ = {abs(vds_actual)}V)', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    ax.set_xlim(0, abs(vgs_stop_actual))
    ax.set_ylim(bottom=0)
    
    # Add ngspice verification stamp
    ax.text(0.98, 0.02, 'Verified with ngspice', transform=ax.transAxes,
            fontsize=8, color='green', ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(plot_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    # Clean up data file
    data_file.unlink(missing_ok=True)
    
    return plot_file


def generate_mos_idvds_plot(
    lib_file: Path,
    device: DeviceInfo,
    output_dir: Path
) -> Optional[Path]:
    """Generate MOS Id vs Vds output characteristic plot with multiple Vgs curves."""
    
    plot_file = output_dir / f"{device.name}_idvds.png"
    
    # Determine voltage ranges
    if device.level and device.level >= 70:
        vds_stop = 0.7
        vgs_values = [0.3, 0.4, 0.5, 0.6, 0.7]
    else:
        vds_stop = 1.8
        vgs_values = [0.6, 0.9, 1.2, 1.5, 1.8]
    
    is_pmos = device.device_type == 'pmos'
    
    all_curves = []
    
    for vgs in vgs_values:
        data_file = output_dir / f"{device.name}_idvds_vgs{vgs:.1f}.dat"
        
        if is_pmos:
            vds_range = f"-{vds_stop} 0 0.02"
            vgs_actual = -vgs
        else:
            vds_range = f"0 {vds_stop} 0.02"
            vgs_actual = vgs
        
        if device.is_model:
            netlist = f"""* MOS Id vs Vds - {device.name} at Vgs={vgs}V
.include '{lib_file}'

Vdd drain 0 DC 0
Vgs gate 0 DC {vgs_actual}

M1 drain gate 0 0 {device.name}

.dc Vdd {vds_range}

.control
run
let id = -i(Vdd)
let vds_data = v(drain)
set wr_singlescale
set wr_vecnames
wrdata {data_file} vds_data id
quit
.endc

.end
"""
        else:
            netlist = f"""* MOS Id vs Vds - {device.name} at Vgs={vgs}V
.include '{lib_file}'

Vdd drain 0 DC 0
Vgs gate 0 DC {vgs_actual}

X1 drain gate 0 0 {device.name}

.dc Vdd {vds_range}

.control
run
let id = -i(Vdd)
let vds_data = v(drain)
set wr_singlescale
set wr_vecnames
wrdata {data_file} vds_data id
quit
.endc

.end
"""
        
        success, stdout, stderr = run_ngspice_simulation(netlist)
        
        if success and data_file.exists():
            vds, id_data = parse_wrdata_output(data_file)
            if len(vds) >= 5:
                all_curves.append((vgs, np.abs(vds), np.abs(id_data) * 1000))
            data_file.unlink(missing_ok=True)
    
    if not all_curves:
        print(f"    ⚠️  No curves generated for {device.name}")
        return None
    
    # Create plot
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(all_curves)))
    
    for (vgs, vds, id_ma), color in zip(all_curves, colors):
        ax.plot(vds, id_ma, '-', linewidth=2, color=color, 
                label=f'$V_{{GS}}$ = {vgs:.1f}V')
    
    ax.set_xlabel('$|V_{DS}|$ (V)', fontsize=12)
    ax.set_ylabel('$|I_D|$ (mA)', fontsize=12)
    ax.set_title(f'Output Characteristics: {device.name}\n({"PMOS" if is_pmos else "NMOS"})', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=10)
    ax.set_xlim(0, vds_stop)
    ax.set_ylim(bottom=0)
    
    ax.text(0.98, 0.02, 'Verified with ngspice', transform=ax.transAxes,
            fontsize=8, color='green', ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(plot_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return plot_file


def generate_bjt_gummel_plot(
    lib_file: Path,
    device: DeviceInfo,
    output_dir: Path
) -> Optional[Path]:
    """Generate BJT Gummel plot (Ic and Ib vs Vbe)."""
    
    data_file_ic = output_dir / f"{device.name}_gummel_ic.dat"
    data_file_ib = output_dir / f"{device.name}_gummel_ib.dat"
    plot_file = output_dir / f"{device.name}_gummel.png"
    
    is_pnp = device.device_type == 'pnp'
    vcc = -3.3 if is_pnp else 3.3
    vbe_range = "-0.8 -0.4 0.01" if is_pnp else "0.4 0.8 0.01"
    
    if device.is_model:
        netlist = f"""* BJT Gummel Plot - {device.name}
.include '{lib_file}'

Vcc collector 0 DC {vcc}
Vbe base 0 DC 0.6
Vee emitter 0 DC 0

Q1 collector base emitter {device.name}

.dc Vbe {vbe_range}

.control
run
let ic = -i(Vcc)
let ib = -i(Vbe)
let vbe_data = v(base)
set wr_singlescale
set wr_vecnames
wrdata {data_file_ic} vbe_data ic
wrdata {data_file_ib} vbe_data ib
quit
.endc

.end
"""
    else:
        netlist = f"""* BJT Gummel Plot - {device.name}
.include '{lib_file}'

Vcc collector 0 DC {vcc}
Vbe base 0 DC 0.6

X1 collector base 0 {device.name}

.dc Vbe {vbe_range}

.control
run
let ic = -i(Vcc)
let ib = -i(Vbe)
let vbe_data = v(base)
set wr_singlescale
set wr_vecnames
wrdata {data_file_ic} vbe_data ic
wrdata {data_file_ib} vbe_data ib
quit
.endc

.end
"""
    
    success, stdout, stderr = run_ngspice_simulation(netlist)
    
    if not success:
        print(f"    ⚠️  Simulation failed for {device.name}")
        return None
    
    vbe_ic, ic = parse_wrdata_output(data_file_ic)
    vbe_ib, ib = parse_wrdata_output(data_file_ib)
    
    if len(vbe_ic) < 5:
        print(f"    ⚠️  Insufficient data for {device.name}")
        data_file_ic.unlink(missing_ok=True)
        data_file_ib.unlink(missing_ok=True)
        return None
    
    # Create semilog plot
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    
    vbe_plot = np.abs(vbe_ic)
    ic_plot = np.abs(ic)
    ib_plot = np.abs(ib) if len(ib) > 0 else None
    
    ax.semilogy(vbe_plot, ic_plot, 'b-', linewidth=2, label='$I_C$')
    if ib_plot is not None and len(ib_plot) == len(vbe_plot):
        ax.semilogy(vbe_plot, ib_plot, 'r--', linewidth=2, label='$I_B$')
    
    ax.set_xlabel('$|V_{BE}|$ (V)', fontsize=12)
    ax.set_ylabel('Current (A)', fontsize=12)
    ax.set_title(f'Gummel Plot: {device.name}\n({"PNP" if is_pnp else "NPN"} BJT)', fontsize=14)
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='lower right', fontsize=11)
    
    ax.text(0.98, 0.02, 'Verified with ngspice', transform=ax.transAxes,
            fontsize=8, color='green', ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(plot_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    # Cleanup
    data_file_ic.unlink(missing_ok=True)
    data_file_ib.unlink(missing_ok=True)
    
    return plot_file


def generate_diode_iv_plot(
    lib_file: Path,
    device: DeviceInfo,
    output_dir: Path
) -> Optional[Path]:
    """Generate diode I-V characteristic plot."""
    
    data_file = output_dir / f"{device.name}_iv.dat"
    plot_file = output_dir / f"{device.name}_iv.png"
    
    if device.is_model:
        netlist = f"""* Diode I-V - {device.name}
.include '{lib_file}'

Vd anode 0 DC 0

D1 anode 0 {device.name}

.dc Vd -1 1 0.01

.control
run
let id = -i(Vd)
let vd_data = v(anode)
set wr_singlescale
set wr_vecnames
wrdata {data_file} vd_data id
quit
.endc

.end
"""
    else:
        netlist = f"""* Diode I-V - {device.name}
.include '{lib_file}'

Vd anode 0 DC 0

X1 anode 0 {device.name}

.dc Vd -1 1 0.01

.control
run
let id = -i(Vd)
let vd_data = v(anode)
set wr_singlescale
set wr_vecnames
wrdata {data_file} vd_data id
quit
.endc

.end
"""
    
    success, stdout, stderr = run_ngspice_simulation(netlist)
    
    if not success or not data_file.exists():
        print(f"    ⚠️  Simulation failed for {device.name}")
        return None
    
    vd, id_data = parse_wrdata_output(data_file)
    
    if len(vd) < 5:
        data_file.unlink(missing_ok=True)
        return None
    
    # Create plot
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    
    ax.plot(vd, id_data * 1000, 'b-', linewidth=2)
    
    ax.set_xlabel('$V_D$ (V)', fontsize=12)
    ax.set_ylabel('$I_D$ (mA)', fontsize=12)
    ax.set_title(f'Diode I-V Characteristic: {device.name}', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='k', linewidth=0.5)
    ax.axvline(x=0, color='k', linewidth=0.5)
    
    ax.text(0.98, 0.02, 'Verified with ngspice', transform=ax.transAxes,
            fontsize=8, color='green', ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(plot_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    data_file.unlink(missing_ok=True)
    
    return plot_file


def process_library_file(lib_file: Path, max_devices: int = 3) -> Dict[str, List[Path]]:
    """Process a library file and generate plots for its devices."""
    
    print(f"\n📂 Processing: {lib_file.name}")
    
    output_dir = lib_file.parent / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    devices = extract_devices(lib_file)
    
    if not devices:
        print("    No devices found")
        return {}
    
    print(f"    Found {len(devices)} devices")
    
    results = {
        'transfer': [],
        'output': [],
        'gummel': [],
        'diode': []
    }
    
    # Group by type and limit
    mos_devices = [d for d in devices if d.device_type in ['nmos', 'pmos']][:max_devices]
    bjt_devices = [d for d in devices if d.device_type in ['npn', 'pnp']][:max_devices]
    diode_devices = [d for d in devices if d.device_type == 'diode'][:max_devices]
    
    # Generate MOS plots
    for device in mos_devices:
        print(f"    🔬 Generating plots for {device.name} ({device.device_type})...")
        
        # Transfer characteristics
        plot = generate_mos_idvgs_plot(lib_file, device, output_dir)
        if plot:
            results['transfer'].append(plot)
            print(f"       ✅ Transfer: {plot.name}")
        
        # Output characteristics
        plot = generate_mos_idvds_plot(lib_file, device, output_dir)
        if plot:
            results['output'].append(plot)
            print(f"       ✅ Output: {plot.name}")
    
    # Generate BJT plots
    for device in bjt_devices:
        print(f"    🔬 Generating Gummel plot for {device.name} ({device.device_type})...")
        plot = generate_bjt_gummel_plot(lib_file, device, output_dir)
        if plot:
            results['gummel'].append(plot)
            print(f"       ✅ Gummel: {plot.name}")
    
    # Generate Diode plots
    for device in diode_devices:
        print(f"    🔬 Generating I-V plot for {device.name} ({device.device_type})...")
        plot = generate_diode_iv_plot(lib_file, device, output_dir)
        if plot:
            results['diode'].append(plot)
            print(f"       ✅ I-V: {plot.name}")
    
    return results


def generate_summary_figure(all_results: Dict[str, Dict], output_dir: Path) -> Path:
    """Generate a summary figure showing all verification results."""
    
    summary_file = output_dir / "verification_summary.png"
    
    # Collect all successful plots
    all_plots = []
    for lib_name, results in all_results.items():
        for plot_type, plots in results.items():
            for plot in plots:
                all_plots.append((lib_name, plot_type, plot))
    
    if not all_plots:
        print("No plots to summarize")
        return None
    
    # Create summary grid
    n_plots = min(len(all_plots), 6)  # Max 6 in summary
    cols = min(3, n_plots)
    rows = (n_plots + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows), dpi=100)
    if n_plots == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = axes.reshape(1, -1)
    
    for idx, (lib_name, plot_type, plot_path) in enumerate(all_plots[:n_plots]):
        row, col = divmod(idx, cols)
        ax = axes[row, col]
        
        try:
            img = plt.imread(str(plot_path))
            ax.imshow(img)
            ax.set_title(f"{lib_name}\n({plot_type})", fontsize=9)
        except Exception as e:
            ax.text(0.5, 0.5, f"Error loading\n{plot_path.name}", 
                   ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
    
    # Hide unused axes
    for idx in range(n_plots, rows * cols):
        row, col = divmod(idx, cols)
        axes[row, col].axis('off')
    
    plt.suptitle('ngspice Verification Summary', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(summary_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return summary_file


def main():
    parser = argparse.ArgumentParser(
        description='Generate ngspice verification plots for translated SPICE models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process a single library file
    %(prog)s output/asap7_hspice-ngspice/tt.lib
    
    # Process all files in output directory
    %(prog)s output/
    
    # Limit devices per file
    %(prog)s output/ --max-devices 2
"""
    )
    
    parser.add_argument('path', type=Path, 
                       help='Library file or directory to process')
    parser.add_argument('--max-devices', '-m', type=int, default=3,
                       help='Maximum devices to plot per file (default: 3)')
    parser.add_argument('--output', '-o', type=Path, default=None,
                       help='Output directory for summary (default: same as input)')
    
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    
    if not path.exists():
        print(f"❌ Path does not exist: {path}")
        sys.exit(1)
    
    all_results = {}
    
    if path.is_file():
        # Single file
        results = process_library_file(path, args.max_devices)
        if results:
            all_results[path.stem] = results
    else:
        # Directory - find all .lib files
        lib_files = list(path.rglob("*.lib"))
        if not lib_files:
            print(f"⚠️  No .lib files found in {path}")
            sys.exit(1)
        
        print(f"🔍 Found {len(lib_files)} library files")
        
        for lib_file in sorted(lib_files):
            # Skip files in plots subdirectory
            if 'plots' in lib_file.parts:
                continue
            results = process_library_file(lib_file, args.max_devices)
            if results:
                all_results[lib_file.stem] = results
    
    # Generate summary
    if all_results:
        output_dir = args.output or (path if path.is_dir() else path.parent)
        summary = generate_summary_figure(all_results, output_dir)
        if summary:
            print(f"\n📊 Summary saved to: {summary}")
    
    # Count total plots
    total_plots = sum(
        len(plots) 
        for results in all_results.values() 
        for plots in results.values()
    )
    
    print(f"\n✅ Generated {total_plots} verification plots")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Simulation Plotter for Verification

Generates I-V curves, AC response plots, and other simulation graphs.
Saves plots to the output directory alongside translated files.

Usage:
    from verification.plotter import SimulationPlotter
    
    plotter = SimulationPlotter()
    plotter.plot_bjt_gummel(lib_file, device_name, output_dir)
"""

import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))


@dataclass
class PlotResult:
    """Result of plot generation"""
    success: bool
    plot_file: Optional[Path]
    data_file: Optional[Path]
    error: Optional[str]
    data_points: int = 0


class SimulationPlotter:
    """
    Generates simulation plots for verification.
    
    Supports:
    - BJT Gummel plots (Ic vs Vbe)
    - MOS I-V curves (Id vs Vgs, Id vs Vds)
    - Diode I-V curves
    - Capacitor AC impedance
    - Resistor I-V curves
    """
    
    def __init__(self, ngspice_path: str = 'ngspice'):
        self.ngspice = ngspice_path
    
    def plot_bjt_gummel(
        self,
        lib_file: Path,
        device_name: str,
        output_dir: Path,
        vbe_start: float = 0.4,
        vbe_stop: float = 0.8,
        vcc: float = 3.3
    ) -> PlotResult:
        """
        Generate BJT Gummel plot (Ic vs Vbe).
        
        Args:
            lib_file: Path to ngspice library file
            device_name: Subcircuit or model name
            output_dir: Directory to save plot and data
            vbe_start: Start voltage for Vbe sweep
            vbe_stop: Stop voltage for Vbe sweep
            vcc: Collector supply voltage
        
        Returns:
            PlotResult with paths to generated files
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        lib_file = Path(lib_file).resolve()
        
        data_file = output_dir / f"{device_name}_gummel.csv"
        plot_file = output_dir / f"{device_name}_gummel.png"
        
        netlist = f"""* BJT Gummel Plot - {device_name}
.include "{lib_file}"

Vcc vcc 0 DC {vcc}
Vbe base 0 DC 0.6
X1 vcc base 0 {device_name}

.dc Vbe {vbe_start} {vbe_stop} 0.01

.control
run

* Extract data
let ic = -i(Vcc)
let vbe_data = v(base)

* Save to file 
set wr_singlescale
set wr_vecnames  
wrdata {data_file} vbe_data ic

echo "Data saved"
quit
.endc

.end
"""
        return self._run_ngspice(netlist, plot_file, data_file)
    
    def plot_mos_idvgs(
        self,
        lib_file: Path,
        device_name: str,
        output_dir: Path,
        mos_type: str = 'nmos',
        vgs_start: float = 0.0,
        vgs_stop: float = 1.8,
        vds: float = 1.0,
        width: float = 1e-6,
        length: float = 180e-9
    ) -> PlotResult:
        """
        Generate MOS Id vs Vgs transfer curve.
        
        Args:
            lib_file: Path to ngspice library file
            device_name: Model or subcircuit name
            output_dir: Directory to save plot and data
            mos_type: 'nmos' or 'pmos'
            vgs_start: Start gate voltage
            vgs_stop: Stop gate voltage
            vds: Drain-source voltage
            width: Device width
            length: Device length
        
        Returns:
            PlotResult with paths to generated files
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        lib_file = Path(lib_file).resolve()
        
        data_file = output_dir / f"{device_name}_idvgs.csv"
        plot_file = output_dir / f"{device_name}_idvgs.png"
        
        # Adjust for PMOS (negative voltages)
        if mos_type.lower() == 'pmos':
            vgs_start, vgs_stop = -abs(vgs_stop), -abs(vgs_start)
            vds = -abs(vds)
        
        netlist = f"""* MOS Id vs Vgs - {device_name}
.include "{lib_file}"

Vdd drain 0 DC {vds}
Vgs gate 0 DC 0
X1 drain gate 0 0 {device_name} W={width} L={length}

.dc Vgs {vgs_start} {vgs_stop} 0.02

.control
run

let id = {'i(Vdd)' if mos_type.lower() == 'pmos' else '-i(Vdd)'}
let vgs_data = v(gate)

set wr_singlescale
set wr_vecnames
wrdata {data_file} vgs_data id

echo "Data saved"
quit
.endc

.end
"""
        return self._run_ngspice(netlist, plot_file, data_file)
    
    def plot_mos_idvds(
        self,
        lib_file: Path,
        device_name: str,
        output_dir: Path,
        mos_type: str = 'nmos',
        vds_start: float = 0.0,
        vds_stop: float = 1.8,
        vgs_values: List[float] = None,
        width: float = 1e-6,
        length: float = 180e-9
    ) -> PlotResult:
        """
        Generate MOS Id vs Vds output characteristics.
        
        Args:
            lib_file: Path to ngspice library file
            device_name: Model or subcircuit name
            output_dir: Directory to save plot and data
            mos_type: 'nmos' or 'pmos'
            vds_start: Start drain voltage
            vds_stop: Stop drain voltage
            vgs_values: List of Vgs values to sweep
            width: Device width
            length: Device length
        
        Returns:
            PlotResult with paths to generated files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if vgs_values is None:
            vgs_values = [0.6, 0.8, 1.0, 1.2, 1.4]
        
        data_file = output_dir / f"{device_name}_idvds.csv"
        plot_file = output_dir / f"{device_name}_idvds.png"
        
        # Adjust for PMOS
        if mos_type.lower() == 'pmos':
            vds_start, vds_stop = -abs(vds_stop), -abs(vds_start)
            vgs_values = [-abs(v) for v in vgs_values]
        
        vgs_str = ' '.join(str(v) for v in vgs_values)
        
        netlist = f"""* MOS Id vs Vds - {device_name}
.include "{lib_file}"

Vdd drain 0 DC 0
Vgs gate 0 DC 0
X1 drain gate 0 0 {device_name} W={width} L={length}

.dc Vdd {vds_start} {vds_stop} 0.02 Vgs list {vgs_str}

.control
run
set filetype=ascii

let id = {'i(Vdd)' if mos_type.lower() == 'pmos' else '-i(Vdd)'}
let vds = v(drain)

set wr_singlescale
set wr_vecnames
wrdata "{data_file}" vds id

set hcopydevtype=png
set hcopypscolor=1
set color0=white
set color1=black
set color2=blue
set color3=red
set color4=green
set color5=orange
set color6=purple

hardcopy "{plot_file}" id vs vds title "Output Curves: {device_name}" xlabel "Vds (V)" ylabel "Id (A)"

echo "Plot saved to {plot_file}"
quit
.endc

.end
"""
        return self._run_ngspice(netlist, plot_file, data_file)
    
    def plot_diode_iv(
        self,
        lib_file: Path,
        device_name: str,
        output_dir: Path,
        v_start: float = -0.5,
        v_stop: float = 1.0
    ) -> PlotResult:
        """
        Generate diode I-V curve.
        
        Args:
            lib_file: Path to ngspice library file
            device_name: Diode model or subcircuit name
            output_dir: Directory to save plot and data
            v_start: Start voltage
            v_stop: Stop voltage
        
        Returns:
            PlotResult with paths to generated files
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        lib_file = Path(lib_file).resolve()
        
        data_file = output_dir / f"{device_name}_iv.csv"
        plot_file = output_dir / f"{device_name}_iv.png"
        
        netlist = f"""* Diode I-V Curve - {device_name}
.include "{lib_file}"

Vd anode 0 DC 0
X1 anode 0 {device_name}

.dc Vd {v_start} {v_stop} 0.01

.control
run

let id = -i(Vd)
let vd_data = v(anode)

set wr_singlescale
set wr_vecnames
wrdata {data_file} vd_data id

echo "Data saved"
quit
.endc

.end
"""
        return self._run_ngspice(netlist, plot_file, data_file)
    
    def plot_capacitor_ac(
        self,
        lib_file: Path,
        device_name: str,
        output_dir: Path,
        freq_start: float = 1e3,
        freq_stop: float = 1e9,
        area: float = 10e-6,
        perim: float = 20e-6
    ) -> PlotResult:
        """
        Generate capacitor AC impedance plot.
        
        Args:
            lib_file: Path to ngspice library file
            device_name: Capacitor subcircuit name
            output_dir: Directory to save plot and data
            freq_start: Start frequency (Hz)
            freq_stop: Stop frequency (Hz)
            area: Capacitor area
            perim: Capacitor perimeter
        
        Returns:
            PlotResult with paths to generated files
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        lib_file = Path(lib_file).resolve()
        
        data_file = output_dir / f"{device_name}_ac.csv"
        plot_file = output_dir / f"{device_name}_ac.png"
        
        netlist = f"""* Capacitor AC Analysis - {device_name}
.include "{lib_file}"

Vac in 0 DC 0 AC 1

X1 in 0 {device_name} area={area} perim={perim}

.ac dec 20 {freq_start} {freq_stop}

.control
run

let z_mag = abs(v(in)/i(Vac))
let freq_data = frequency

set wr_singlescale
set wr_vecnames
wrdata {data_file} freq_data z_mag

echo "Data saved"
quit
.endc

.end
"""
        return self._run_ngspice(netlist, plot_file, data_file)
    
    def plot_resistor_iv(
        self,
        lib_file: Path,
        device_name: str,
        output_dir: Path,
        v_start: float = -1.0,
        v_stop: float = 1.0
    ) -> PlotResult:
        """
        Generate resistor I-V curve.
        
        Args:
            lib_file: Path to ngspice library file
            device_name: Resistor subcircuit name
            output_dir: Directory to save plot and data
            v_start: Start voltage
            v_stop: Stop voltage
        
        Returns:
            PlotResult with paths to generated files
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        lib_file = Path(lib_file).resolve()
        
        data_file = output_dir / f"{device_name}_iv.csv"
        plot_file = output_dir / f"{device_name}_iv.png"
        
        netlist = f"""* Resistor I-V Curve - {device_name}
.include "{lib_file}"

Vr in 0 DC 0
X1 in 0 {device_name}

.dc Vr {v_start} {v_stop} 0.02

.control
run

let ir = -i(Vr)
let vr_data = v(in)

set wr_singlescale
set wr_vecnames
wrdata {data_file} vr_data ir

echo "Data saved"
quit
.endc

.end
"""
        return self._run_ngspice(netlist, plot_file, data_file)
    
    def _run_ngspice(
        self,
        netlist: str,
        plot_file: Path,
        data_file: Path
    ) -> PlotResult:
        """Run ngspice simulation and generate plot/data."""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.sp', delete=False
            ) as f:
                f.write(netlist)
                netlist_file = f.name
            
            result = subprocess.run(
                [self.ngspice, '-b', netlist_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Clean up
            Path(netlist_file).unlink(missing_ok=True)
            
            # Check if data file was generated (more reliable than plot)
            if data_file.exists():
                # Count data points
                data_points = 0
                try:
                    lines = data_file.read_text().strip().split('\n')
                    # Skip header lines
                    data_points = len([l for l in lines if l and not l.startswith('#') and not l.startswith('V')])
                except:
                    pass
                
                # Check if plot was generated (optional - requires X11/gnuplot)
                plot_exists = plot_file.exists()
                
                return PlotResult(
                    success=True,
                    plot_file=plot_file if plot_exists else None,
                    data_file=data_file,
                    error=None if plot_exists else "Data saved (PNG requires X11/gnuplot backend)",
                    data_points=data_points
                )
            else:
                # Check for simulation errors
                if 'Error' in result.stderr or result.returncode != 0:
                    error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
                    return PlotResult(
                        success=False,
                        plot_file=None,
                        data_file=None,
                        error=f"Simulation failed: {error_msg}"
                    )
                else:
                    return PlotResult(
                        success=False,
                        plot_file=None,
                        data_file=None,
                        error=f"Data file not generated. Output: {result.stdout[-300:]}"
                    )
                
        except subprocess.TimeoutExpired:
            return PlotResult(
                success=False,
                plot_file=None,
                data_file=None,
                error="Simulation timed out (60s)"
            )
        except Exception as e:
            return PlotResult(
                success=False,
                plot_file=None,
                data_file=None,
                error=str(e)
            )


def plot_device(
    lib_file: str,
    device_name: str,
    device_class: str,
    output_dir: Optional[str] = None,
    **kwargs
) -> PlotResult:
    """
    Convenience function to plot any device type.
    
    Args:
        lib_file: Path to ngspice library
        device_name: Device/model name
        device_class: 'mos', 'bjt', 'diode', 'capacitor', 'resistor'
        output_dir: Output directory (default: same as lib_file)
        **kwargs: Device-specific parameters
    
    Returns:
        PlotResult
    
    Example:
        result = plot_device(
            lib_file='output/gpdk090_bipolar.lib',
            device_name='gpdk090_npn',
            device_class='bjt'
        )
        print(f"Plot saved to: {result.plot_file}")
    """
    lib_path = Path(lib_file)
    
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = lib_path.parent
    
    plotter = SimulationPlotter()
    
    # Filter kwargs for each device class
    if device_class == 'bjt':
        bjt_kwargs = {k: v for k, v in kwargs.items() if k in ['vbe_start', 'vbe_stop', 'vcc']}
        return plotter.plot_bjt_gummel(lib_path, device_name, out_path, **bjt_kwargs)
    elif device_class == 'mos':
        mos_kwargs = {k: v for k, v in kwargs.items() if k in ['mos_type', 'vgs_start', 'vgs_stop', 'vds', 'width', 'length']}
        return plotter.plot_mos_idvgs(lib_path, device_name, out_path, **mos_kwargs)
    elif device_class == 'diode':
        diode_kwargs = {k: v for k, v in kwargs.items() if k in ['v_start', 'v_stop']}
        return plotter.plot_diode_iv(lib_path, device_name, out_path, **diode_kwargs)
    elif device_class == 'capacitor':
        cap_kwargs = {k: v for k, v in kwargs.items() if k in ['freq_start', 'freq_stop', 'area', 'perim']}
        return plotter.plot_capacitor_ac(lib_path, device_name, out_path, **cap_kwargs)
    elif device_class == 'resistor':
        res_kwargs = {k: v for k, v in kwargs.items() if k in ['v_start', 'v_stop']}
        return plotter.plot_resistor_iv(lib_path, device_name, out_path, **res_kwargs)
    else:
        return PlotResult(
            success=False,
            plot_file=None,
            data_file=None,
            error=f"Unknown device class: {device_class}"
        )


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate simulation plots')
    parser.add_argument('lib_file', help='Path to ngspice library file')
    parser.add_argument('device_name', help='Device/subcircuit name')
    parser.add_argument('--device-class', '-c', required=True,
                        choices=['mos', 'bjt', 'diode', 'capacitor', 'resistor'],
                        help='Device class')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--mos-type', choices=['nmos', 'pmos'], default='nmos',
                        help='MOS type for MOS plots')
    
    args = parser.parse_args()
    
    result = plot_device(
        lib_file=args.lib_file,
        device_name=args.device_name,
        device_class=args.device_class,
        output_dir=args.output,
        mos_type=args.mos_type
    )
    
    if result.success:
        if result.data_file:
            print(f"✅ Simulation data saved to: {result.data_file}")
            print(f"   Data points: {result.data_points}")
        if result.plot_file:
            print(f"   Plot saved to: {result.plot_file}")
        if result.error:
            print(f"   Note: {result.error}")
    else:
        print(f"❌ Simulation failed: {result.error}")

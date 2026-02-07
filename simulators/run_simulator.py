"""
Simulator Wrappers

Execute SPICE simulations and collect outputs for metrics extraction.
Provides unified interface across ngspice, HSPICE, and Spectre.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SimulationResult:
    """Result from a SPICE simulation"""
    success: bool
    output_file: Optional[Path]
    stdout: str
    stderr: str
    returncode: int
    simulator: str
    error_message: Optional[str] = None
    status: str = "failed"  # 'passed' | 'failed' | 'skipped'
    skip_reason: Optional[str] = None


class SimulatorError(Exception):
    """Exception raised when simulation fails"""
    pass


def run_ngspice(netlist: str, output_dir: Optional[Path] = None) -> SimulationResult:
    """
    Run ngspice simulation
    
    Args:
        netlist: Netlist content string
        output_dir: Directory for output files
    
    Returns:
        SimulationResult with output paths
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix='ngspice_'))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write netlist to file
    netlist_file = output_dir / 'testbench.cir'
    netlist_file.write_text(netlist)
    
    try:
        result = subprocess.run(
            ['ngspice', '-b', netlist_file.name],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=output_dir
        )
        
        # Find output file (metrics .txt file)
        output_files = list(output_dir.glob('*_metrics*.txt'))
        output_file = output_files[0] if output_files else None
        
        success = result.returncode == 0

        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        combined_lower = combined.lower()

        status = "passed" if success else "failed"
        skip_reason = None

        # Known ngspice limitation (build-dependent): unsupported MOS model levels.
        if (not success) and ("only mos device levels" in combined_lower) and ("supported in this binary" in combined_lower):
            status = "skipped"
            skip_reason = "unsupported_mos_level"

        error_msg = None if success else f"ngspice failed: {(result.stderr or '')[:200]}"
        
        return SimulationResult(
            success=success,
            output_file=output_file,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            simulator='ngspice',
            error_message=error_msg,
            status=status,
            skip_reason=skip_reason,
        )
    
    except subprocess.TimeoutExpired:
        return SimulationResult(
            success=False,
            output_file=None,
            stdout='',
            stderr='Simulation timeout',
            returncode=-1,
            simulator='ngspice',
            error_message='Simulation timeout after 60s',
            status='failed',
        )
    except FileNotFoundError:
        return SimulationResult(
            success=False,
            output_file=None,
            stdout='',
            stderr='ngspice not found',
            returncode=-1,
            simulator='ngspice',
            error_message='ngspice executable not found in PATH',
            status='failed',
        )


def run_hspice(netlist: str, output_dir: Optional[Path] = None) -> SimulationResult:
    """
    Run HSPICE simulation
    
    Args:
        netlist: Netlist content string
        output_dir: Directory for output files
    
    Returns:
        SimulationResult with output paths
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix='hspice_'))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write netlist to file
    netlist_file = output_dir / 'testbench.sp'
    netlist_file.write_text(netlist)
    
    try:
        result = subprocess.run(
            ['hspice', str(netlist_file)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=output_dir
        )
        
        # HSPICE outputs to .lis, .mt0, etc.
        output_files = list(output_dir.glob('*.lis')) + list(output_dir.glob('*.mt0'))
        output_file = output_files[0] if output_files else None
        
        success = result.returncode == 0
        error_msg = None if success else f"HSPICE failed: {result.stderr[:200]}"
        
        return SimulationResult(
            success=success,
            output_file=output_file,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            simulator='hspice',
            error_message=error_msg,
            status='passed' if success else 'failed',
        )
    
    except subprocess.TimeoutExpired:
        return SimulationResult(
            success=False,
            output_file=None,
            stdout='',
            stderr='Simulation timeout',
            returncode=-1,
            simulator='hspice',
            error_message='Simulation timeout after 60s',
            status='failed',
        )
    except FileNotFoundError:
        return SimulationResult(
            success=False,
            output_file=None,
            stdout='',
            stderr='hspice not found',
            returncode=-1,
            simulator='hspice',
            error_message='hspice executable not found in PATH',
            status='failed',
        )


def run_spectre(netlist: str, output_dir: Optional[Path] = None) -> SimulationResult:
    """
    Run Spectre simulation
    
    Args:
        netlist: Netlist content string
        output_dir: Directory for output files
    
    Returns:
        SimulationResult with output paths
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix='spectre_'))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write netlist to file
    netlist_file = output_dir / 'testbench.scs'
    netlist_file.write_text(netlist)
    
    try:
        result = subprocess.run(
            ['spectre', str(netlist_file), '-format', 'psfascii'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=output_dir
        )
        
        # Spectre outputs to .raw directory
        output_files = list(output_dir.glob('*.raw/*'))
        output_file = output_dir if output_files else None
        
        success = result.returncode == 0
        error_msg = None if success else f"Spectre failed: {result.stderr[:200]}"
        
        return SimulationResult(
            success=success,
            output_file=output_file,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            simulator='spectre',
            error_message=error_msg,
            status='passed' if success else 'failed',
        )
    
    except subprocess.TimeoutExpired:
        return SimulationResult(
            success=False,
            output_file=None,
            stdout='',
            stderr='Simulation timeout',
            returncode=-1,
            simulator='spectre',
            error_message='Simulation timeout after 60s',
            status='failed',
        )
    except FileNotFoundError:
        return SimulationResult(
            success=False,
            output_file=None,
            stdout='',
            stderr='spectre not found',
            returncode=-1,
            simulator='spectre',
            error_message='spectre executable not found in PATH',
            status='failed',
        )


def run_simulation(netlist: str, simulator: str, output_dir: Optional[Path] = None) -> SimulationResult:
    """
    Run simulation with specified simulator
    
    Args:
        netlist: Netlist content
        simulator: 'ngspice', 'hspice', or 'spectre'
        output_dir: Output directory
    
    Returns:
        SimulationResult
    """
    simulators = {
        'ngspice': run_ngspice,
        'hspice': run_hspice,
        'spectre': run_spectre
    }
    
    sim_func = simulators.get(simulator.lower())
    if not sim_func:
        raise ValueError(f"Unknown simulator: {simulator}")
    
    return sim_func(netlist, output_dir)

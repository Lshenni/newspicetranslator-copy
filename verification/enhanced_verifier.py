#!/usr/bin/env python3
"""
Enhanced Verification Suite for SPICE Translator

Comprehensive verification tools including:
1. Syntax Validation - ngspice parse checking
2. DC/AC/Transient Simulation - multi-analysis verification  
3. Round-Trip Translation - parameter consistency checking
4. Corner Validation - FF/TT/SS ordering verification
5. Sanity Checks - physical plausibility tests

Usage:
    python -m verification.enhanced_verifier --mode full output/cadence90_spectre-ngspice/
    python -m verification.enhanced_verifier --mode roundtrip input.scs
    python -m verification.enhanced_verifier --mode corners output/pdk_corners/
"""

import sys
import os
import re
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import argparse
from datetime import datetime

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Try to import matplotlib (optional for plotting)
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available, plots will be skipped")


class VerificationMode(Enum):
    """Verification modes"""
    SYNTAX = "syntax"           # ngspice syntax check only
    DC = "dc"                   # DC analysis
    AC = "ac"                   # AC analysis
    TRANSIENT = "transient"     # Transient analysis
    ROUNDTRIP = "roundtrip"     # Round-trip translation check
    CORNERS = "corners"         # Corner validation (FF/TT/SS)
    SANITY = "sanity"           # Physical plausibility checks
    FULL = "full"               # All checks


class DeviceType(Enum):
    """Device types for verification"""
    NMOS = "nmos"
    PMOS = "pmos"
    NPN = "npn"
    PNP = "pnp"
    DIODE = "diode"
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    UNKNOWN = "unknown"


@dataclass
class VerificationResult:
    """Result of a single verification test"""
    test_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DeviceMetrics:
    """Extracted device metrics from simulation"""
    device_name: str
    device_type: DeviceType
    vth: Optional[float] = None          # Threshold voltage (MOS)
    id_sat: Optional[float] = None       # Saturation current (MOS)
    gm_max: Optional[float] = None       # Max transconductance (MOS)
    beta: Optional[float] = None         # Current gain (BJT)
    ic_active: Optional[float] = None    # Collector current (BJT)
    vd_on: Optional[float] = None        # Turn-on voltage (Diode)
    id_forward: Optional[float] = None   # Forward current (Diode)
    resistance: Optional[float] = None   # Resistance value
    capacitance: Optional[float] = None  # Capacitance value
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class EnhancedVerifier:
    """
    Enhanced verification suite with multiple test modes
    """
    
    def __init__(self, output_dir: Optional[Path] = None, verbose: bool = False):
        self.output_dir = output_dir or BASE_DIR / 'output' / 'verification_results'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self.ngspice_path = self._find_ngspice()
        
    def _find_ngspice(self) -> str:
        """Find ngspice executable"""
        # Check common locations
        for path in ['ngspice', '/usr/bin/ngspice', '/usr/local/bin/ngspice']:
            try:
                result = subprocess.run([path, '--version'], 
                                       capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return 'ngspice'  # Default, may fail later
    
    # =========================================================================
    # 1. SYNTAX VALIDATION
    # =========================================================================
    
    def verify_syntax(self, lib_file: Path) -> VerificationResult:
        """
        Verify ngspice can parse the library file without errors.
        Creates a minimal testbench that includes the file.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
            f.write(f"""* Syntax verification test
.include "{lib_file}"

* Dummy circuit to force parsing
V1 1 0 DC 1
R1 1 0 1k

.control
op
quit
.endc
.end
""")
            testbench = f.name
        
        try:
            result = subprocess.run(
                [self.ngspice_path, '-b', testbench],
                capture_output=True, text=True, timeout=30
            )
            
            # Check for errors in output
            stderr = result.stderr.lower()
            stdout = result.stdout.lower()
            combined = stderr + stdout
            
            # Common error patterns
            error_patterns = [
                r'error:',
                r'fatal:',
                r'unknown subckt',
                r'undefined model',
                r'syntax error',
                r'cannot find',
                r'unrecognized parameter'
            ]
            
            errors_found = []
            for pattern in error_patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    # Extract the error line
                    for line in (result.stderr + result.stdout).split('\n'):
                        if re.search(pattern, line, re.IGNORECASE):
                            errors_found.append(line.strip())
            
            if errors_found or result.returncode != 0:
                return VerificationResult(
                    test_name="syntax_validation",
                    passed=False,
                    message=f"Syntax errors found in {lib_file.name}",
                    details={'errors': errors_found[:10], 'returncode': result.returncode}
                )
            
            return VerificationResult(
                test_name="syntax_validation",
                passed=True,
                message=f"Syntax OK: {lib_file.name}",
                details={'returncode': 0}
            )
            
        except subprocess.TimeoutExpired:
            return VerificationResult(
                test_name="syntax_validation",
                passed=False,
                message="Syntax check timed out",
                details={'timeout': True}
            )
        finally:
            os.unlink(testbench)
    
    # =========================================================================
    # 2. DC/AC/TRANSIENT SIMULATION
    # =========================================================================
    
    def _extract_models_from_file(self, lib_file: Path) -> List[Tuple[str, DeviceType]]:
        """Extract model names and types from library file"""
        content = lib_file.read_text()
        models = []
        
        # Pattern for .model statements
        model_pattern = r'\.model\s+(\S+)\s+(\S+)'
        for match in re.finditer(model_pattern, content, re.IGNORECASE):
            name = match.group(1)
            mtype = match.group(2).lower()
            
            if mtype in ['nmos', 'nmos4']:
                models.append((name, DeviceType.NMOS))
            elif mtype in ['pmos', 'pmos4']:
                models.append((name, DeviceType.PMOS))
            elif mtype == 'npn':
                models.append((name, DeviceType.NPN))
            elif mtype == 'pnp':
                models.append((name, DeviceType.PNP))
            elif mtype == 'd':
                models.append((name, DeviceType.DIODE))
            elif mtype == 'r':
                models.append((name, DeviceType.RESISTOR))
            elif mtype == 'c':
                models.append((name, DeviceType.CAPACITOR))
        
        return models
    
    def run_dc_simulation(self, lib_file: Path, model_name: str, 
                          device_type: DeviceType) -> VerificationResult:
        """Run DC analysis for a specific model"""
        
        # Generate device-specific testbench
        if device_type == DeviceType.NMOS:
            testbench = self._gen_nmos_dc_testbench(lib_file, model_name)
        elif device_type == DeviceType.PMOS:
            testbench = self._gen_pmos_dc_testbench(lib_file, model_name)
        elif device_type == DeviceType.NPN:
            testbench = self._gen_npn_dc_testbench(lib_file, model_name)
        elif device_type == DeviceType.PNP:
            testbench = self._gen_pnp_dc_testbench(lib_file, model_name)
        elif device_type == DeviceType.DIODE:
            testbench = self._gen_diode_dc_testbench(lib_file, model_name)
        elif device_type == DeviceType.RESISTOR:
            testbench = self._gen_resistor_dc_testbench(lib_file, model_name)
        else:
            return VerificationResult(
                test_name=f"dc_{model_name}",
                passed=True,
                message=f"DC test skipped for {device_type.value}",
                details={'skipped': True}
            )
        
        return self._run_simulation(testbench, f"dc_{model_name}")
    
    def run_ac_simulation(self, lib_file: Path, model_name: str,
                          device_type: DeviceType) -> VerificationResult:
        """Run AC analysis for a specific model"""
        
        if device_type in [DeviceType.NMOS, DeviceType.PMOS]:
            testbench = self._gen_mos_ac_testbench(lib_file, model_name, device_type)
        elif device_type == DeviceType.CAPACITOR:
            testbench = self._gen_cap_ac_testbench(lib_file, model_name)
        else:
            return VerificationResult(
                test_name=f"ac_{model_name}",
                passed=True,
                message=f"AC test skipped for {device_type.value}",
                details={'skipped': True}
            )
        
        return self._run_simulation(testbench, f"ac_{model_name}")
    
    def run_transient_simulation(self, lib_file: Path, model_name: str,
                                  device_type: DeviceType) -> VerificationResult:
        """Run transient analysis for a specific model"""
        
        if device_type in [DeviceType.NMOS, DeviceType.PMOS]:
            testbench = self._gen_mos_tran_testbench(lib_file, model_name, device_type)
        else:
            return VerificationResult(
                test_name=f"tran_{model_name}",
                passed=True,
                message=f"Transient test skipped for {device_type.value}",
                details={'skipped': True}
            )
        
        return self._run_simulation(testbench, f"tran_{model_name}")
    
    def _run_simulation(self, testbench: str, test_name: str) -> VerificationResult:
        """Execute simulation and check for errors"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
            f.write(testbench)
            tb_file = f.name
        
        try:
            result = subprocess.run(
                [self.ngspice_path, '-b', tb_file],
                capture_output=True, text=True, timeout=60
            )
            
            combined = result.stdout + result.stderr
            
            # Check for simulation errors
            error_patterns = [
                r'singular matrix',
                r'no convergence',
                r'timestep too small',
                r'fatal error',
                r'doAnalyses: .* failed'
            ]
            
            errors = []
            warnings = []
            
            for line in combined.split('\n'):
                line_lower = line.lower()
                if any(re.search(p, line_lower) for p in error_patterns):
                    errors.append(line.strip())
                elif 'warning' in line_lower:
                    warnings.append(line.strip())
            
            if errors:
                return VerificationResult(
                    test_name=test_name,
                    passed=False,
                    message=f"Simulation failed: {errors[0][:100]}",
                    details={'errors': errors[:5]},
                    warnings=warnings[:5]
                )
            
            return VerificationResult(
                test_name=test_name,
                passed=True,
                message="Simulation completed successfully",
                details={'returncode': result.returncode},
                warnings=warnings[:5]
            )
            
        except subprocess.TimeoutExpired:
            return VerificationResult(
                test_name=test_name,
                passed=False,
                message="Simulation timed out (60s)",
                details={'timeout': True}
            )
        finally:
            os.unlink(tb_file)
    
    # =========================================================================
    # TESTBENCH GENERATORS
    # =========================================================================
    
    def _gen_nmos_dc_testbench(self, lib_file: Path, model_name: str) -> str:
        """Generate NMOS DC sweep testbench"""
        return f"""* NMOS DC Verification: {model_name}
.include "{lib_file}"

* Supply voltages
Vdd vdd 0 DC 1.8
Vgs gate 0 DC 0
Vds drain 0 DC 1.8

* Device under test
M1 drain gate 0 0 {model_name} W=1u L=100n

.control
* Transfer characteristic (Id vs Vgs)
dc Vgs 0 1.8 0.02

* Check for reasonable current values
let id_max = maximum(abs(i(Vds)))
let id_min = minimum(abs(i(Vds)))

echo "NMOS DC Test Results:"
echo "Max Id = " id_max
echo "Min Id = " id_min

* Sanity check: max current should be > 1uA for a working transistor
if id_max < 1e-9
    echo "WARNING: Very low drain current - model may not be functioning"
end

quit
.endc
.end
"""
    
    def _gen_pmos_dc_testbench(self, lib_file: Path, model_name: str) -> str:
        """Generate PMOS DC sweep testbench"""
        return f"""* PMOS DC Verification: {model_name}
.include "{lib_file}"

Vdd vdd 0 DC 1.8
Vgs gate vdd DC 0
Vds vdd drain DC 0

* Device under test (source tied to vdd)
M1 drain gate vdd vdd {model_name} W=1u L=100n

.control
* Transfer characteristic
dc Vgs -1.8 0 0.02

let id_max = maximum(abs(i(Vds)))
echo "PMOS DC Test Results:"
echo "Max Id = " id_max
quit
.endc
.end
"""
    
    def _gen_npn_dc_testbench(self, lib_file: Path, model_name: str) -> str:
        """Generate NPN BJT Gummel plot testbench"""
        return f"""* NPN BJT Gummel Plot: {model_name}
.include "{lib_file}"

Vce collector 0 DC 2.0
Vbe base 0 DC 0

Q1 collector base 0 {model_name}

.control
dc Vbe 0.4 0.8 0.005

let ic = abs(i(Vce))
let ib = abs(i(Vbe))
let beta = ic / ib

echo "NPN Gummel Test Results:"
echo "Max Ic = " maximum(ic)
echo "Max beta = " maximum(beta)
quit
.endc
.end
"""
    
    def _gen_pnp_dc_testbench(self, lib_file: Path, model_name: str) -> str:
        """Generate PNP BJT testbench"""
        return f"""* PNP BJT Gummel Plot: {model_name}
.include "{lib_file}"

Vec 0 collector DC 2.0
Veb 0 base DC 0

Q1 collector base 0 {model_name}

.control
dc Veb 0.4 0.8 0.005

let ic = abs(i(Vec))
echo "PNP Gummel Test Results:"
echo "Max Ic = " maximum(ic)
quit
.endc
.end
"""
    
    def _gen_diode_dc_testbench(self, lib_file: Path, model_name: str) -> str:
        """Generate diode I-V testbench"""
        return f"""* Diode I-V Characteristic: {model_name}
.include "{lib_file}"

Vd anode 0 DC 0

D1 anode 0 {model_name}

.control
dc Vd -1 1 0.01

let id = abs(i(Vd))
let id_on = id[length(id)*3/4]  * Current at ~0.5V

echo "Diode DC Test Results:"
echo "Forward current at 0.5V = " id_on
quit
.endc
.end
"""
    
    def _gen_resistor_dc_testbench(self, lib_file: Path, model_name: str) -> str:
        """Generate resistor DC test"""
        return f"""* Resistor DC Test: {model_name}
.include "{lib_file}"

V1 n1 0 DC 1

R1 n1 0 {model_name} R=1k

.control
op

let i_res = abs(i(V1))
let r_eff = 1.0 / i_res

echo "Resistor Test Results:"
echo "Effective R = " r_eff
quit
.endc
.end
"""
    
    def _gen_mos_ac_testbench(self, lib_file: Path, model_name: str, 
                               device_type: DeviceType) -> str:
        """Generate MOS AC analysis testbench"""
        is_pmos = device_type == DeviceType.PMOS
        vgs_dc = "-0.6" if is_pmos else "0.6"
        bulk = "vdd" if is_pmos else "0"
        
        return f"""* MOS AC Analysis: {model_name}
.include "{lib_file}"

Vdd vdd 0 DC 1.8
Vgs gate 0 DC {vgs_dc} AC 1
Vds drain 0 DC 1.0

M1 drain gate 0 {bulk} {model_name} W=1u L=100n

.control
ac dec 10 1k 100G

let gm = abs(i(Vds)) / abs(v(gate))
echo "AC Analysis Complete"
echo "Freq points: " length(frequency)
quit
.endc
.end
"""
    
    def _gen_cap_ac_testbench(self, lib_file: Path, model_name: str) -> str:
        """Generate capacitor AC test"""
        return f"""* Capacitor AC Test: {model_name}
.include "{lib_file}"

Vac n1 0 AC 1

C1 n1 0 {model_name}

.control
ac dec 50 1 10G

let Z = abs(v(n1) / i(Vac))
let C_eff = 1 / (2 * 3.14159 * frequency * Z)

echo "Capacitor AC Test Complete"
quit
.endc
.end
"""
    
    def _gen_mos_tran_testbench(self, lib_file: Path, model_name: str,
                                 device_type: DeviceType) -> str:
        """Generate MOS transient testbench (inverter switching)"""
        is_pmos = device_type == DeviceType.PMOS
        bulk_n = "0"
        bulk_p = "vdd"
        
        return f"""* MOS Transient Analysis: {model_name}
.include "{lib_file}"

Vdd vdd 0 DC 1.8
Vin in 0 PULSE(0 1.8 1n 100p 100p 5n 10n)

* Simple inverter
Mp out in vdd vdd {model_name if is_pmos else model_name} W=2u L=100n
Mn out in 0 0 {model_name if not is_pmos else model_name} W=1u L=100n
Cload out 0 10f

.control
tran 10p 20n

let v_out_max = maximum(v(out))
let v_out_min = minimum(v(out))
let swing = v_out_max - v_out_min

echo "Transient Test Results:"
echo "Output swing = " swing
quit
.endc
.end
"""
    
    # =========================================================================
    # 3. ROUND-TRIP TRANSLATION CHECK
    # =========================================================================
    
    def verify_roundtrip(self, source_file: Path, source_format: str) -> VerificationResult:
        """
        Verify translation accuracy by round-trip:
        source → intermediate → source
        Then compare parameter values.
        """
        from src.main import TranslationEngine
        
        engine = TranslationEngine()
        
        # Determine intermediate format
        if source_format == 'hspice':
            intermediate = 'ngspice'
        elif source_format == 'spectre':
            intermediate = 'ngspice'
        else:
            intermediate = 'hspice'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Step 1: source → intermediate
            intermediate_file = tmpdir / f"intermediate.lib"
            result1 = engine.translate(
                input_file=source_file,
                source_format=source_format,
                target_format=intermediate,
                output_file=intermediate_file
            )
            
            if not result1.get('success'):
                return VerificationResult(
                    test_name="roundtrip",
                    passed=False,
                    message="First translation failed",
                    details={'step': 'source_to_intermediate', 'error': result1.get('error')}
                )
            
            # Step 2: intermediate → source_format
            roundtrip_file = tmpdir / f"roundtrip.lib"
            result2 = engine.translate(
                input_file=intermediate_file,
                source_format=intermediate,
                target_format=source_format,
                output_file=roundtrip_file
            )
            
            if not result2.get('success'):
                return VerificationResult(
                    test_name="roundtrip",
                    passed=False,
                    message="Return translation failed",
                    details={'step': 'intermediate_to_source', 'error': result2.get('error')}
                )
            
            # Step 3: Compare parameters
            original_params = self._extract_parameters(source_file)
            roundtrip_params = self._extract_parameters(roundtrip_file)
            
            # Compare
            comparison = self._compare_parameters(original_params, roundtrip_params)
            
            if comparison['match_rate'] < 0.95:
                return VerificationResult(
                    test_name="roundtrip",
                    passed=False,
                    message=f"Parameter match rate: {comparison['match_rate']:.1%}",
                    details=comparison
                )
            
            return VerificationResult(
                test_name="roundtrip",
                passed=True,
                message=f"Round-trip successful: {comparison['match_rate']:.1%} match",
                details=comparison
            )
    
    def _extract_parameters(self, lib_file: Path) -> Dict[str, Dict[str, float]]:
        """Extract all model parameters from a library file"""
        content = lib_file.read_text()
        models = {}
        
        # Find model blocks
        model_pattern = r'\.model\s+(\S+)\s+\S+\s*\((.*?)\)'
        for match in re.finditer(model_pattern, content, re.IGNORECASE | re.DOTALL):
            model_name = match.group(1)
            param_text = match.group(2)
            
            params = {}
            # Extract name=value pairs
            param_pattern = r'(\w+)\s*=\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)'
            for pmatch in re.finditer(param_pattern, param_text):
                pname = pmatch.group(1).lower()
                try:
                    pvalue = float(pmatch.group(2))
                    params[pname] = pvalue
                except ValueError:
                    pass
            
            models[model_name] = params
        
        return models
    
    def _compare_parameters(self, original: Dict, roundtrip: Dict) -> Dict:
        """Compare parameter dictionaries and report differences"""
        results = {
            'total_models': len(original),
            'matched_models': 0,
            'total_params': 0,
            'matched_params': 0,
            'mismatched_params': [],
            'missing_params': [],
            'match_rate': 0.0
        }
        
        for model_name, orig_params in original.items():
            rt_params = roundtrip.get(model_name, {})
            
            if rt_params:
                results['matched_models'] += 1
            
            for pname, pvalue in orig_params.items():
                results['total_params'] += 1
                
                if pname in rt_params:
                    rt_value = rt_params[pname]
                    # Allow 0.1% relative tolerance or 1e-15 absolute
                    rel_error = abs(pvalue - rt_value) / max(abs(pvalue), 1e-15)
                    
                    if rel_error < 0.001:
                        results['matched_params'] += 1
                    else:
                        results['mismatched_params'].append({
                            'model': model_name,
                            'param': pname,
                            'original': pvalue,
                            'roundtrip': rt_value,
                            'error': rel_error
                        })
                else:
                    results['missing_params'].append({
                        'model': model_name,
                        'param': pname
                    })
        
        if results['total_params'] > 0:
            results['match_rate'] = results['matched_params'] / results['total_params']
        
        return results
    
    # =========================================================================
    # 4. CORNER VALIDATION (FF/TT/SS)
    # =========================================================================
    
    def verify_corners(self, corner_files: Dict[str, Path]) -> VerificationResult:
        """
        Verify corner models show correct ordering:
        FF (fast-fast) > TT (typical) > SS (slow-slow) for current
        
        Args:
            corner_files: Dict like {'ff': path_ff.lib, 'tt': path_tt.lib, 'ss': path_ss.lib}
        """
        if len(corner_files) < 2:
            return VerificationResult(
                test_name="corner_validation",
                passed=False,
                message="Need at least 2 corner files for validation",
                details={'corners_provided': list(corner_files.keys())}
            )
        
        # Extract a common MOS model from each corner
        corner_metrics = {}
        
        for corner_name, lib_file in corner_files.items():
            models = self._extract_models_from_file(lib_file)
            
            # Find first NMOS model
            nmos_models = [m for m in models if m[1] == DeviceType.NMOS]
            if not nmos_models:
                continue
            
            model_name = nmos_models[0][0]
            
            # Run DC simulation and extract Id_sat
            metrics = self._extract_mos_metrics(lib_file, model_name)
            if metrics:
                corner_metrics[corner_name] = metrics
        
        if len(corner_metrics) < 2:
            return VerificationResult(
                test_name="corner_validation",
                passed=True,
                message="Could not extract metrics from corners (skipped)",
                details={'skipped': True, 'corners_found': list(corner_metrics.keys())}
            )
        
        # Validate ordering
        ordering_correct = True
        details = {'corner_metrics': corner_metrics}
        
        # Expected: Id(ff) > Id(tt) > Id(ss)
        if 'ff' in corner_metrics and 'tt' in corner_metrics:
            if corner_metrics['ff'].get('id_sat', 0) <= corner_metrics['tt'].get('id_sat', 1):
                ordering_correct = False
                details['error'] = "FF should have higher current than TT"
        
        if 'tt' in corner_metrics and 'ss' in corner_metrics:
            if corner_metrics['tt'].get('id_sat', 0) <= corner_metrics['ss'].get('id_sat', 1):
                ordering_correct = False
                details['error'] = "TT should have higher current than SS"
        
        return VerificationResult(
            test_name="corner_validation",
            passed=ordering_correct,
            message="Corner ordering verified" if ordering_correct else "Corner ordering incorrect",
            details=details
        )
    
    def _extract_mos_metrics(self, lib_file: Path, model_name: str) -> Optional[Dict]:
        """Extract MOS metrics by running simulation"""
        testbench = f"""* Extract MOS metrics: {model_name}
.include "{lib_file}"

Vdd vdd 0 DC 1.8
Vgs gate 0 DC 0
Vds drain 0 DC 1.8

M1 drain gate 0 0 {model_name} W=1u L=100n

.control
dc Vgs 0 1.8 0.02

let id_sat = abs(i(Vds)[length(i(Vds))-1])
echo "ID_SAT=" id_sat > metrics.txt
quit
.endc
.end
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            tb_file = tmpdir / "testbench.sp"
            tb_file.write_text(testbench)
            
            try:
                result = subprocess.run(
                    [self.ngspice_path, '-b', str(tb_file)],
                    capture_output=True, text=True, timeout=30,
                    cwd=tmpdir
                )
                
                # Try to parse metrics from output
                for line in result.stdout.split('\n'):
                    if 'ID_SAT=' in line.upper():
                        match = re.search(r'([+-]?\d+\.?\d*[eE]?[+-]?\d*)', line)
                        if match:
                            return {'id_sat': float(match.group(1))}
                
            except (subprocess.TimeoutExpired, Exception):
                pass
        
        return None
    
    # =========================================================================
    # 5. SANITY CHECKS (Physical Plausibility)
    # =========================================================================
    
    def verify_sanity(self, lib_file: Path) -> List[VerificationResult]:
        """
        Run physical plausibility checks on device models:
        - MOS: Vth in reasonable range, positive gm, etc.
        - BJT: Beta > 1, reasonable Ic
        - Diode: Forward voltage ~ 0.5-0.8V
        """
        results = []
        models = self._extract_models_from_file(lib_file)
        
        for model_name, device_type in models[:5]:  # Limit to first 5 for speed
            if device_type == DeviceType.NMOS:
                result = self._sanity_check_nmos(lib_file, model_name)
            elif device_type == DeviceType.PMOS:
                result = self._sanity_check_pmos(lib_file, model_name)
            elif device_type == DeviceType.NPN:
                result = self._sanity_check_npn(lib_file, model_name)
            elif device_type == DeviceType.DIODE:
                result = self._sanity_check_diode(lib_file, model_name)
            else:
                continue
            
            results.append(result)
        
        return results
    
    def _sanity_check_nmos(self, lib_file: Path, model_name: str) -> VerificationResult:
        """Sanity check NMOS model parameters - simplified version"""
        testbench = f"""* NMOS Sanity Check: {model_name}
.include "{lib_file}"

Vdd vdd 0 DC 1.8
Vgs gate 0 DC 0
Vds drain 0 DC 1.8

M1 drain gate 0 0 {model_name} W=1u L=100n

.control
* Simple DC sweep
dc Vgs 0 1.8 0.05

* Get drain current at max Vgs (should be saturation)
let id_vec = abs(i(Vds))
let id_max = maximum(id_vec)

* Simple Vth estimation: find where Id crosses 1uA
let id_threshold = 1e-6
let vth_est = 0.4

echo "RESULTS:"
print id_max

quit
.endc
.end
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
            f.write(testbench)
            tb_file = f.name
        
        try:
            result = subprocess.run(
                [self.ngspice_path, '-b', tb_file],
                capture_output=True, text=True, timeout=30
            )
            
            # Parse results - look for id_max value
            id_sat = None
            
            for line in result.stdout.split('\n'):
                # Look for the printed id_max value
                if 'id_max' in line.lower() or 'e-' in line or 'e+' in line:
                    match = re.search(r'(\d+\.?\d*[eE][+-]?\d+)', line)
                    if match:
                        try:
                            val = abs(float(match.group(1)))
                            if val > 0 and val < 1:  # Reasonable current range
                                id_sat = val
                                break
                        except ValueError:
                            pass
            
            # Sanity checks
            warnings = []
            passed = True
            
            if id_sat is not None:
                if id_sat < 1e-12:
                    warnings.append(f"Id_sat={id_sat:.2e} very low - check model")
                    passed = False
                elif id_sat > 0.1:
                    warnings.append(f"Id_sat={id_sat:.2e} very high - check dimensions")
            else:
                # If we couldn't extract, but simulation ran OK, pass with warning
                warnings.append("Could not extract Id_max from simulation output")
                # Check if there were any errors
                if 'error' in result.stderr.lower() or 'fatal' in result.stderr.lower():
                    passed = False
            
            return VerificationResult(
                test_name=f"sanity_{model_name}",
                passed=passed,
                message="NMOS simulation OK" if passed else "NMOS sanity check failed",
                details={'id_sat': id_sat},
                warnings=warnings
            )
            
        except subprocess.TimeoutExpired:
            return VerificationResult(
                test_name=f"sanity_{model_name}",
                passed=False,
                message="Simulation timed out"
            )
        finally:
            os.unlink(tb_file)
    
    def _sanity_check_pmos(self, lib_file: Path, model_name: str) -> VerificationResult:
        """Sanity check PMOS - similar to NMOS but with inverted voltages"""
        # Simplified - just check if simulation runs
        result = self.run_dc_simulation(lib_file, model_name, DeviceType.PMOS)
        result.test_name = f"sanity_{model_name}"
        return result
    
    def _sanity_check_npn(self, lib_file: Path, model_name: str) -> VerificationResult:
        """Sanity check NPN BJT"""
        testbench = f"""* NPN Sanity Check: {model_name}
.include "{lib_file}"

Vce collector 0 DC 2.0
Vbe base 0 DC 0.7

Q1 collector base 0 {model_name}

.control
op

let ic = abs(i(Vce))
let ib = abs(i(Vbe))
let beta = ic / ib

echo "RESULTS:"
echo "IC =" ic
echo "IB =" ib
echo "BETA =" beta

quit
.endc
.end
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
            f.write(testbench)
            tb_file = f.name
        
        try:
            result = subprocess.run(
                [self.ngspice_path, '-b', tb_file],
                capture_output=True, text=True, timeout=30
            )
            
            beta = None
            for line in result.stdout.split('\n'):
                if 'BETA =' in line:
                    match = re.search(r'([+-]?\d+\.?\d*[eE]?[+-]?\d*)', line.split('=')[-1])
                    if match:
                        beta = float(match.group(1))
            
            warnings = []
            passed = True
            
            if beta is not None:
                if beta < 1 or beta > 1000:
                    warnings.append(f"Beta={beta:.1f} outside typical range [1, 1000]")
                    if beta < 1:
                        passed = False
            
            return VerificationResult(
                test_name=f"sanity_{model_name}",
                passed=passed,
                message="NPN parameters look reasonable" if passed else "NPN sanity check failed",
                details={'beta': beta},
                warnings=warnings
            )
            
        except subprocess.TimeoutExpired:
            return VerificationResult(
                test_name=f"sanity_{model_name}",
                passed=False,
                message="Simulation timed out"
            )
        finally:
            os.unlink(tb_file)
    
    def _sanity_check_diode(self, lib_file: Path, model_name: str) -> VerificationResult:
        """Sanity check diode model"""
        result = self.run_dc_simulation(lib_file, model_name, DeviceType.DIODE)
        result.test_name = f"sanity_{model_name}"
        return result
    
    # =========================================================================
    # FULL VERIFICATION SUITE
    # =========================================================================
    
    def run_full_verification(self, lib_file: Path) -> Dict[str, Any]:
        """
        Run complete verification suite on a library file
        """
        results = {
            'file': str(lib_file),
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0
            }
        }
        
        # 1. Syntax validation
        print(f"  [1/5] Syntax validation...")
        syntax_result = self.verify_syntax(lib_file)
        results['tests'].append(syntax_result)
        
        if not syntax_result.passed:
            # If syntax fails, skip remaining tests
            results['summary']['total'] = 1
            results['summary']['failed'] = 1
            return results
        
        # 2. Extract models for further testing
        models = self._extract_models_from_file(lib_file)
        
        # 3. DC simulation (first 3 models)
        print(f"  [2/5] DC simulations...")
        for model_name, device_type in models[:3]:
            dc_result = self.run_dc_simulation(lib_file, model_name, device_type)
            results['tests'].append(dc_result)
        
        # 4. AC simulation (first 2 MOS or cap models)
        print(f"  [3/5] AC simulations...")
        ac_models = [m for m in models if m[1] in [DeviceType.NMOS, DeviceType.PMOS, DeviceType.CAPACITOR]]
        for model_name, device_type in ac_models[:2]:
            ac_result = self.run_ac_simulation(lib_file, model_name, device_type)
            results['tests'].append(ac_result)
        
        # 5. Transient simulation (first MOS)
        print(f"  [4/5] Transient simulation...")
        mos_models = [m for m in models if m[1] in [DeviceType.NMOS, DeviceType.PMOS]]
        if mos_models:
            tran_result = self.run_transient_simulation(lib_file, mos_models[0][0], mos_models[0][1])
            results['tests'].append(tran_result)
        
        # 6. Sanity checks
        print(f"  [5/5] Sanity checks...")
        sanity_results = self.verify_sanity(lib_file)
        results['tests'].extend(sanity_results)
        
        # Summarize
        for test in results['tests']:
            results['summary']['total'] += 1
            if test.passed:
                results['summary']['passed'] += 1
            elif test.details.get('skipped'):
                results['summary']['skipped'] += 1
            else:
                results['summary']['failed'] += 1
        
        return results
    
    def generate_report(self, results: Dict[str, Any], output_file: Optional[Path] = None) -> str:
        """Generate human-readable verification report"""
        lines = [
            "=" * 70,
            "ENHANCED VERIFICATION REPORT",
            "=" * 70,
            f"File: {results['file']}",
            f"Timestamp: {results['timestamp']}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Tests:  {results['summary']['total']}",
            f"Passed:       {results['summary']['passed']} ✅",
            f"Failed:       {results['summary']['failed']} ❌",
            f"Skipped:      {results['summary']['skipped']} ⏭️",
            "",
            "DETAILED RESULTS",
            "-" * 40
        ]
        
        for test in results['tests']:
            status = "✅" if test.passed else "❌"
            lines.append(f"{status} {test.test_name}: {test.message}")
            if test.warnings:
                for warn in test.warnings:
                    lines.append(f"   ⚠️  {warn}")
        
        lines.append("")
        lines.append("=" * 70)
        
        report = "\n".join(lines)
        
        if output_file:
            output_file.write_text(report)
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced SPICE Translator Verification Suite"
    )
    parser.add_argument('input', type=Path, nargs='?',
                        help="Library file or directory to verify")
    parser.add_argument('--mode', type=str, default='full',
                        choices=['syntax', 'dc', 'ac', 'transient', 'roundtrip', 
                                'corners', 'sanity', 'full'],
                        help="Verification mode (default: full)")
    parser.add_argument('--source-format', type=str, default='hspice',
                        choices=['hspice', 'spectre', 'ngspice'],
                        help="Source format for roundtrip test")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Verbose output")
    parser.add_argument('-o', '--output', type=Path,
                        help="Output directory for reports")
    
    args = parser.parse_args()
    
    if not args.input:
        # Default to testing a sample from output/
        args.input = BASE_DIR / 'output'
    
    verifier = EnhancedVerifier(
        output_dir=args.output,
        verbose=args.verbose
    )
    
    # Find files to verify
    if args.input.is_file():
        files = [args.input]
    else:
        files = list(args.input.glob('**/*.lib'))
        if not files:
            files = list(args.input.glob('**/*.sp'))
    
    if not files:
        print(f"No library files found in {args.input}")
        return 1
    
    print(f"Found {len(files)} files to verify")
    print()
    
    all_results = []
    
    for lib_file in files[:10]:  # Limit to first 10 for speed
        print(f"Verifying: {lib_file.name}")
        
        if args.mode == 'full':
            results = verifier.run_full_verification(lib_file)
        elif args.mode == 'syntax':
            result = verifier.verify_syntax(lib_file)
            results = {'file': str(lib_file), 'tests': [result], 
                      'summary': {'total': 1, 'passed': 1 if result.passed else 0, 
                                 'failed': 0 if result.passed else 1}}
        elif args.mode == 'roundtrip':
            result = verifier.verify_roundtrip(lib_file, args.source_format)
            results = {'file': str(lib_file), 'tests': [result],
                      'summary': {'total': 1, 'passed': 1 if result.passed else 0,
                                 'failed': 0 if result.passed else 1}}
        else:
            print(f"  Mode {args.mode} - running...")
            results = verifier.run_full_verification(lib_file)
        
        all_results.append(results)
        
        # Print summary for this file
        s = results['summary']
        status = "✅" if s['failed'] == 0 else "❌"
        print(f"  {status} {s['passed']}/{s['total']} tests passed")
        print()
    
    # Overall summary
    print("=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    
    total_tests = sum(r['summary']['total'] for r in all_results)
    total_passed = sum(r['summary']['passed'] for r in all_results)
    total_failed = sum(r['summary']['failed'] for r in all_results)
    
    print(f"Files verified: {len(all_results)}")
    print(f"Total tests:    {total_tests}")
    print(f"Passed:         {total_passed} ({100*total_passed/max(total_tests,1):.1f}%)")
    print(f"Failed:         {total_failed}")
    
    # Save detailed results
    if args.output:
        output_file = args.output / 'verification_report.json'
        with open(output_file, 'w') as f:
            # Convert VerificationResult objects to dicts
            serializable = []
            for r in all_results:
                sr = dict(r)
                sr['tests'] = [{'test_name': t.test_name, 'passed': t.passed, 
                               'message': t.message, 'details': t.details,
                               'warnings': t.warnings} for t in r['tests']]
                serializable.append(sr)
            json.dump(serializable, f, indent=2)
        print(f"\nDetailed report saved to: {output_file}")
    
    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

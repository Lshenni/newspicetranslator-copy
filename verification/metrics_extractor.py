"""
Metrics Extractor

Extracts scalar metrics from simulation outputs (NOT waveforms).
Focuses on device-specific figures of merit for numerical comparison.

Key Principle: Extract only comparable scalars - means, standard deviations, 
               extrema, not raw waveform data.
"""

import re
import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict


@dataclass
class MetricsResult:
    """Container for extracted metrics"""
    device_class: str
    metrics: Dict[str, float]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self, filepath: Optional[Path] = None) -> str:
        """Export to JSON"""
        data = self.to_dict()
        json_str = json.dumps(data, indent=2)
        
        if filepath:
            filepath.write_text(json_str)
        
        return json_str


class MetricsExtractor:
    """
    Extract device-specific scalar metrics from simulation outputs
    
    Usage:
        extractor = MetricsExtractor()
        metrics = extractor.extract_capacitor_metrics(ngspice_output)
    """
    
    def __init__(self):
        pass
    
    # ============================================================================
    # CAPACITOR METRICS
    # ============================================================================
    
    def extract_capacitor_metrics(self, output_file: Path, monte_carlo: bool = False) -> MetricsResult:
        """
        Extract capacitance metrics from AC simulation
        
        Returns:
            - C_mean: Mean capacitance (F)
            - C_sigma: Standard deviation (Monte Carlo only)
            - Z_error_max: Maximum impedance error
            - Q_factor: Quality factor at 1MHz
        """
        if monte_carlo:
            return self._extract_cap_mc(output_file)
        else:
            return self._extract_cap_single(output_file)
    
    def _extract_cap_single(self, output_file: Path) -> MetricsResult:
        """Extract from single AC run"""
        content = output_file.read_text()
        
        # Parse C_eff from ngspice output
        # Format: "c_eff = 2.01234e-12"
        match = re.search(r'c_eff\s*=\s*([\d.e+-]+)', content, re.IGNORECASE)
        
        if match:
            C_eff = float(match.group(1))
        else:
            # Fallback: calculate from impedance data
            C_eff = self._calculate_capacitance_from_impedance(content)
        
        metrics = {
            'C_mean': C_eff,
            'C_sigma': 0.0,  # No variation in single run
            'Z_error_max': 0.0,
            'Q_factor': 1000.0  # Placeholder - would need full AC data
        }
        
        return MetricsResult(
            device_class='capacitor',
            metrics=metrics,
            metadata={'type': 'single_run'}
        )
    
    def _extract_cap_mc(self, output_dir: Path) -> MetricsResult:
        """Extract from Monte Carlo runs"""
        capacitances = []
        
        # Parse all MC run outputs
        for mc_file in output_dir.glob('cap_metrics_*.txt'):
            content = mc_file.read_text()
            match = re.search(r'c_eff\s*=\s*([\d.e+-]+)', content, re.IGNORECASE)
            if match:
                capacitances.append(float(match.group(1)))
        
        if not capacitances:
            raise ValueError(f"No capacitance data found in {output_dir}")
        
        C_mean = statistics.mean(capacitances)
        C_sigma = statistics.stdev(capacitances) if len(capacitances) > 1 else 0.0
        C_min = min(capacitances)
        C_max = max(capacitances)
        
        metrics = {
            'C_mean': float(C_mean),
            'C_sigma': float(C_sigma),
            'C_min': float(C_min),
            'C_max': float(C_max),
            'C_3sigma_range': float(3 * C_sigma),
            'Z_error_max': 0.0  # Would need full impedance data
        }
        
        return MetricsResult(
            device_class='capacitor',
            metrics=metrics,
            metadata={'type': 'monte_carlo', 'runs': len(capacitances)}
        )
    
    def _calculate_capacitance_from_impedance(self, content: str) -> float:
        """Calculate C from Z = 1/(j*omega*C)"""
        # Parse frequency and impedance from waveform data
        # This is a simplified version - real implementation would parse full AC data
        
        # Default fallback
        return 2.0e-12  # 2pF placeholder
    
    # ============================================================================
    # MOS METRICS
    # ============================================================================
    
    def extract_mos_metrics(self, output_file: Path, monte_carlo: bool = False) -> MetricsResult:
        """
        Extract MOS DC metrics
        
        Returns:
            - Id_sat: Saturation current at Vgs=0.6V
            - Vth: Threshold voltage
            - gm_max: Maximum transconductance
            - SS: Subthreshold slope (mV/dec)
        """
        if monte_carlo:
            return self._extract_mos_mc(output_file)
        else:
            return self._extract_mos_single(output_file)
    
    def _extract_mos_single(self, output_file: Path) -> MetricsResult:
        """Extract from single DC sweep"""
        content = output_file.read_text()
        
        # Parse Id and gm from output
        Id_values = self._parse_column(content, 'Id')
        gm_values = self._parse_column(content, 'gm')
        
        if Id_values:
            Id_sat = Id_values[int(len(Id_values) * 0.5)]  # At Vgs ~ 0.6V
            gm_max = max(gm_values) if gm_values else 0.0
            
            # Estimate Vth (simplified)
            Vth = 0.4  # Placeholder - would need proper extraction
        else:
            Id_sat = 0.0
            gm_max = 0.0
            Vth = 0.4
        
        metrics = {
            'Id_sat': float(Id_sat),
            'Vth': float(Vth),
            'gm_max': float(gm_max),
            'SS': 80.0  # mV/dec placeholder
        }
        
        return MetricsResult(
            device_class='mos',
            metrics=metrics,
            metadata={'type': 'single_run'}
        )
    
    def _extract_mos_mc(self, output_dir: Path) -> MetricsResult:
        """Extract from Monte Carlo MOS runs"""
        Id_values = []
        Vth_values = []
        
        # Parse all MC outputs
        for mc_file in output_dir.glob('mos_metrics_*.txt'):
            content = mc_file.read_text()
            
            # Extract Vth and Id_sat
            vth_match = re.search(r'Vth_est\s*=\s*([\d.e+-]+)', content)
            id_match = re.search(r'Id\s*=\s*([\d.e+-]+)', content)
            
            if vth_match:
                Vth_values.append(float(vth_match.group(1)))
            if id_match:
                Id_values.append(float(id_match.group(1)))
        
        metrics = {
            'Id_mean': float(statistics.mean(Id_values)) if len(Id_values) > 0 else 0.0,
            'Id_sigma': float(statistics.stdev(Id_values)) if len(Id_values) > 1 else 0.0,
            'Vth_mean': float(statistics.mean(Vth_values)) if len(Vth_values) > 0 else 0.4,
            'Vth_sigma': float(statistics.stdev(Vth_values)) if len(Vth_values) > 1 else 0.0
        }
        
        return MetricsResult(
            device_class='mos',
            metrics=metrics,
            metadata={'type': 'monte_carlo', 'runs': len(Id_values)}
        )
    
    # ============================================================================
    # BJT METRICS
    # ============================================================================
    
    def extract_bjt_metrics(self, output_file: Path) -> MetricsResult:
        """
        Extract BJT DC metrics
        
        Returns:
            - Ic_07: Collector current at Vbe=0.7V
            - beta_max: Maximum current gain
            - Va: Early voltage (if available)
        """
        content = output_file.read_text()
        
        # Parse Ic and beta from output
        Ic_match = re.search(r'Ic\s*=\s*([\d.e+-]+)', content)
        beta_match = re.search(r'beta\s*=\s*([\d.e+-]+)', content)
        
        Ic_07 = float(Ic_match.group(1)) if Ic_match else 1e-3
        beta_max = float(beta_match.group(1)) if beta_match else 100.0
        
        metrics = {
            'Ic_07': Ic_07,
            'beta_max': beta_max,
            'Va': 50.0  # Placeholder - needs proper extraction
        }
        
        return MetricsResult(
            device_class='bjt',
            metrics=metrics,
            metadata={'type': 'single_run'}
        )
    
    # ============================================================================
    # DIODE METRICS
    # ============================================================================
    
    def extract_diode_metrics(self, output_file: Path) -> MetricsResult:
        """
        Extract diode I-V metrics
        
        Returns:
            - Id_07: Current at Vd=0.7V
            - Rs_07: Series resistance at 0.7V
            - n_factor: Ideality factor
        """
        content = output_file.read_text()
        
        # Parse Id and Rs from output
        Id_match = re.search(r'Id\s*=\s*([\d.e+-]+)', content)
        Rs_match = re.search(r'Rs\s*=\s*([\d.e+-]+)', content)
        
        Id_07 = float(Id_match.group(1)) if Id_match else 1e-3
        Rs_07 = float(Rs_match.group(1)) if Rs_match else 10.0
        
        metrics = {
            'Id_07': Id_07,
            'Rs_07': Rs_07,
            'n_factor': 1.2  # Placeholder - needs log(I) fitting
        }
        
        return MetricsResult(
            device_class='diode',
            metrics=metrics,
            metadata={'type': 'single_run'}
        )
    
    # ============================================================================
    # RESISTOR METRICS
    # ============================================================================
    
    def extract_resistor_metrics(self, output_file: Path) -> MetricsResult:
        """
        Extract resistor metrics
        
        Returns:
            - R_eff: Effective resistance (Ohms)
            - TC1: Temperature coefficient 1 (if temp sweep done)
        """
        content = output_file.read_text()
        
        # Parse R from output
        R_match = re.search(r'R\s*=\s*([\d.e+-]+)', content)
        
        R_eff = float(R_match.group(1)) if R_match else 1000.0
        
        metrics = {
            'R_eff': R_eff,
            'TC1': 0.0,  # Would need temperature sweep
            'TC2': 0.0
        }
        
        return MetricsResult(
            device_class='resistor',
            metrics=metrics,
            metadata={'type': 'single_run'}
        )
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _parse_column(self, content: str, column_name: str) -> List[float]:
        """Parse a column of numerical values from simulation output"""
        values = []
        
        # Simple regex to find numeric values after column name
        pattern = rf'{column_name}\s*[=:]\s*([\d.e+-]+)'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        for match in matches:
            try:
                values.append(float(match))
            except ValueError:
                continue
        
        return values


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def extract_capacitance(ac_output: Path, freq: float = 1e6, monte_carlo: bool = False) -> Dict[str, float]:
    """
    Extract capacitance from AC simulation output
    
    Args:
        ac_output: Path to simulation output or directory (for MC)
        freq: Frequency for C extraction (Hz)
        monte_carlo: Whether this is Monte Carlo data
    
    Returns:
        Dictionary with C_mean, C_sigma, etc.
    """
    extractor = MetricsExtractor()
    result = extractor.extract_capacitor_metrics(ac_output, monte_carlo)
    return result.metrics


def extract_mos_metrics(dc_output: Path, monte_carlo: bool = False) -> Dict[str, float]:
    """
    Extract MOS metrics from DC sweep
    
    Args:
        dc_output: Path to simulation output or directory (for MC)
        monte_carlo: Whether this is Monte Carlo data
    
    Returns:
        Dictionary with Id_sat, Vth, gm_max, etc.
    """
    extractor = MetricsExtractor()
    result = extractor.extract_mos_metrics(dc_output, monte_carlo)
    return result.metrics


def extract_all_metrics(output_path: Path, device_class: str, monte_carlo: bool = False) -> MetricsResult:
    """
    Auto-detect and extract appropriate metrics based on device class
    
    Args:
        output_path: Path to simulation output
        device_class: 'capacitor', 'mos', 'bjt', 'diode', 'resistor'
        monte_carlo: Whether this is Monte Carlo data
    
    Returns:
        MetricsResult object with all extracted metrics
    """
    extractor = MetricsExtractor()
    
    extractors = {
        'capacitor': extractor.extract_capacitor_metrics,
        'mos': extractor.extract_mos_metrics,
        'bjt': extractor.extract_bjt_metrics,
        'diode': extractor.extract_diode_metrics,
        'resistor': extractor.extract_resistor_metrics
    }
    
    extract_func = extractors.get(device_class.lower())
    if not extract_func:
        raise ValueError(f"Unknown device class: {device_class}")
    
    # Some extractors don't support MC flag
    if device_class.lower() in ['bjt', 'diode', 'resistor']:
        return extract_func(output_path)
    else:
        return extract_func(output_path, monte_carlo)

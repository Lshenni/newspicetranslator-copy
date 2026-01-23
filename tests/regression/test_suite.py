"""
Regression Test Suite

Defines standard test cases for CI/regression testing.
Ensures no future changes break verified functionality.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RegressionTestCase:
    """Single regression test definition"""
    name: str
    device_file: str
    device_name: str
    device_class: str
    source_format: str
    target_format: str
    device_params: Dict
    expected_metrics: Optional[Dict] = None
    strict: bool = False
    monte_carlo_runs: int = 0


# ============================================================================
# CAPACITOR TESTS
# ============================================================================

CAP_TESTS = [
    RegressionTestCase(
        name="gpdk090_mimcap_spectre_to_ngspice",
        device_file="tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs",
        device_name="mimcap",
        device_class="capacitor",
        source_format="spectre",
        target_format="ngspice",
        device_params={'area': 10e-6, 'perim': 20e-6},
        expected_metrics={'C_mean': 2.0e-12},  # ~2pF
        strict=False
    ),
    RegressionTestCase(
        name="gpdk090_mimcap_spectre_to_hspice",
        device_file="tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs",
        device_name="mimcap",
        device_class="capacitor",
        source_format="spectre",
        target_format="hspice",
        device_params={'area': 10e-6, 'perim': 20e-6},
        expected_metrics={'C_mean': 2.0e-12}
    ),
    RegressionTestCase(
        name="gpdk045_moscap_mc_validation",
        device_file="tools/spice-libraries/private-models/cadence45/spectre/gpdk045_moscap.scs",
        device_name="gpdk045_nmoscap1v",
        device_class="capacitor",
        source_format="spectre",
        target_format="ngspice",
        device_params={'area': 10e-6, 'perim': 20e-6},
        monte_carlo_runs=100  # Light MC for regression
    )
]


# ============================================================================
# MOS TESTS
# ============================================================================

MOS_TESTS = [
    RegressionTestCase(
        name="gpdk090_nmos_dc_sweep",
        device_file="tools/spice-libraries/private-models/cadence90/spectre/gpdk090_mos.scs",
        device_name="gpdk090_nmos1v_x",
        device_class="mos",
        source_format="spectre",
        target_format="ngspice",
        device_params={'width': 1e-6, 'length': 90e-9},
        expected_metrics={'Vth': 0.4, 'Id_sat': 1e-4}
    ),
    RegressionTestCase(
        name="gpdk090_pmos_dc_sweep",
        device_file="tools/spice-libraries/private-models/cadence90/spectre/gpdk090_mos.scs",
        device_name="gpdk090_pmos1v_x",
        device_class="mos",
        source_format="spectre",
        target_format="ngspice",
        device_params={'width': 1e-6, 'length': 90e-9},
        expected_metrics={'Vth': -0.4, 'Id_sat': -5e-5}
    )
]


# ============================================================================
# DIODE TESTS
# ============================================================================

DIODE_TESTS = [
    RegressionTestCase(
        name="gpdk090_diode_iv",
        device_file="tools/spice-libraries/private-models/cadence90/spectre/gpdk090_diode.scs",
        device_name="gpdk090_ndio_D",
        device_class="diode",
        source_format="spectre",
        target_format="ngspice",
        device_params={},
        expected_metrics={'Id_07': 1e-3}
    ),
    RegressionTestCase(
        name="gpdk045_diode_iv",
        device_file="tools/spice-libraries/private-models/cadence45/spectre/gpdk045_diode.scs",
        device_name="g45nd1svt",
        device_class="diode",
        source_format="spectre",
        target_format="ngspice",
        device_params={}
    )
]


# ============================================================================
# BJT TESTS
# ============================================================================

BJT_TESTS = [
    RegressionTestCase(
        name="gpdk045_bjt_dc",
        device_file="tools/spice-libraries/private-models/cadence45/spectre/gpdk045_bipolar.scs",
        device_name="g45vpnp2",
        device_class="bjt",
        source_format="spectre",
        target_format="ngspice",
        device_params={},
        expected_metrics={'Ic_07': 1e-3, 'beta_max': 100}
    )
]


# ============================================================================
# FULL REGRESSION SUITE
# ============================================================================

FULL_REGRESSION_SUITE = CAP_TESTS + MOS_TESTS + DIODE_TESTS + BJT_TESTS


# Critical tests that MUST pass (for CI gate)
CRITICAL_TESTS = [
    "gpdk090_mimcap_spectre_to_ngspice",
    "gpdk090_nmos_dc_sweep",
    "gpdk090_diode_iv"
]


def get_regression_suite(
    device_class: Optional[str] = None,
    critical_only: bool = False
) -> List[RegressionTestCase]:
    """
    Get regression test suite
    
    Args:
        device_class: Filter by device class ('capacitor', 'mos', etc.)
        critical_only: Only return critical tests
    
    Returns:
        List of test cases
    """
    tests = FULL_REGRESSION_SUITE
    
    if device_class:
        tests = [t for t in tests if t.device_class == device_class]
    
    if critical_only:
        tests = [t for t in tests if t.name in CRITICAL_TESTS]
    
    return tests

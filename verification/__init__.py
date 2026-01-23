"""
Verification Framework for SPICE Translator

This module provides automated verification of translation correctness through:
- Automatic testbench generation
- Simulation execution
- Metrics extraction
- Numerical comparison with tolerances
- Pass/fail certification

Architecture mirrors compiler verification:
  translate → generate testbench → simulate → extract metrics → compare → report
"""

from .testbench_generator import TestbenchGenerator, DeviceClass
from .metrics_extractor import MetricsExtractor, extract_capacitance, extract_mos_metrics
from .comparators import Comparator, TOLERANCES, ComparisonResult
from .verifier import Verifier, VerificationError, VerificationReport

__all__ = [
    'TestbenchGenerator',
    'DeviceClass',
    'MetricsExtractor',
    'extract_capacitance',
    'extract_mos_metrics',
    'Comparator',
    'TOLERANCES',
    'ComparisonResult',
    'Verifier',
    'VerificationError',
    'VerificationReport'
]

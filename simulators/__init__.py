"""
Simulators Package

Unified interface for running SPICE simulations (ngspice, HSPICE, Spectre).
"""

from .run_simulator import (
    run_ngspice,
    run_hspice,
    run_spectre,
    run_simulation,
    SimulationResult,
    SimulatorError
)

__all__ = [
    'run_ngspice',
    'run_hspice',
    'run_spectre',
    'run_simulation',
    'SimulationResult',
    'SimulatorError'
]

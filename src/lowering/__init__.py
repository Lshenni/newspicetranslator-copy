"""
Lowering passes for SPICE translation.

Converts high-level physics models to simulator-specific primitives.
"""

from .capacitor_lowering import CapacitorLowering
from .backend_capabilities import BackendCapabilities

__all__ = ['CapacitorLowering', 'BackendCapabilities']

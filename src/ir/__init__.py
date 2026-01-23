"""
Intermediate Representation (IR) module for SPICE model translation.

This module provides the core IR data structures and serialization
utilities for the translator framework.

Compliance: CONSTRAINTS.md
"""

from .model_ir import (
    ModelIR,
    Condition,
    ModelVariation,
    Corner,
    Temperature,
    DeviceType,
)
from .ir_serializer import IRSerializer

__all__ = [
    "ModelIR",
    "Condition",
    "ModelVariation",
    "Corner",
    "Temperature",
    "DeviceType",
    "IRSerializer",
]

"""
Parameter mapping system initialization.

Exports main classes for SPICE parameter mapping.
"""

from .parameter_mapper import ParameterMapper, DeviceCategory, Confidence, MappingResult
from .alias_resolver import AliasResolver, AliasMatch, build_resolver_from_mapper_data

__all__ = [
    'ParameterMapper',
    'DeviceCategory',
    'Confidence',
    'MappingResult',
    'AliasResolver',
    'AliasMatch',
    'build_resolver_from_mapper_data',
]

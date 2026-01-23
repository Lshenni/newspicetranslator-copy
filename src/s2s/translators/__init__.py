"""
SPICE model format translation package.

This package provides translators for converting between different SPICE formats:
- Spectre (.scs)
- HSPICE (.sp)
- ngspice (.lib)
"""

from .types import (
    Format,
    ConfidenceLevel,
    ParameterMapping,
    TranslationResult,
    TranslationError,
    ParameterNotFoundError,
    InvalidFormatError,
    ConfidenceThresholdError
)
from .base_translator import BaseTranslator
from .parameter_mappings import (
    PARAMETER_MAPPINGS,
    get_parameter_mapping,
    get_all_mappings_for_formats,
    get_confidence_stats,
    validate_mapping_completeness
)
from .translator_factory import (
    TranslatorFactory,
    create_translator,
    list_supported_translations,
    get_translation_info
)
from .spectre_to_hspice_translator import SpectreToHSPICETranslator
from .spectre_to_ngspice_translator import SpectreToNgspiceTranslator
from .hspice_to_spectre_translator import HSPICEToSpectreTranslator
from .ngspice_to_hspice_translator import NgspiceToHSPICETranslator
try:
    from .validation_engine import ValidationEngine, ValidationResult
except ImportError:
    # Validation engine is optional
    ValidationEngine = None
    ValidationResult = None

__all__ = [
    # Base classes
    'BaseTranslator',
    'Format',
    'ConfidenceLevel',
    'ParameterMapping',
    'TranslationResult',

    # Exceptions
    'TranslationError',
    'ParameterNotFoundError',
    'InvalidFormatError',
    'ConfidenceThresholdError',

    # Parameter mappings
    'PARAMETER_MAPPINGS',
    'get_parameter_mapping',
    'get_all_mappings_for_formats',
    'get_confidence_stats',
    'validate_mapping_completeness',

    # Factory and utilities
    'TranslatorFactory',
    'create_translator',
    'list_supported_translations',
    'get_translation_info',

    # Specific translators
    'SpectreToHSPICETranslator',
    'SpectreToNgspiceTranslator',
    'HSPICEToSpectreTranslator',
    'NgspiceToHSPICETranslator',

    # Validation
    'ValidationEngine',
    'ValidationResult'
]
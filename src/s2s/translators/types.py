"""
Shared types for SPICE translator modules.

This module contains type definitions that are shared between translators and config modules
to avoid circular import issues.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union, Callable, Set


class Format(Enum):
    """Supported SPICE format types."""
    SPECTRE = "spectre"
    HSPICE = "hspice"
    NGSPICE = "ngspice"


class ConfidenceLevel(Enum):
    """Confidence levels for parameter mappings."""
    HIGH = "high"      # >95% confidence
    MEDIUM = "medium"  # 80-95% confidence
    LOW = "low"        # 60-80% confidence
    UNKNOWN = "unknown"  # <60% confidence


@dataclass
class ParameterMapping:
    """Represents a parameter mapping between formats."""
    source_name: str
    target_name: str
    confidence: ConfidenceLevel
    transformation: Optional[str] = None  # Mathematical transformation if needed
    unit_conversion: Optional[str] = None  # Unit conversion factor
    dependencies: Optional[List[str]] = None  # Other parameters this depends on
    notes: Optional[str] = None  # Additional notes about the mapping

    def __post_init__(self) -> None:
        """Validate the parameter mapping."""
        if not self.source_name or not self.target_name:
            raise ValueError("Source and target parameter names are required")


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    source_format: Format
    target_format: Format
    source_file: str  # Changed from Path to str to avoid import issues
    target_file: str  # Changed from Path to str to avoid import issues
    parameters_mapped: int
    parameters_unmapped: int
    confidence_score: float  # Average confidence score (0.0-1.0)
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of parameter mapping."""
        total_params = self.parameters_mapped + self.parameters_unmapped
        return self.parameters_mapped / total_params if total_params > 0 else 0.0


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class ParameterNotFoundError(TranslationError):
    """Raised when a required parameter is not found."""
    pass


class InvalidFormatError(TranslationError):
    """Raised when an invalid format is specified."""
    pass


class ConfidenceThresholdError(TranslationError):
    """Raised when confidence threshold is not met."""
    pass


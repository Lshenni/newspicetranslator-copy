"""
IR Validator - Validates Intermediate Representation structure integrity.

Ensures ModelIR objects have valid structure, required fields, and consistent data.

Compliance: CONSTRAINTS.md
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from ..ir.model_ir import ModelIR, DeviceType, Corner, Temperature, Condition

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Critical issue, translation will fail
    WARNING = "warning"  # Non-critical issue, translation may succeed
    INFO = "info"        # Informational message


@dataclass
class IRValidationError:
    """
    Represents a validation issue found in IR.
    
    Attributes:
        severity: Error severity level
        message: Human-readable error description
        field: Field name where error occurred (if applicable)
        model_name: Name of model with error (if applicable)
        suggestion: Suggested fix (if applicable)
    """
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    model_name: Optional[str] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """Format error for display."""
        parts = [f"[{self.severity.value.upper()}]"]
        if self.model_name:
            parts.append(f"Model '{self.model_name}'")
        if self.field:
            parts.append(f"field '{self.field}'")
        parts.append(f"- {self.message}")
        if self.suggestion:
            parts.append(f"(Suggestion: {self.suggestion})")
        return " ".join(parts)


@dataclass
class IRValidationResult:
    """
    Result of IR validation.
    
    Attributes:
        valid: True if no errors found
        errors: List of validation errors
        warnings: List of validation warnings
        info: List of informational messages
    """
    valid: bool
    errors: List[IRValidationError]
    warnings: List[IRValidationError]
    info: List[IRValidationError]
    
    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len(self.warnings)
    
    @property
    def total_issues(self) -> int:
        """Total number of issues (errors + warnings)."""
        return self.error_count + self.warning_count
    
    def __str__(self) -> str:
        """Format validation result."""
        if self.valid:
            return f"✓ Validation passed ({self.warning_count} warnings, {len(self.info)} info)"
        return f"✗ Validation failed ({self.error_count} errors, {self.warning_count} warnings)"


class IRValidator:
    """
    Validates ModelIR structure integrity.
    
    Checks:
    - Required fields are present
    - Field values are valid
    - Parameter types are correct
    - Variations are consistent with conditions
    - No duplicate conditions
    """
    
    def __init__(self, strict: bool = False) -> None:
        """
        Initialize validator.
        
        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
        self.errors: List[IRValidationError] = []
        self.warnings: List[IRValidationError] = []
        self.info: List[IRValidationError] = []
    
    def validate(self, models: List[ModelIR]) -> IRValidationResult:
        """
        Validate a list of ModelIR objects.
        
        Args:
            models: List of ModelIR objects to validate
            
        Returns:
            Validation result with errors/warnings
        """
        self.errors = []
        self.warnings = []
        self.info = []
        
        # Check if list is empty
        if not models:
            self.warnings.append(IRValidationError(
                severity=ValidationSeverity.WARNING,
                message="Empty model list",
                suggestion="Ensure parser produced models"
            ))
        
        # Validate each model
        for model in models:
            self._validate_model(model)
        
        # Determine if valid (no errors, or no errors/warnings in strict mode)
        if self.strict:
            valid = len(self.errors) == 0 and len(self.warnings) == 0
        else:
            valid = len(self.errors) == 0
        
        return IRValidationResult(
            valid=valid,
            errors=self.errors,
            warnings=self.warnings,
            info=self.info
        )
    
    def _validate_model(self, model: ModelIR) -> None:
        """Validate a single ModelIR object."""
        # Check required fields
        self._check_required_fields(model)
        
        # Check field types and values
        self._check_field_types(model)
        
        # Check parameters
        self._check_parameters(model)
        
        # Check variations
        self._check_variations(model)
        
        # Check metadata
        self._check_metadata(model)
    
    def _check_required_fields(self, model: ModelIR) -> None:
        """Check that required fields are present and non-empty."""
        # Name is required
        if not model.name or not model.name.strip():
            self.errors.append(IRValidationError(
                severity=ValidationSeverity.ERROR,
                message="Model name is required and cannot be empty",
                field="name",
                model_name=str(model.name) if model.name else "<unnamed>"
            ))
        
        # Model type is required
        if not model.model_type or not model.model_type.strip():
            self.errors.append(IRValidationError(
                severity=ValidationSeverity.ERROR,
                message="Model type is required",
                field="model_type",
                model_name=model.name,
                suggestion="Set to device model type (e.g., 'bsim4', 'bsim3')"
            ))
        
        # Device type is required
        if model.device_type == DeviceType.UNKNOWN:
            self.warnings.append(IRValidationError(
                severity=ValidationSeverity.WARNING,
                message="Device type is UNKNOWN",
                field="device_type",
                model_name=model.name,
                suggestion="Set to specific device type (NMOS, PMOS, etc.)"
            ))
    
    def _check_field_types(self, model: ModelIR) -> None:
        """Check field types are correct."""
        # Check name is string
        if not isinstance(model.name, str):
            self.errors.append(IRValidationError(
                severity=ValidationSeverity.ERROR,
                message=f"Name must be string, got {type(model.name).__name__}",
                field="name",
                model_name=str(model.name)
            ))
        
        # Check model_type is string
        if not isinstance(model.model_type, str):
            self.errors.append(IRValidationError(
                severity=ValidationSeverity.ERROR,
                message=f"Model type must be string, got {type(model.model_type).__name__}",
                field="model_type",
                model_name=model.name
            ))
        
        # Check device_type is DeviceType enum
        if not isinstance(model.device_type, DeviceType):
            self.errors.append(IRValidationError(
                severity=ValidationSeverity.ERROR,
                message=f"Device type must be DeviceType enum, got {type(model.device_type).__name__}",
                field="device_type",
                model_name=model.name
            ))
    
    def _check_parameters(self, model: ModelIR) -> None:
        """Check base parameters are valid."""
        if not isinstance(model.base_parameters, dict):
            self.errors.append(IRValidationError(
                severity=ValidationSeverity.ERROR,
                message=f"Base parameters must be dict, got {type(model.base_parameters).__name__}",
                field="base_parameters",
                model_name=model.name
            ))
            return
        
        # Check for empty parameters
        if not model.base_parameters:
            self.warnings.append(IRValidationError(
                severity=ValidationSeverity.WARNING,
                message="Model has no base parameters",
                field="base_parameters",
                model_name=model.name
            ))
        
        # Check parameter names and values
        for param_name, param_value in model.base_parameters.items():
            # Parameter names should be strings
            if not isinstance(param_name, str):
                self.errors.append(IRValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Parameter name must be string, got {type(param_name).__name__}",
                    field="base_parameters",
                    model_name=model.name
                ))
            
            # Parameter names should not be empty
            if isinstance(param_name, str) and not param_name.strip():
                self.errors.append(IRValidationError(
                    severity=ValidationSeverity.ERROR,
                    message="Parameter name cannot be empty",
                    field="base_parameters",
                    model_name=model.name
                ))
            
            # Parameter values should be numeric or string
            if not isinstance(param_value, (int, float, str, bool)):
                self.warnings.append(IRValidationError(
                    severity=ValidationSeverity.WARNING,
                    message=f"Parameter '{param_name}' has unusual type {type(param_value).__name__}",
                    field="base_parameters",
                    model_name=model.name,
                    suggestion="Use int, float, or string values"
                ))
    
    def _check_variations(self, model: ModelIR) -> None:
        """Check variations are consistent with conditions."""
        # Get all conditions
        conditions = model.get_conditions()
        
        # Check for duplicate conditions
        seen_conditions = set()
        for condition in conditions:
            if condition in seen_conditions:
                self.errors.append(IRValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate condition: {condition}",
                    field="variations",
                    model_name=model.name,
                    suggestion="Remove duplicate condition"
                ))
            seen_conditions.add(condition)
        
        # Check each variation
        for condition in conditions:
            variation = model.get_variation(condition)
            
            if variation is None:
                self.warnings.append(IRValidationError(
                    severity=ValidationSeverity.WARNING,
                    message=f"Condition {condition} has no variation data",
                    field="variations",
                    model_name=model.name
                ))
                continue
            
            # Check variation parameters
            if not isinstance(variation.parameters, dict):
                self.errors.append(IRValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Variation parameters must be dict for condition {condition}",
                    field="variations",
                    model_name=model.name
                ))
                continue
            
            # Check that variation parameters are subset of base parameters
            for param_name in variation.parameters:
                if param_name not in model.base_parameters:
                    self.warnings.append(IRValidationError(
                        severity=ValidationSeverity.WARNING,
                        message=f"Variation parameter '{param_name}' not in base parameters (condition: {condition})",
                        field="variations",
                        model_name=model.name,
                        suggestion="Add to base_parameters or remove from variation"
                    ))
    
    def _check_metadata(self, model: ModelIR) -> None:
        """Check metadata fields."""
        # Check metadata dict
        if not isinstance(model.metadata, dict):
            self.warnings.append(IRValidationError(
                severity=ValidationSeverity.WARNING,
                message=f"Metadata should be dict, got {type(model.metadata).__name__}",
                field="metadata",
                model_name=model.name
            ))
        
        # Info message about metadata
        if not model.metadata:
            self.info.append(IRValidationError(
                severity=ValidationSeverity.INFO,
                message="No metadata present",
                field="metadata",
                model_name=model.name
            ))

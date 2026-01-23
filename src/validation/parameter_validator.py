"""
Parameter Validator - Validates parameter mapping accuracy and electrical equivalence.

Ensures that parameter translations maintain electrical equivalence and
that all mappings are correct.

Compliance: CONSTRAINTS.md
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set, Tuple
import math
import logging

from ..ir.model_ir import ModelIR, DeviceType

logger = logging.getLogger(__name__)


@dataclass
class ParameterIssue:
    """
    Represents a parameter validation issue.
    
    Attributes:
        severity: Issue severity (error/warning/info)
        parameter: Parameter name
        message: Issue description
        expected: Expected value (if applicable)
        actual: Actual value (if applicable)
        suggestion: Suggested fix
    """
    severity: str  # 'error', 'warning', 'info'
    parameter: str
    message: str
    expected: Optional[float] = None
    actual: Optional[float] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """Format issue for display."""
        parts = [f"[{self.severity.upper()}]"]
        parts.append(f"Parameter '{self.parameter}':")
        parts.append(self.message)
        if self.expected is not None and self.actual is not None:
            parts.append(f"(expected: {self.expected}, actual: {self.actual})")
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return " ".join(parts)


@dataclass
class ParameterValidationResult:
    """
    Result of parameter validation.
    
    Attributes:
        valid: True if no errors found
        errors: List of parameter errors
        warnings: List of parameter warnings
        info: List of informational messages
        tolerance: Tolerance used for comparison
    """
    valid: bool
    errors: List[ParameterIssue]
    warnings: List[ParameterIssue]
    info: List[ParameterIssue]
    tolerance: float
    
    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len(self.warnings)
    
    def __str__(self) -> str:
        """Format validation result."""
        if self.valid:
            return f"✓ Parameters valid ({self.warning_count} warnings, tolerance={self.tolerance})"
        return f"✗ Parameters invalid ({self.error_count} errors, {self.warning_count} warnings)"


class ParameterValidator:
    """
    Validates parameter mapping accuracy.
    
    Checks:
    - Parameter values are within expected ranges
    - Unit conversions are correct
    - Electrical equivalence is maintained
    - Required parameters are present
    - Parameter types match expectations
    """
    
    # Common parameter ranges for MOSFET models (BSIM3/4)
    PARAMETER_RANGES = {
        'vth0': (-5.0, 5.0),        # Threshold voltage (V)
        'tox': (1e-10, 1e-6),       # Oxide thickness (m)
        'u0': (1e-3, 1.0),          # Mobility (m²/V·s)
        'vsat': (1e3, 3e5),         # Saturation velocity (m/s)
        'toxe': (1e-10, 1e-6),      # Effective oxide thickness (m)
        'toxm': (1e-10, 1e-6),      # Gate oxide thickness (m)
        'epsrox': (3.0, 10.0),      # Oxide permittivity
        'wint': (-1e-6, 1e-6),      # Width offset (m)
        'lint': (-1e-6, 1e-6),      # Length offset (m)
        'voff': (-5.0, 5.0),        # Offset voltage (V)
        'nfactor': (0.1, 10.0),     # Subthreshold slope factor
        'cdsc': (-1e-2, 1e-2),      # Drain/Source coupling capacitance (F/m²)
    }
    
    # Required parameters for different model types
    REQUIRED_PARAMETERS = {
        'bsim4': {'version', 'toxe', 'toxm', 'vth0'},
        'bsim3': {'version', 'tox', 'vth0'},
        'bsim_bulk': {'version', 'toxe', 'vth0'},
    }
    
    def __init__(self, tolerance: float = 0.01, strict: bool = False) -> None:
        """
        Initialize validator.
        
        Args:
            tolerance: Relative tolerance for parameter comparison (default 1%)
            strict: If True, treat warnings as errors
        """
        self.tolerance = tolerance
        self.strict = strict
        self.errors: List[ParameterIssue] = []
        self.warnings: List[ParameterIssue] = []
        self.info: List[ParameterIssue] = []
    
    def validate(self, model: ModelIR) -> ParameterValidationResult:
        """
        Validate parameters for a single model.
        
        Args:
            model: ModelIR object to validate
            
        Returns:
            Validation result
        """
        self.errors = []
        self.warnings = []
        self.info = []
        
        # Check required parameters
        self._check_required_parameters(model)
        
        # Check parameter ranges
        self._check_parameter_ranges(model)
        
        # Check parameter types
        self._check_parameter_types(model)
        
        # Check for suspicious values
        self._check_suspicious_values(model)
        
        # Determine validity
        if self.strict:
            valid = len(self.errors) == 0 and len(self.warnings) == 0
        else:
            valid = len(self.errors) == 0
        
        return ParameterValidationResult(
            valid=valid,
            errors=self.errors,
            warnings=self.warnings,
            info=self.info,
            tolerance=self.tolerance
        )
    
    def validate_equivalence(self, source: ModelIR, target: ModelIR, 
                            common_params: Optional[Set[str]] = None) -> ParameterValidationResult:
        """
        Validate electrical equivalence between source and target models.
        
        Args:
            source: Source model
            target: Target model
            common_params: Set of parameters to compare (if None, use intersection)
            
        Returns:
            Validation result
        """
        self.errors = []
        self.warnings = []
        self.info = []
        
        # Determine which parameters to compare
        if common_params is None:
            common_params = set(source.base_parameters.keys()) & set(target.base_parameters.keys())
        
        if not common_params:
            self.warnings.append(ParameterIssue(
                severity='warning',
                parameter='<all>',
                message="No common parameters to compare",
                suggestion="Check that translation produced expected parameters"
            ))
        
        # Compare each common parameter
        for param_name in common_params:
            source_value = source.base_parameters.get(param_name)
            target_value = target.base_parameters.get(param_name)
            
            if source_value is None or target_value is None:
                continue
            
            # Convert to float for comparison
            try:
                source_float = self._to_float(source_value)
                target_float = self._to_float(target_value)
            except (ValueError, TypeError):
                self.warnings.append(ParameterIssue(
                    severity='warning',
                    parameter=param_name,
                    message=f"Cannot compare non-numeric values: {source_value} vs {target_value}"
                ))
                continue
            
            # Check if values match within tolerance
            if not self._values_match(source_float, target_float):
                rel_error = abs(source_float - target_float) / max(abs(source_float), abs(target_float), 1e-20)
                self.warnings.append(ParameterIssue(
                    severity='warning',
                    parameter=param_name,
                    message=f"Values differ beyond tolerance ({rel_error*100:.2f}% error)",
                    expected=source_float,
                    actual=target_float,
                    suggestion=f"Check parameter mapping and unit conversion"
                ))
        
        # Determine validity
        if self.strict:
            valid = len(self.errors) == 0 and len(self.warnings) == 0
        else:
            valid = len(self.errors) == 0
        
        return ParameterValidationResult(
            valid=valid,
            errors=self.errors,
            warnings=self.warnings,
            info=self.info,
            tolerance=self.tolerance
        )
    
    def _check_required_parameters(self, model: ModelIR) -> None:
        """Check that required parameters are present."""
        model_type_lower = model.model_type.lower()
        
        # Find matching required parameter set
        required_set = None
        for key, params in self.REQUIRED_PARAMETERS.items():
            if key in model_type_lower:
                required_set = params
                break
        
        if required_set is None:
            self.info.append(ParameterIssue(
                severity='info',
                parameter='<model_type>',
                message=f"No required parameter set defined for model type '{model.model_type}'"
            ))
            return
        
        # Check each required parameter
        for param in required_set:
            if param not in model.base_parameters:
                self.errors.append(ParameterIssue(
                    severity='error',
                    parameter=param,
                    message=f"Required parameter missing for {model.model_type}",
                    suggestion=f"Add {param} to base_parameters"
                ))
    
    def _check_parameter_ranges(self, model: ModelIR) -> None:
        """Check that parameters are within expected ranges."""
        for param_name, param_value in model.base_parameters.items():
            # Skip if no range defined
            if param_name.lower() not in self.PARAMETER_RANGES:
                continue
            
            # Get expected range
            min_val, max_val = self.PARAMETER_RANGES[param_name.lower()]
            
            # Convert to float
            try:
                value_float = self._to_float(param_value)
            except (ValueError, TypeError):
                continue
            
            # Check range
            if value_float < min_val or value_float > max_val:
                self.warnings.append(ParameterIssue(
                    severity='warning',
                    parameter=param_name,
                    message=f"Value {value_float} outside typical range [{min_val}, {max_val}]",
                    suggestion="Verify parameter value and units"
                ))
    
    def _check_parameter_types(self, model: ModelIR) -> None:
        """Check that parameter values have expected types."""
        for param_name, param_value in model.base_parameters.items():
            # Check for None
            if param_value is None:
                self.warnings.append(ParameterIssue(
                    severity='warning',
                    parameter=param_name,
                    message="Parameter value is None",
                    suggestion="Set to appropriate value or remove parameter"
                ))
            
            # Check for non-numeric, non-string types
            elif not isinstance(param_value, (int, float, str, bool)):
                self.errors.append(ParameterIssue(
                    severity='error',
                    parameter=param_name,
                    message=f"Unexpected type: {type(param_value).__name__}",
                    suggestion="Use int, float, or string"
                ))
    
    def _check_suspicious_values(self, model: ModelIR) -> None:
        """Check for suspicious parameter values."""
        for param_name, param_value in model.base_parameters.items():
            try:
                value_float = self._to_float(param_value)
            except (ValueError, TypeError):
                continue
            
            # Check for zero (often suspicious)
            if value_float == 0.0 and param_name.lower() not in ['voff', 'wint', 'lint']:
                self.info.append(ParameterIssue(
                    severity='info',
                    parameter=param_name,
                    message="Parameter is zero (may be intentional)",
                    suggestion="Verify this is correct"
                ))
            
            # Check for very large values
            if abs(value_float) > 1e10:
                self.warnings.append(ParameterIssue(
                    severity='warning',
                    parameter=param_name,
                    message=f"Very large value: {value_float}",
                    suggestion="Check units and scaling"
                ))
            
            # Check for very small non-zero values
            if 0 < abs(value_float) < 1e-20:
                self.warnings.append(ParameterIssue(
                    severity='warning',
                    parameter=param_name,
                    message=f"Very small value: {value_float}",
                    suggestion="Check units and scaling"
                ))
            
            # Check for NaN or Inf
            if math.isnan(value_float) or math.isinf(value_float):
                self.errors.append(ParameterIssue(
                    severity='error',
                    parameter=param_name,
                    message=f"Invalid value: {value_float}",
                    suggestion="Use finite numeric value"
                ))
    
    def _to_float(self, value) -> float:
        """
        Convert parameter value to float.
        
        Args:
            value: Parameter value
            
        Returns:
            Float value
            
        Raises:
            ValueError: If cannot convert to float
        """
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Handle scientific notation and engineering suffixes
            value_lower = value.lower().strip()
            
            # Handle engineering suffixes (k, m, u, n, p, f)
            multipliers = {
                'k': 1e3,
                'm': 1e-3,
                'u': 1e-6,
                'n': 1e-9,
                'p': 1e-12,
                'f': 1e-15,
            }
            
            for suffix, mult in multipliers.items():
                if value_lower.endswith(suffix):
                    return float(value_lower[:-1]) * mult
            
            # Try direct conversion
            return float(value)
        
        raise ValueError(f"Cannot convert {type(value).__name__} to float")
    
    def _values_match(self, val1: float, val2: float) -> bool:
        """
        Check if two values match within tolerance.
        
        Args:
            val1: First value
            val2: Second value
            
        Returns:
            True if values match within relative tolerance
        """
        # Handle exact match
        if val1 == val2:
            return True
        
        # Handle zero comparison
        if val1 == 0 or val2 == 0:
            return abs(val1 - val2) < self.tolerance
        
        # Relative error
        rel_error = abs(val1 - val2) / max(abs(val1), abs(val2))
        return rel_error <= self.tolerance

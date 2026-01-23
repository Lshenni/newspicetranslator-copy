"""
Tests for ParameterValidator.

Compliance: CONSTRAINTS.md
"""

import pytest
import math
from src.validation.parameter_validator import (
    ParameterValidator,
    ParameterValidationResult,
    ParameterIssue
)
from src.ir.model_ir import ModelIR, DeviceType


class TestParameterValidator:
    """Test suite for ParameterValidator."""
    
    def test_valid_parameters(self):
        """Test validation of valid parameters."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "toxm": 2.5e-9,
                "vth0": 0.45,
                "u0": 0.03
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert result.valid
        assert result.error_count == 0
    
    def test_missing_required_parameters(self):
        """Test detection of missing required parameters."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                # Missing required: version, toxe, toxm, vth0
                "u0": 0.03
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_parameter_out_of_range(self):
        """Test detection of parameters out of range."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 10.0,  # Out of range (-5.0, 5.0)
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert result.warning_count >= 1
    
    def test_none_parameter_value(self):
        """Test detection of None parameter values."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": None
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert result.warning_count >= 1
    
    def test_invalid_parameter_type(self):
        """Test detection of invalid parameter types."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": ["invalid", "list"]
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_zero_parameter_value(self):
        """Test detection of suspicious zero values."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 0.0,  # Suspicious
                "wint": 0.0,  # OK for wint
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        # Should have info message about vth0=0
        assert len(result.info) >= 1
    
    def test_very_large_value(self):
        """Test detection of very large values."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 1e15  # Very large
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert result.warning_count >= 1
    
    def test_very_small_value(self):
        """Test detection of very small values."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 1e-25  # Very small
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert result.warning_count >= 1
    
    def test_nan_value(self):
        """Test detection of NaN values."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": float('nan')
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_inf_value(self):
        """Test detection of infinity values."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": float('inf')
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_equivalence_matching_values(self):
        """Test equivalence validation with matching values."""
        source = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45, "u0": 0.03}
        )
        
        target = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45, "u0": 0.03}
        )
        
        validator = ParameterValidator(tolerance=0.01)
        result = validator.validate_equivalence(source, target)
        
        assert result.valid
        assert result.warning_count == 0
    
    def test_equivalence_within_tolerance(self):
        """Test equivalence with values within tolerance."""
        source = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )
        
        target = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.4505}  # 0.11% difference
        )
        
        validator = ParameterValidator(tolerance=0.01)  # 1% tolerance
        result = validator.validate_equivalence(source, target)
        
        assert result.valid
    
    def test_equivalence_beyond_tolerance(self):
        """Test equivalence with values beyond tolerance."""
        source = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )
        
        target = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.50}  # 11% difference
        )
        
        validator = ParameterValidator(tolerance=0.01)
        result = validator.validate_equivalence(source, target)
        
        assert result.warning_count >= 1
    
    def test_equivalence_no_common_parameters(self):
        """Test equivalence with no common parameters."""
        source = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )
        
        target = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"u0": 0.03}
        )
        
        validator = ParameterValidator()
        result = validator.validate_equivalence(source, target)
        
        assert result.warning_count >= 1
    
    def test_string_to_float_conversion(self):
        """Test conversion of string values to float."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": "2.5e-9",
                "toxm": "2.5e-9",
                "vth0": "0.45",
                "u0": "30m",  # Engineering suffix
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        # Should handle string conversion
        assert result.valid or result.error_count == 0
    
    def test_engineering_suffix_conversion(self):
        """Test conversion of engineering suffixes."""
        validator = ParameterValidator()
        
        # Test various suffixes
        assert validator._to_float("1k") == 1000.0
        assert validator._to_float("1m") == 0.001
        assert validator._to_float("1u") == 1e-6
        assert validator._to_float("1n") == 1e-9
        assert validator._to_float("1p") == 1e-12
        assert validator._to_float("1f") == 1e-15
    
    def test_strict_mode(self):
        """Test strict mode treats warnings as errors."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "toxm": 2.5e-9,
                "vth0": 10.0  # Out of range - warning
            }
        )
        
        # Non-strict - warnings don't fail
        validator = ParameterValidator(strict=False)
        result = validator.validate(model)
        assert result.valid
        assert result.warning_count >= 1  # Out of range warning
        
        # Strict - warnings fail
        validator = ParameterValidator(strict=True)
        result = validator.validate(model)
        assert not result.valid


# Run tests 10 times for stability
@pytest.mark.parametrize("iteration", range(10))
class TestParameterValidatorStability:
    """Test validator stability across multiple runs."""
    
    def test_consistent_validation(self, iteration):
        """Test that validation is consistent across runs."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "toxm": 2.5e-9,
                "vth0": 0.45
            }
        )
        
        validator = ParameterValidator()
        result = validator.validate(model)
        
        assert result.valid
        assert result.error_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

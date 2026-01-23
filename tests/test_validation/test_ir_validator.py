"""
Tests for IRValidator.

Compliance: CONSTRAINTS.md
"""

import pytest
from src.validation.ir_validator import (
    IRValidator,
    IRValidationResult,
    IRValidationError,
    ValidationSeverity
)
from src.ir.model_ir import ModelIR, DeviceType, Corner, Temperature, Condition


class TestIRValidator:
    """Test suite for IRValidator."""
    
    def test_valid_model(self):
        """Test validation of a valid model."""
        model = ModelIR(
            name="nmos_test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "toxm": 2.5e-9,
                "vth0": 0.45
            }
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert result.valid
        assert result.error_count == 0
    
    def test_empty_model_list(self):
        """Test validation of empty model list."""
        validator = IRValidator()
        result = validator.validate([])
        
        assert result.valid  # No errors, just warning
        assert result.warning_count == 1
    
    def test_missing_name(self):
        """Test detection of missing model name."""
        model = ModelIR(
            name="",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert not result.valid
        assert result.error_count >= 1
        assert any("name" in str(err).lower() for err in result.errors)
    
    def test_missing_model_type(self):
        """Test detection of missing model type."""
        model = ModelIR(
            name="test",
            model_type="",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_unknown_device_type(self):
        """Test detection of unknown device type."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.UNKNOWN,
            base_parameters={"vth0": 0.45}
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert result.warning_count >= 1
    
    def test_empty_parameters(self):
        """Test detection of empty parameters."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={}
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert result.warning_count >= 1
    
    def test_invalid_parameter_name(self):
        """Test detection of invalid parameter names."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "": 0.45,  # Empty parameter name
                "vth0": 0.45
            }
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_duplicate_conditions(self):
        """Test detection of duplicate conditions."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )
        
        # Add same condition twice
        condition = Condition(corner=Corner.TT, temperature=Temperature.NOMINAL)
        model.add_variation(condition, {"vth0": 0.50})
        model.add_variation(condition, {"vth0": 0.48})  # Duplicate
        
        validator = IRValidator()
        result = validator.validate([model])
        
        # Should detect duplicate
        assert result.error_count >= 1
    
    def test_variation_parameter_not_in_base(self):
        """Test detection of variation parameters not in base."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )
        
        condition = Condition(corner=Corner.FF, temperature=Temperature.HOT)
        model.add_variation(condition, {"u0": 0.03})  # u0 not in base
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert result.warning_count >= 1
    
    def test_strict_mode(self):
        """Test strict mode treats warnings as errors."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.UNKNOWN,  # Causes warning
            base_parameters={"vth0": 0.45}
        )
        
        # Non-strict mode
        validator = IRValidator(strict=False)
        result = validator.validate([model])
        assert result.valid  # Warnings don't fail validation
        
        # Strict mode
        validator = IRValidator(strict=True)
        result = validator.validate([model])
        assert not result.valid  # Warnings fail validation
    
    def test_multiple_models(self):
        """Test validation of multiple models."""
        models = [
            ModelIR(
                name=f"model_{i}",
                model_type="bsim4",
                device_type=DeviceType.NMOS,
                base_parameters={"vth0": 0.45}
            )
            for i in range(5)
        ]
        
        validator = IRValidator()
        result = validator.validate(models)
        
        assert result.valid
    
    def test_invalid_parameter_type(self):
        """Test detection of invalid parameter types."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": ["invalid", "list"]  # Invalid type
            }
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert result.warning_count >= 1


# Run tests 10 times for stability (Tier methodology)
@pytest.mark.parametrize("iteration", range(10))
class TestIRValidatorStability:
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
                "vth0": 0.45
            }
        )
        
        validator = IRValidator()
        result = validator.validate([model])
        
        assert result.valid
        assert result.error_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

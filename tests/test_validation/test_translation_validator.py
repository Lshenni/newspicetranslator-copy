"""
Tests for TranslationValidator.

Compliance: CONSTRAINTS.md
"""

import pytest
from pathlib import Path
from src.validation.translation_validator import (
    TranslationValidator,
    TranslationValidationResult,
    RoundTripResult
)
from src.ir.model_ir import ModelIR, DeviceType


class TestTranslationValidator:
    """Test suite for TranslationValidator."""
    
    def test_valid_translation(self):
        """Test validation of a valid translation."""
        source_ir = [ModelIR(
            name="nmos_test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "vth0": 0.45
            }
        )]
        
        target_ir = [ModelIR(
            name="nmos_test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "vth0": 0.45
            }
        )]
        
        target_content = """
* Translated model
.MODEL nmos_test NMOS LEVEL=54 VERSION=4.8.0
+ TOXE=2.5E-9 VTH0=0.45
.END
"""
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        assert result.valid
        assert result.total_errors == 0
    
    def test_ir_validation_failure(self):
        """Test detection of IR validation failures."""
        source_ir = [ModelIR(
            name="",  # Invalid - empty name
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        target_ir = source_ir
        target_content = ".MODEL test NMOS"
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        assert not result.valid
        assert result.ir_validation is not None
        assert result.ir_validation.error_count > 0
    
    def test_syntax_validation_failure(self):
        """Test detection of syntax validation failures."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        target_ir = source_ir
        target_content = "+ TOXE=2.5E-9"  # Invalid - continuation at start
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        assert not result.valid
        assert result.syntax_validation is not None
        assert result.syntax_validation.error_count > 0
    
    def test_parameter_validation_failure(self):
        """Test detection of parameter validation failures."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        target_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.90}  # Very different
        )]
        
        target_content = ".MODEL test NMOS VTH0=0.90"
        
        validator = TranslationValidator(tolerance=0.01)
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        # Parameter validation should show warnings
        assert result.parameter_validation is not None
        assert result.parameter_validation.warning_count > 0
    
    def test_skip_validations(self):
        """Test skipping individual validations."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=".MODEL test NMOS",
            source_format="hspice",
            target_format="hspice",
            validate_ir=False,
            validate_syntax=False,
            validate_parameters=False
        )
        
        assert result.ir_validation is None
        assert result.syntax_validation is None
        assert result.parameter_validation is None
    
    def test_round_trip_success(self):
        """Test successful round-trip validation."""
        source_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45, "toxe": 2.5e-9}
        )]
        
        final_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45, "toxe": 2.5e-9}
        )]
        
        validator = TranslationValidator()
        result = validator.validate_round_trip(source_models, final_models)
        
        assert result.valid
        assert result.error_count == 0
    
    def test_round_trip_model_count_mismatch(self):
        """Test round-trip with model count mismatch."""
        source_models = [ModelIR(
            name="test1",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        final_models = [
            ModelIR(name="test1", model_type="bsim4", device_type=DeviceType.NMOS, base_parameters={"vth0": 0.45}),
            ModelIR(name="test2", model_type="bsim4", device_type=DeviceType.NMOS, base_parameters={"vth0": 0.45})
        ]
        
        validator = TranslationValidator()
        result = validator.validate_round_trip(source_models, final_models)
        
        assert not result.valid
        assert result.error_count > 0
    
    def test_round_trip_name_change(self):
        """Test round-trip with name change."""
        source_models = [ModelIR(
            name="original",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        final_models = [ModelIR(
            name="changed",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        validator = TranslationValidator()
        result = validator.validate_round_trip(source_models, final_models)
        
        # Name change is a warning
        assert result.warning_count > 0
    
    def test_round_trip_device_type_change(self):
        """Test round-trip with device type change."""
        source_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        final_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.PMOS,  # Changed!
            base_parameters={"vth0": 0.45}
        )]
        
        validator = TranslationValidator()
        result = validator.validate_round_trip(source_models, final_models)
        
        assert not result.valid
        assert result.error_count > 0
    
    def test_round_trip_parameter_difference(self):
        """Test round-trip with parameter differences."""
        source_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        final_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.50}  # Different value
        )]
        
        validator = TranslationValidator(tolerance=0.01)
        result = validator.validate_round_trip(source_models, final_models)
        
        # Large parameter difference should be warning
        assert result.warning_count > 0
    
    def test_generate_report(self):
        """Test report generation."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        target_content = ".MODEL test NMOS VTH0=0.45"
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        report = validator.generate_report(result)
        
        assert isinstance(report, str)
        assert len(report) > 0
        assert "VALIDATION REPORT" in report
        assert "hspice" in report.lower()
    
    def test_generate_report_with_file(self, tmp_path):
        """Test report generation with file output."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        target_content = ".MODEL test NMOS VTH0=0.45"
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        output_path = tmp_path / "validation_report.txt"
        report = validator.generate_report(result, output_path)
        
        assert output_path.exists()
        assert output_path.read_text() == report
    
    def test_strict_mode(self):
        """Test strict mode."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.UNKNOWN,  # Causes warning
            base_parameters={"vth0": 0.45}
        )]
        
        target_content = ".MODEL test NMOS VTH0=0.45"
        
        # Non-strict
        validator = TranslationValidator(strict=False)
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        assert result.valid
        
        # Strict
        validator = TranslationValidator(strict=True)
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        assert not result.valid


# Run tests 10 times for stability
@pytest.mark.parametrize("iteration", range(10))
class TestTranslationValidatorStability:
    """Test validator stability across multiple runs."""
    
    def test_consistent_validation(self, iteration):
        """Test that validation is consistent across runs."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "vth0": 0.45
            }
        )]
        
        target_content = ".MODEL test NMOS LEVEL=54"
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        assert result.valid or result.error_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

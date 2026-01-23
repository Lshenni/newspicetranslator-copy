"""
Additional comprehensive tests for TranslationValidator to achieve 90%+ coverage.

Focuses on error paths, report generation, and multi-model scenarios.
"""

import pytest
from pathlib import Path
from src.validation.translation_validator import (
    TranslationValidator,
    TranslationValidationResult,
    RoundTripResult
)
from src.ir.model_ir import ModelIR, DeviceType, Corner, Temperature, Condition


class TestTranslationValidatorComprehensive:
    """Comprehensive test suite targeting uncovered paths."""
    
    def test_get_summary_with_all_errors(self):
        """Test get_summary() with errors in all validation types."""
        # Create a result with errors in all validators
        source_ir = [ModelIR(
            name="",  # Error: empty name
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        target_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.90}  # Different value
        )]
        
        target_content = "+ INVALID"  # Invalid syntax
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        # Get summary - this exercises lines 81-111
        summary = result.get_summary()
        
        assert isinstance(summary, str)
        assert "Translation Validation:" in summary
        assert "✗ FAIL" in summary
        assert len(summary) > 100
    
    def test_get_summary_with_warnings_only(self):
        """Test get_summary() with warnings but no errors."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.UNKNOWN,  # Warning
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "toxm": 2.5e-9,
                "vth0": 0.45
            }
        )]
        
        target_content = ".MODEL test NMOS VTH0=0.45"
        
        validator = TranslationValidator(strict=False)
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        summary = result.get_summary()
        assert "✓ PASS" in summary or "WARNING" in summary.upper()
    
    def test_multiple_models_parameter_validation(self):
        """Test parameter validation with multiple models (line 144-146)."""
        source_ir = [
            ModelIR(
                name="nmos1",
                model_type="bsim4",
                device_type=DeviceType.NMOS,
                base_parameters={"vth0": 0.45, "toxe": 2.5e-9}
            ),
            ModelIR(
                name="nmos2",
                model_type="bsim4",
                device_type=DeviceType.NMOS,
                base_parameters={"vth0": 0.50, "toxe": 2.0e-9}
            ),
            ModelIR(
                name="pmos1",
                model_type="bsim4",
                device_type=DeviceType.PMOS,
                base_parameters={"vth0": -0.45, "toxe": 2.5e-9}
            )
        ]
        
        target_ir = [
            ModelIR(
                name="nmos1",
                model_type="bsim4",
                device_type=DeviceType.NMOS,
                base_parameters={"vth0": 0.46, "toxe": 2.5e-9}  # Slight difference
            ),
            ModelIR(
                name="nmos2",
                model_type="bsim4",
                device_type=DeviceType.NMOS,
                base_parameters={"vth0": 0.55, "toxe": 2.0e-9}  # Larger difference
            ),
            ModelIR(
                name="pmos1",
                model_type="bsim4",
                device_type=DeviceType.PMOS,
                base_parameters={"vth0": -0.45, "toxe": 2.5e-9}  # Match
            )
        ]
        
        target_content = ".MODEL nmos1 NMOS\n.MODEL nmos2 NMOS\n.MODEL pmos1 PMOS"
        
        validator = TranslationValidator(tolerance=0.01)
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice",
            validate_ir=False,
            validate_syntax=False
        )
        
        # This exercises the aggregation logic at lines 237-244
        assert result.parameter_validation is not None
        # Should have warnings from model differences
        assert result.parameter_validation.warning_count >= 1
    
    def test_round_trip_with_model_type_change(self):
        """Test round-trip with model type change (line 295)."""
        source_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        final_models = [ModelIR(
            name="test",
            model_type="bsim3",  # Changed model type
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        validator = TranslationValidator()
        result = validator.validate_round_trip(source_models, final_models)
        
        # Should have warning about model type change
        assert result.warning_count >= 1
        assert any("model type" in str(d).lower() for d in result.differences)
    
    def test_round_trip_with_parameter_differences(self):
        """Test round-trip with parameter differences (lines 237-240)."""
        source_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 0.45,
                "toxe": 2.5e-9,
                "u0": 0.03
            }
        )]
        
        final_models = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 0.50,  # 11% difference
                "toxe": 2.6e-9,  # 4% difference
                "u0": 0.031  # 3% difference
            }
        )]
        
        validator = TranslationValidator(tolerance=0.01)
        result = validator.validate_round_trip(source_models, final_models)
        
        # Should detect parameter differences
        assert len(result.differences) > 0
        assert result.warning_count >= 1
    
    def test_generate_report_with_ir_errors(self):
        """Test report generation with IR validation errors."""
        source_ir = [ModelIR(
            name="",  # Error
            model_type="",  # Error
            device_type=DeviceType.NMOS,
            base_parameters={}  # Warning
        )]
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=".MODEL test NMOS",
            source_format="hspice",
            target_format="hspice",
            validate_syntax=False,
            validate_parameters=False
        )
        
        # Generate report - exercises lines 358-369
        report = validator.generate_report(result)
        
        assert "VALIDATION REPORT" in report
        assert "IR VALIDATION" in report
        assert "Errors:" in report
        assert len(report) > 200
    
    def test_generate_report_with_syntax_errors(self):
        """Test report generation with syntax validation errors."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        # Invalid syntax - continuation at start, missing required fields
        target_content = "+ TOXE=2.5E-9\n.MODEL\n.ENDS"
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice",
            validate_ir=False,
            validate_parameters=False
        )
        
        # Generate report - exercises lines 382-393
        report = validator.generate_report(result)
        
        assert "SYNTAX VALIDATION" in report
        assert "Errors:" in report or "✗" in report
    
    def test_generate_report_with_parameter_errors(self):
        """Test report generation with parameter validation errors."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 0.45,
                "toxe": 2.5e-9
            }
        )]
        
        target_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "vth0": 0.90,  # Very different
                "toxe": 5.0e-9  # Very different
            }
        )]
        
        validator = TranslationValidator(tolerance=0.01)
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=".MODEL test NMOS",
            source_format="hspice",
            target_format="hspice",
            validate_ir=False,
            validate_syntax=False
        )
        
        # Generate report - exercises lines 406-417
        report = validator.generate_report(result)
        
        assert "PARAMETER VALIDATION" in report
    
    def test_generate_report_with_round_trip(self):
        """Test report generation with round-trip validation."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.45}
        )]
        
        validator = TranslationValidator()
        
        # First do regular validation
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=source_ir,
            target_content=".MODEL test NMOS",
            source_format="hspice",
            target_format="hspice"
        )
        
        # Add round-trip validation
        final_models = [ModelIR(
            name="test_changed",  # Name changed
            model_type="bsim4",
            device_type=DeviceType.PMOS,  # Type changed
            base_parameters={"vth0": 0.50}  # Value changed
        )]
        
        result.round_trip_validation = validator.validate_round_trip(
            source_ir, final_models
        )
        
        # Generate report - exercises lines 421-435
        report = validator.generate_report(result)
        
        assert "ROUND-TRIP VALIDATION" in report
        assert "Differences:" in report
    
    def test_generate_report_with_many_warnings(self):
        """Test report generation truncates long warning lists."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                f"param{i}": i * 0.1 for i in range(20)  # 20 parameters
            }
        )]
        
        target_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                f"param{i}": i * 0.15 for i in range(20)  # Different values
            }
        )]
        
        validator = TranslationValidator(tolerance=0.01)
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=".MODEL test NMOS",
            source_format="hspice",
            target_format="hspice",
            validate_ir=False,
            validate_syntax=False
        )
        
        report = validator.generate_report(result)
        
        # Should truncate to 10 warnings
        if result.parameter_validation and result.parameter_validation.warning_count > 10:
            assert "... and" in report
            assert "more" in report
    
    def test_generate_report_with_file_output(self, tmp_path):
        """Test report generation saves to file."""
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
            target_format="hspice"
        )
        
        output_path = tmp_path / "detailed_report.txt"
        report = validator.generate_report(result, output_path)
        
        # File should exist and contain report
        assert output_path.exists()
        file_content = output_path.read_text()
        assert file_content == report
        assert "VALIDATION REPORT" in file_content
    
    def test_round_trip_multiple_models_with_differences(self):
        """Test round-trip with multiple models having various differences."""
        source_models = [
            ModelIR(
                name="nmos",
                model_type="bsim4",
                device_type=DeviceType.NMOS,
                base_parameters={"vth0": 0.45}
            ),
            ModelIR(
                name="pmos",
                model_type="bsim4",
                device_type=DeviceType.PMOS,
                base_parameters={"vth0": -0.45}
            )
        ]
        
        final_models = [
            ModelIR(
                name="nmos_modified",  # Name changed
                model_type="bsim4",
                device_type=DeviceType.NMOS,
                base_parameters={"vth0": 0.48}  # Value changed
            ),
            ModelIR(
                name="pmos",
                model_type="bsim3",  # Model type changed
                device_type=DeviceType.PMOS,
                base_parameters={"vth0": -0.45}
            )
        ]
        
        validator = TranslationValidator(tolerance=0.01)
        result = validator.validate_round_trip(source_models, final_models)
        
        # Should detect multiple differences
        assert len(result.differences) >= 3
        assert result.warning_count >= 1


# Run tests 5 times for stability
@pytest.mark.parametrize("iteration", range(5))
class TestTranslationValidatorStability5x:
    """Test validator stability across 5 runs."""
    
    def test_comprehensive_validation_stability(self, iteration):
        """Test complete validation workflow is stable."""
        source_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "toxm": 2.5e-9,
                "vth0": 0.45
            }
        )]
        
        target_ir = [ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "version": "4.8.0",
                "toxe": 2.5e-9,
                "toxm": 2.5e-9,
                "vth0": 0.45
            }
        )]
        
        target_content = ".MODEL test NMOS LEVEL=54 VERSION=4.8.0"
        
        validator = TranslationValidator()
        result = validator.validate_translation(
            source_ir=source_ir,
            target_ir=target_ir,
            target_content=target_content,
            source_format="hspice",
            target_format="hspice"
        )
        
        assert result.valid
        
        # Generate report
        report = validator.generate_report(result)
        assert "VALIDATION REPORT" in report
        
        # Round-trip
        round_trip = validator.validate_round_trip(source_ir, target_ir)
        assert round_trip.valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

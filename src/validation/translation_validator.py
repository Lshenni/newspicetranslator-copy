"""
Translation Validator - End-to-end validation of translation pipeline.

Validates complete translation workflows including round-trip testing
and cross-validation between different translators.

Compliance: CONSTRAINTS.md
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import logging

from ..ir.model_ir import ModelIR
from .ir_validator import IRValidator, IRValidationResult
from .syntax_validator import SyntaxValidator, SPICEFormat, SyntaxValidationResult
from .parameter_validator import ParameterValidator, ParameterValidationResult

logger = logging.getLogger(__name__)


@dataclass
class TranslationValidationResult:
    """
    Complete translation validation result.
    
    Attributes:
        valid: True if all validations passed
        source_format: Source SPICE format
        target_format: Target SPICE format
        ir_validation: IR validation result
        syntax_validation: Syntax validation result
        parameter_validation: Parameter validation result
        round_trip_validation: Round-trip validation result (if performed)
    """
    valid: bool
    source_format: str
    target_format: str
    ir_validation: Optional[IRValidationResult] = None
    syntax_validation: Optional[SyntaxValidationResult] = None
    parameter_validation: Optional[ParameterValidationResult] = None
    round_trip_validation: Optional['RoundTripResult'] = None
    
    @property
    def total_errors(self) -> int:
        """Total number of errors across all validations."""
        total = 0
        if self.ir_validation:
            total += self.ir_validation.error_count
        if self.syntax_validation:
            total += self.syntax_validation.error_count
        if self.parameter_validation:
            total += self.parameter_validation.error_count
        if self.round_trip_validation:
            total += self.round_trip_validation.error_count
        return total
    
    @property
    def total_warnings(self) -> int:
        """Total number of warnings across all validations."""
        total = 0
        if self.ir_validation:
            total += self.ir_validation.warning_count
        if self.syntax_validation:
            total += self.syntax_validation.warning_count
        if self.parameter_validation:
            total += self.parameter_validation.warning_count
        if self.round_trip_validation:
            total += self.round_trip_validation.warning_count
        return total
    
    def __str__(self) -> str:
        """Format validation result."""
        if self.valid:
            return f"✓ Translation {self.source_format}→{self.target_format} valid ({self.total_warnings} warnings)"
        return f"✗ Translation {self.source_format}→{self.target_format} invalid ({self.total_errors} errors, {self.total_warnings} warnings)"
    
    def get_summary(self) -> str:
        """Get detailed summary of validation results."""
        lines = [
            f"Translation Validation: {self.source_format} → {self.target_format}",
            f"Overall: {'✓ PASS' if self.valid else '✗ FAIL'}",
            ""
        ]
        
        if self.ir_validation:
            lines.append(f"IR Validation: {self.ir_validation}")
            if self.ir_validation.errors:
                lines.append(f"  Errors: {len(self.ir_validation.errors)}")
                for err in self.ir_validation.errors[:3]:  # Show first 3
                    lines.append(f"    - {err}")
        
        if self.syntax_validation:
            lines.append(f"Syntax Validation: {self.syntax_validation}")
            if self.syntax_validation.errors:
                lines.append(f"  Errors: {len(self.syntax_validation.errors)}")
                for err in self.syntax_validation.errors[:3]:
                    lines.append(f"    - {err}")
        
        if self.parameter_validation:
            lines.append(f"Parameter Validation: {self.parameter_validation}")
            if self.parameter_validation.errors:
                lines.append(f"  Errors: {len(self.parameter_validation.errors)}")
                for err in self.parameter_validation.errors[:3]:
                    lines.append(f"    - {err}")
        
        if self.round_trip_validation:
            lines.append(f"Round-Trip Validation: {self.round_trip_validation}")
        
        return "\n".join(lines)


@dataclass
class RoundTripResult:
    """
    Result of round-trip translation validation.
    
    Attributes:
        valid: True if round-trip successful
        source_models: Original models
        final_models: Models after round-trip
        differences: List of detected differences
        error_count: Number of errors
        warning_count: Number of warnings
    """
    valid: bool
    source_models: List[ModelIR]
    final_models: List[ModelIR]
    differences: List[str]
    
    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len([d for d in self.differences if d.startswith('[ERROR]')])
    
    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len([d for d in self.differences if d.startswith('[WARNING]')])
    
    def __str__(self) -> str:
        """Format result."""
        if self.valid:
            return f"✓ Round-trip valid ({len(self.differences)} differences)"
        return f"✗ Round-trip failed ({self.error_count} errors)"


class TranslationValidator:
    """
    End-to-end translation validation.
    
    Validates complete translation workflow:
    1. Source parsing → IR validation
    2. Translation → parameter validation
    3. Output generation → syntax validation
    4. Round-trip testing (optional)
    """
    
    def __init__(self, strict: bool = False, tolerance: float = 0.01) -> None:
        """
        Initialize validator.
        
        Args:
            strict: If True, treat warnings as errors
            tolerance: Tolerance for parameter comparison
        """
        self.strict = strict
        self.tolerance = tolerance
    
    def validate_translation(
        self,
        source_ir: List[ModelIR],
        target_ir: List[ModelIR],
        target_content: str,
        source_format: str,
        target_format: str,
        validate_ir: bool = True,
        validate_syntax: bool = True,
        validate_parameters: bool = True
    ) -> TranslationValidationResult:
        """
        Validate a complete translation.
        
        Args:
            source_ir: Source ModelIR objects
            target_ir: Target ModelIR objects (after translation)
            target_content: Generated target netlist content
            source_format: Source SPICE format
            target_format: Target SPICE format
            validate_ir: Whether to validate IR
            validate_syntax: Whether to validate syntax
            validate_parameters: Whether to validate parameters
            
        Returns:
            Validation result
        """
        result = TranslationValidationResult(
            valid=True,
            source_format=source_format,
            target_format=target_format
        )
        
        # 1. Validate source IR
        if validate_ir:
            ir_validator = IRValidator(strict=self.strict)
            result.ir_validation = ir_validator.validate(source_ir)
            if not result.ir_validation.valid:
                result.valid = False
                logger.warning(f"IR validation failed: {result.ir_validation}")
        
        # 2. Validate target syntax
        if validate_syntax and target_content:
            try:
                spice_format = SPICEFormat(target_format.lower())
                syntax_validator = SyntaxValidator(format=spice_format, strict=self.strict)
                result.syntax_validation = syntax_validator.validate(target_content)
                if not result.syntax_validation.valid:
                    result.valid = False
                    logger.warning(f"Syntax validation failed: {result.syntax_validation}")
            except ValueError:
                logger.warning(f"Unknown SPICE format: {target_format}")
        
        # 3. Validate parameter equivalence
        if validate_parameters and source_ir and target_ir:
            # Compare corresponding models
            param_validator = ParameterValidator(tolerance=self.tolerance, strict=self.strict)
            
            for i, (src_model, tgt_model) in enumerate(zip(source_ir, target_ir)):
                param_result = param_validator.validate_equivalence(src_model, tgt_model)
                
                # Store result from first model (or aggregate if needed)
                if i == 0:
                    result.parameter_validation = param_result
                else:
                    # Aggregate errors/warnings
                    if result.parameter_validation:
                        result.parameter_validation.errors.extend(param_result.errors)
                        result.parameter_validation.warnings.extend(param_result.warnings)
                        result.parameter_validation.info.extend(param_result.info)
                
                if not param_result.valid:
                    result.valid = False
                    logger.warning(f"Parameter validation failed for model {src_model.name}")
        
        return result
    
    def validate_round_trip(
        self,
        source_models: List[ModelIR],
        final_models: List[ModelIR],
        tolerance: float = 0.01
    ) -> RoundTripResult:
        """
        Validate round-trip translation (source → target → source).
        
        Args:
            source_models: Original models
            final_models: Models after round-trip translation
            tolerance: Tolerance for parameter comparison
            
        Returns:
            Round-trip validation result
        """
        differences = []
        
        # Check model count
        if len(source_models) != len(final_models):
            differences.append(
                f"[ERROR] Model count mismatch: {len(source_models)} → {len(final_models)}"
            )
            return RoundTripResult(
                valid=False,
                source_models=source_models,
                final_models=final_models,
                differences=differences
            )
        
        # Compare each model
        for i, (src, final) in enumerate(zip(source_models, final_models)):
            # Check names
            if src.name != final.name:
                differences.append(
                    f"[WARNING] Model {i}: Name changed '{src.name}' → '{final.name}'"
                )
            
            # Check device types
            if src.device_type != final.device_type:
                differences.append(
                    f"[ERROR] Model {src.name}: Device type changed {src.device_type} → {final.device_type}"
                )
            
            # Check model types
            if src.model_type != final.model_type:
                differences.append(
                    f"[WARNING] Model {src.name}: Model type changed '{src.model_type}' → '{final.model_type}'"
                )
            
            # Compare parameters
            param_validator = ParameterValidator(tolerance=tolerance)
            param_result = param_validator.validate_equivalence(src, final)
            
            for error in param_result.errors:
                differences.append(f"[ERROR] Model {src.name}: {error}")
            
            for warning in param_result.warnings:
                differences.append(f"[WARNING] Model {src.name}: {warning}")
        
        # Determine if valid (no errors)
        error_count = len([d for d in differences if d.startswith('[ERROR]')])
        valid = error_count == 0
        
        return RoundTripResult(
            valid=valid,
            source_models=source_models,
            final_models=final_models,
            differences=differences
        )
    
    def generate_report(
        self,
        result: TranslationValidationResult,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate detailed validation report.
        
        Args:
            result: Validation result
            output_path: Optional path to save report
            
        Returns:
            Report content as string
        """
        report_lines = [
            "=" * 80,
            "TRANSLATION VALIDATION REPORT",
            "=" * 80,
            "",
            f"Translation: {result.source_format} → {result.target_format}",
            f"Status: {'✓ PASS' if result.valid else '✗ FAIL'}",
            f"Total Errors: {result.total_errors}",
            f"Total Warnings: {result.total_warnings}",
            "",
            "-" * 80,
        ]
        
        # IR Validation section
        if result.ir_validation:
            report_lines.extend([
                "IR VALIDATION",
                "-" * 80,
                str(result.ir_validation),
                ""
            ])
            
            if result.ir_validation.errors:
                report_lines.append("Errors:")
                for err in result.ir_validation.errors:
                    report_lines.append(f"  - {err}")
                report_lines.append("")
            
            if result.ir_validation.warnings:
                report_lines.append("Warnings:")
                for warn in result.ir_validation.warnings[:10]:  # Limit to 10
                    report_lines.append(f"  - {warn}")
                if len(result.ir_validation.warnings) > 10:
                    report_lines.append(f"  ... and {len(result.ir_validation.warnings) - 10} more")
                report_lines.append("")
        
        # Syntax Validation section
        if result.syntax_validation:
            report_lines.extend([
                "-" * 80,
                "SYNTAX VALIDATION",
                "-" * 80,
                str(result.syntax_validation),
                ""
            ])
            
            if result.syntax_validation.errors:
                report_lines.append("Errors:")
                for err in result.syntax_validation.errors:
                    report_lines.append(f"  - {err}")
                report_lines.append("")
            
            if result.syntax_validation.warnings:
                report_lines.append("Warnings:")
                for warn in result.syntax_validation.warnings[:10]:
                    report_lines.append(f"  - {warn}")
                if len(result.syntax_validation.warnings) > 10:
                    report_lines.append(f"  ... and {len(result.syntax_validation.warnings) - 10} more")
                report_lines.append("")
        
        # Parameter Validation section
        if result.parameter_validation:
            report_lines.extend([
                "-" * 80,
                "PARAMETER VALIDATION",
                "-" * 80,
                str(result.parameter_validation),
                ""
            ])
            
            if result.parameter_validation.errors:
                report_lines.append("Errors:")
                for err in result.parameter_validation.errors:
                    report_lines.append(f"  - {err}")
                report_lines.append("")
            
            if result.parameter_validation.warnings:
                report_lines.append("Warnings:")
                for warn in result.parameter_validation.warnings[:10]:
                    report_lines.append(f"  - {warn}")
                if len(result.parameter_validation.warnings) > 10:
                    report_lines.append(f"  ... and {len(result.parameter_validation.warnings) - 10} more")
                report_lines.append("")
        
        # Round-trip section
        if result.round_trip_validation:
            report_lines.extend([
                "-" * 80,
                "ROUND-TRIP VALIDATION",
                "-" * 80,
                str(result.round_trip_validation),
                ""
            ])
            
            if result.round_trip_validation.differences:
                report_lines.append("Differences:")
                for diff in result.round_trip_validation.differences[:20]:
                    report_lines.append(f"  - {diff}")
                if len(result.round_trip_validation.differences) > 20:
                    report_lines.append(f"  ... and {len(result.round_trip_validation.differences) - 20} more")
                report_lines.append("")
        
        report_lines.extend([
            "=" * 80,
            "END OF REPORT",
            "=" * 80
        ])
        
        report = "\n".join(report_lines)
        
        # Save to file if requested
        if output_path:
            output_path.write_text(report)
            logger.info(f"Validation report saved to {output_path}")
        
        return report

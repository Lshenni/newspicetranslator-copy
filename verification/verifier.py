"""
Verifier - Orchestration Layer

Coordinates the complete verification workflow:
  translate → generate testbench → simulate → extract metrics → compare → report

This is the main entry point for end-to-end verification.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine
from verification.testbench_generator import TestbenchGenerator, DeviceClass, TestbenchConfig
from verification.metrics_extractor import MetricsExtractor, extract_all_metrics
from verification.comparators import Comparator, VerificationResult as ComparisonVerificationResult
from simulators.run_simulator import run_simulation, SimulationResult


class VerificationError(Exception):
    """Raised when verification fails"""
    pass


@dataclass
class VerificationReport:
    """Complete verification report"""
    device_name: str
    device_class: str
    source_format: str
    target_format: str
    translation_success: bool
    reference_sim_success: bool
    target_sim_success: bool
    comparison_result: Optional[ComparisonVerificationResult]
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Human-readable report"""
        lines = [
            "="*70,
            f"VERIFICATION REPORT: {self.device_name}",
            "="*70,
            f"Device Class: {self.device_class}",
            f"Translation: {self.source_format} → {self.target_format}",
            "",
            f"Status: {'✅ PASS' if self.passed else '❌ FAIL'}",
            "",
            f"Translation: {'✅ Success' if self.translation_success else '❌ Failed'}",
            f"Reference Sim ({self.source_format}): {'✅ Success' if self.reference_sim_success else '❌ Failed'}",
            f"Target Sim ({self.target_format}): {'✅ Success' if self.target_sim_success else '❌ Failed'}",
            ""
        ]
        
        if self.comparison_result:
            lines.append(self.comparison_result.summary())
        
        if self.errors:
            lines.append("\n❌ ERRORS:")
            for err in self.errors:
                lines.append(f"   {err}")
        
        if self.warnings:
            lines.append("\n⚠️  WARNINGS:")
            for warn in self.warnings:
                lines.append(f"   {warn}")
        
        return "\n".join(lines)


class Verifier:
    """
    End-to-end verification orchestrator
    
    Usage:
        verifier = Verifier()
        report = verifier.verify(
            device_file='gpdk090_capacitor.scs',
            device_name='mimcap',
            device_class='capacitor',
            source_format='spectre',
            target_format='ngspice'
        )
        
        if not report.passed:
            raise VerificationError(report)
    """
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        strict: bool = False,
        monte_carlo_runs: int = 0
    ):
        """
        Initialize verifier
        
        Args:
            output_dir: Directory for verification outputs
            strict: Use strict tolerances
            monte_carlo_runs: Number of MC runs (0 = disabled)
        """
        self.output_dir = output_dir or (BASE_DIR / 'output' / 'verification')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.strict = strict
        self.monte_carlo_runs = monte_carlo_runs
        
        self.translator = TranslationEngine()
        self.testbench_gen = TestbenchGenerator()
        self.metrics_extractor = MetricsExtractor()
        self.comparator = Comparator(strict=strict)
    
    def verify(
        self,
        device_file: Path,
        device_name: str,
        device_class: str,
        source_format: str,
        target_format: str,
        **device_params
    ) -> VerificationReport:
        """
        Run complete verification workflow
        
        Args:
            device_file: Path to source device library file
            device_name: Model/subcircuit name
            device_class: 'capacitor', 'mos', 'bjt', 'diode', 'resistor'
            source_format: 'spectre', 'hspice', 'ngspice'
            target_format: 'spectre', 'hspice', 'ngspice'
            **device_params: Device-specific params (area, width, length, etc.)
        
        Returns:
            VerificationReport with complete results
        """
        errors = []
        warnings = []
        
        # Step 1: Translate
        translated_file = self.output_dir / f"{device_name}_translated.lib"
        translation_result = self._translate(device_file, translated_file, source_format, target_format)
        
        if not translation_result.get('success', False):
            return VerificationReport(
                device_name=device_name,
                device_class=device_class,
                source_format=source_format,
                target_format=target_format,
                translation_success=False,
                reference_sim_success=False,
                target_sim_success=False,
                comparison_result=None,
                passed=False,
                errors=[f"Translation failed: {translation_result.get('error', 'Unknown')}"]
            )
        
        # Step 2: Generate testbenches
        ref_tb = self._generate_testbench(
            device_name, device_class, source_format, str(device_file), **device_params
        )
        tgt_tb = self._generate_testbench(
            device_name, device_class, target_format, str(translated_file), **device_params
        )
        
        # Step 3: Run reference simulation
        ref_sim_result = run_simulation(ref_tb, source_format, self.output_dir / 'ref')
        
        if not ref_sim_result.success:
            errors.append(f"Reference simulation failed: {ref_sim_result.error_message}")
        
        # Step 4: Run target simulation
        tgt_sim_result = run_simulation(tgt_tb, target_format, self.output_dir / 'tgt')
        
        if not tgt_sim_result.success:
            errors.append(f"Target simulation failed: {tgt_sim_result.error_message}")
        
        # Step 5: Extract metrics
        if ref_sim_result.success and tgt_sim_result.success:
            ref_metrics_result = extract_all_metrics(
                ref_sim_result.output_file, 
                device_class,
                monte_carlo=(self.monte_carlo_runs > 0)
            )
            tgt_metrics_result = extract_all_metrics(
                tgt_sim_result.output_file,
                device_class,
                monte_carlo=(self.monte_carlo_runs > 0)
            )
            
            # Step 6: Compare
            comparison = self.comparator.compare_metrics(
                ref_metrics_result.metrics,
                tgt_metrics_result.metrics,
                device_class,
                device_name
            )
            
            passed = comparison.passed
        else:
            comparison = None
            passed = False
        
        return VerificationReport(
            device_name=device_name,
            device_class=device_class,
            source_format=source_format,
            target_format=target_format,
            translation_success=translation_result.get('success', False),
            reference_sim_success=ref_sim_result.success,
            target_sim_success=tgt_sim_result.success,
            comparison_result=comparison,
            passed=passed and not errors,
            errors=errors,
            warnings=warnings
        )
    
    def _translate(
        self,
        input_file: Path,
        output_file: Path,
        source_format: str,
        target_format: str
    ) -> Dict:
        """Run translation"""
        return self.translator.translate(
            input_file=input_file,
            output_file=output_file,
            source_format=source_format,
            target_format=target_format
        )
    
    def _generate_testbench(
        self,
        device_name: str,
        device_class: str,
        format: str,
        lib_file: str,
        **params
    ) -> str:
        """Generate testbench and inject library path"""
        config = TestbenchConfig(
            device_name=device_name,
            device_class=DeviceClass(device_class),
            format=format,
            monte_carlo_runs=self.monte_carlo_runs,
            **params
        )
        
        testbench = self.testbench_gen.generate(config)
        
        # Replace {lib_file} placeholder - use quotes for ngspice/hspice format
        if format in ['ngspice', 'hspice']:
            testbench = testbench.replace('{lib_file}', f'"{lib_file}"')
        else:
            testbench = testbench.replace('{lib_file}', lib_file)
        
        return testbench


def verify_device(
    device_file: str,
    device_name: str,
    device_class: str,
    source: str = 'spectre',
    target: str = 'ngspice',
    runs: int = 0,
    strict: bool = False,
    **params
) -> VerificationReport:
    """
    Convenience function for device verification
    
    Example:
        report = verify_device(
            device_file='gpdk090_capacitor.scs',
            device_name='mimcap',
            device_class='capacitor',
            source='spectre',
            target='ngspice',
            runs=500,
            area=10e-6,
            perim=20e-6
        )
    
    Args:
        device_file: Path to device library
        device_name: Model/subcircuit name
        device_class: Device type
        source: Source format
        target: Target format
        runs: Monte Carlo runs (0 = disabled)
        strict: Use strict tolerances
        **params: Device parameters
    
    Returns:
        VerificationReport
    """
    verifier = Verifier(monte_carlo_runs=runs, strict=strict)
    
    return verifier.verify(
        device_file=Path(device_file),
        device_name=device_name,
        device_class=device_class,
        source_format=source,
        target_format=target,
        **params
    )

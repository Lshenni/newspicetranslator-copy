"""
Comparators with Tolerances

Numerical comparison logic for verification with configurable tolerances.
Implements pass/fail decision logic based on relative and absolute errors.

Key Principle: Failing early is a feature, not a bug.
               Refuse certification if physics is compromised.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ComparisonStatus(Enum):
    """Comparison result status"""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"  # Unsupported feature


# ============================================================================
# TOLERANCE DEFINITIONS
# ============================================================================

TOLERANCES = {
    # Capacitor metrics
    'C_mean': {
        'relative': 0.01,  # 1% relative error
        'absolute': 1e-15  # 1fF absolute error
    },
    'C_sigma': {
        'relative': 0.05,  # 5% relative error (Monte Carlo has more variance)
        'absolute': 1e-14  # 10fF absolute error
    },
    'Z_error_max': {
        'relative': 0.01,  # 1% impedance error
        'absolute': 0.1    # 0.1 Ohm absolute
    },
    
    # MOS metrics
    'Id_sat': {
        'relative': 0.05,  # 5% current error
        'absolute': 1e-9   # 1nA absolute
    },
    'Vth': {
        'relative': 0.02,  # 2% Vth error
        'absolute': 0.01   # 10mV absolute
    },
    'gm_max': {
        'relative': 0.05,  # 5% transconductance error
        'absolute': 1e-6   # 1uS absolute
    },
    'Id_sigma': {
        'relative': 0.10,  # 10% sigma tolerance (MC stats)
        'absolute': 1e-10  # 0.1nA
    },
    'Vth_sigma': {
        'relative': 0.10,  # 10% sigma tolerance
        'absolute': 0.005  # 5mV
    },
    
    # BJT metrics
    'Ic_07': {
        'relative': 0.05,  # 5% collector current error
        'absolute': 1e-9   # 1nA
    },
    'beta_max': {
        'relative': 0.10,  # 10% beta tolerance
        'absolute': 5.0    # Absolute beta delta
    },
    
    # Diode metrics
    'Id_07': {
        'relative': 0.05,  # 5% current error
        'absolute': 1e-9   # 1nA
    },
    'Rs_07': {
        'relative': 0.10,  # 10% series resistance
        'absolute': 1.0    # 1 Ohm
    },
    
    # Resistor metrics
    'R_eff': {
        'relative': 0.02,  # 2% resistance error
        'absolute': 0.1    # 0.1 Ohm
    },
    'TC1': {
        'relative': 0.15,  # 15% TC tolerance
        'absolute': 1e-4   # Absolute TC delta
    }
}


# Strict mode tolerances (for certification-grade verification)
STRICT_TOLERANCES = {
    **TOLERANCES,
    'C_mean': {'relative': 0.001, 'absolute': 1e-16},  # 0.1%
    'Id_sat': {'relative': 0.01, 'absolute': 1e-10},   # 1%
    'Vth': {'relative': 0.01, 'absolute': 0.005},      # 1%, 5mV
}


@dataclass
class ComparisonResult:
    """Result of a single metric comparison"""
    metric_name: str
    reference_value: float
    target_value: float
    relative_error: float
    absolute_error: float
    status: ComparisonStatus
    message: str
    tolerance_used: Dict[str, float] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """Human-readable representation"""
        icon = {
            ComparisonStatus.PASS: "✅",
            ComparisonStatus.WARN: "⚠️",
            ComparisonStatus.FAIL: "❌",
            ComparisonStatus.SKIP: "⊘"
        }[self.status]
        
        return (f"{icon} [{self.status.value}] {self.metric_name}: "
                f"ref={self.reference_value:.3e}, tgt={self.target_value:.3e}, "
                f"rel_err={self.relative_error*100:.2f}%, {self.message}")


@dataclass
class VerificationResult:
    """Complete verification result for a device"""
    device_name: str
    device_class: str
    passed: bool
    comparisons: List[ComparisonResult]
    unsupported_features: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        """Generate summary report"""
        passed_count = sum(1 for c in self.comparisons if c.status == ComparisonStatus.PASS)
        failed_count = sum(1 for c in self.comparisons if c.status == ComparisonStatus.FAIL)
        warned_count = sum(1 for c in self.comparisons if c.status == ComparisonStatus.WARN)
        skipped_count = sum(1 for c in self.comparisons if c.status == ComparisonStatus.SKIP)
        
        lines = [
            f"{'='*70}",
            f"Verification Result: {self.device_name} ({self.device_class})",
            f"{'='*70}",
            f"Overall Status: {'✅ PASS' if self.passed else '❌ FAIL'}",
            f"",
            f"Metrics: {passed_count} passed, {failed_count} failed, "
            f"{warned_count} warnings, {skipped_count} skipped",
            f""
        ]
        
        for comp in self.comparisons:
            lines.append(str(comp))
        
        if self.unsupported_features:
            lines.append(f"\n⚠️  Unsupported features:")
            for feat in self.unsupported_features:
                lines.append(f"   - {feat}")
        
        if self.warnings:
            lines.append(f"\n⚠️  Warnings:")
            for warn in self.warnings:
                lines.append(f"   - {warn}")
        
        return "\n".join(lines)


class Comparator:
    """
    Numerical comparator with tolerance checking
    
    Usage:
        comp = Comparator(strict=False)
        result = comp.compare_metrics(ref_metrics, tgt_metrics, 'capacitor')
    """
    
    def __init__(self, strict: bool = False, custom_tolerances: Optional[Dict] = None):
        """
        Initialize comparator
        
        Args:
            strict: Use strict tolerances (for certification)
            custom_tolerances: Override default tolerances
        """
        self.strict = strict
        
        if custom_tolerances:
            self.tolerances = custom_tolerances
        elif strict:
            self.tolerances = STRICT_TOLERANCES
        else:
            self.tolerances = TOLERANCES
    
    def compare_metrics(
        self,
        reference: Dict[str, float],
        target: Dict[str, float],
        device_class: str,
        device_name: str = "unknown"
    ) -> VerificationResult:
        """
        Compare two sets of metrics
        
        Args:
            reference: Reference metrics (from original format)
            target: Target metrics (from translated format)
            device_class: Device type
            device_name: Device/model name
        
        Returns:
            VerificationResult with all comparisons
        """
        comparisons = []
        unsupported = []
        warnings = []
        
        # Compare all common metrics
        common_metrics = set(reference.keys()) & set(target.keys())
        
        for metric_name in common_metrics:
            ref_val = reference[metric_name]
            tgt_val = target[metric_name]
            
            comp_result = self.compare_single_metric(metric_name, ref_val, tgt_val)
            comparisons.append(comp_result)
        
        # Check for missing metrics in target
        missing_in_target = set(reference.keys()) - set(target.keys())
        for metric_name in missing_in_target:
            comparisons.append(ComparisonResult(
                metric_name=metric_name,
                reference_value=reference[metric_name],
                target_value=0.0,
                relative_error=1.0,
                absolute_error=reference[metric_name],
                status=ComparisonStatus.SKIP,
                message="Metric not available in target (unsupported feature)"
            ))
            unsupported.append(f"{metric_name} (not in target)")
        
        # Check for unexpected metrics in target
        extra_in_target = set(target.keys()) - set(reference.keys())
        for metric_name in extra_in_target:
            warnings.append(f"{metric_name} present in target but not reference")
        
        # Determine overall pass/fail
        has_failures = any(c.status == ComparisonStatus.FAIL for c in comparisons)
        passed = not has_failures
        
        # In strict mode, warnings also cause failure
        if self.strict and (warnings or unsupported):
            passed = False
        
        return VerificationResult(
            device_name=device_name,
            device_class=device_class,
            passed=passed,
            comparisons=comparisons,
            unsupported_features=unsupported,
            warnings=warnings
        )
    
    def compare_single_metric(
        self,
        metric_name: str,
        reference_value: float,
        target_value: float
    ) -> ComparisonResult:
        """
        Compare a single metric with tolerances
        
        Args:
            metric_name: Name of metric
            reference_value: Reference value
            target_value: Target value
        
        Returns:
            ComparisonResult
        """
        # Get tolerances for this metric
        tol = self.tolerances.get(metric_name, {
            'relative': 0.05,  # Default 5%
            'absolute': 1e-12  # Default small absolute
        })
        
        # Calculate errors
        abs_error = abs(target_value - reference_value)
        
        if abs(reference_value) > 0:
            rel_error = abs_error / abs(reference_value)
        else:
            rel_error = 0.0 if abs_error < tol['absolute'] else float('inf')
        
        # Determine pass/fail
        # Pass if EITHER relative OR absolute tolerance is satisfied
        relative_ok = rel_error <= tol['relative']
        absolute_ok = abs_error <= tol['absolute']
        
        if relative_ok or absolute_ok:
            status = ComparisonStatus.PASS
            message = f"Within tolerance (rel={rel_error*100:.2f}%, abs={abs_error:.3e})"
        elif rel_error <= tol['relative'] * 2:
            # Marginal - within 2x tolerance
            status = ComparisonStatus.WARN
            message = f"Marginal (rel={rel_error*100:.2f}%, abs={abs_error:.3e})"
        else:
            status = ComparisonStatus.FAIL
            message = (f"Out of tolerance (rel={rel_error*100:.2f}% > {tol['relative']*100:.2f}%, "
                      f"abs={abs_error:.3e} > {tol['absolute']:.3e})")
        
        return ComparisonResult(
            metric_name=metric_name,
            reference_value=reference_value,
            target_value=target_value,
            relative_error=rel_error,
            absolute_error=abs_error,
            status=status,
            message=message,
            tolerance_used=tol
        )


def compare_metrics(
    reference: Dict[str, float],
    target: Dict[str, float],
    device_class: str,
    strict: bool = False
) -> VerificationResult:
    """
    Convenience function for metric comparison
    
    Args:
        reference: Reference metrics
        target: Target metrics
        device_class: Device type
        strict: Use strict tolerances
    
    Returns:
        VerificationResult
    """
    comparator = Comparator(strict=strict)
    return comparator.compare_metrics(reference, target, device_class)


def should_fail_certification(result: VerificationResult) -> Tuple[bool, List[str]]:
    """
    Determine if certification should fail and why
    
    Certification MUST fail if:
      - Any metric exceeds tolerance
      - Unsupported physics is silently dropped (Monte Carlo flattened)
      - User requested strict fidelity
    
    Args:
        result: VerificationResult to evaluate
    
    Returns:
        (should_fail: bool, reasons: List[str])
    """
    reasons = []
    
    # Check for failed comparisons
    failures = [c for c in result.comparisons if c.status == ComparisonStatus.FAIL]
    if failures:
        for fail in failures:
            reasons.append(f"Metric {fail.metric_name} failed tolerance check")
    
    # Check for unsupported features
    if result.unsupported_features:
        for feat in result.unsupported_features:
            # Critical features that MUST NOT be dropped
            if any(critical in feat.lower() for critical in ['monte', 'mc', 'temperature', 'tc']):
                reasons.append(f"Critical feature unsupported: {feat}")
    
    # Check for silent dropping (warnings about missing critical params)
    critical_metrics = {'C_sigma', 'Id_sigma', 'Vth_sigma', 'TC1', 'TC2'}
    skipped_critical = [
        c.metric_name for c in result.comparisons 
        if c.status == ComparisonStatus.SKIP and c.metric_name in critical_metrics
    ]
    
    if skipped_critical:
        reasons.append(f"Critical metrics dropped: {', '.join(skipped_critical)}")
    
    should_fail = len(reasons) > 0
    
    return should_fail, reasons

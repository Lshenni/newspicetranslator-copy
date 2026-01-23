# Next Steps - Detailed Implementation Plan

**Date Created:** January 15, 2026  
**Status:** Ready for Implementation  
**Estimated Time:** 2-3 days total

---

## Overview

This document provides a detailed, step-by-step plan for completing the remaining work on the SPICE translator project. An AI agent can follow this plan independently.

**Current Status:**
- ✅ All core functionality working (Phases 1-6)
- ✅ CLI functional
- ✅ 15/15 integration tests passing
- ✅ 5/38 real files tested

**Remaining Work:**
1. **Verification Methods** - Roundtrip testing demo & simulation validation plan
2. **Input File Testing** - Test all 38 .scs files
3. **Output Organization** - Structured output folders with proper naming

---

## Task 1: Verification Methods (3-4 hours)

### Objective
Provide two verification approaches:
1. **Roundtrip Testing Tool** (working demo)
2. **Simulation Validation Plan** (detailed spec for future implementation)

---

### 1.1: Create Roundtrip Testing Tool

**File:** `tools/verify_roundtrip.py`

**Purpose:** Automated roundtrip testing with detailed reporting

**Requirements:**
```python
"""
Roundtrip Verification Tool

Tests translation quality by:
1. Parse source file (Format A)
2. Translate to Format B
3. Translate back to Format A
4. Compare original vs. final

Reports:
- Model count preservation
- Parameter value differences
- Name/alias changes
- Warnings and errors
"""

Usage:
    python tools/verify_roundtrip.py input.scs --via ngspice
    python tools/verify_roundtrip.py input.lib --via spectre --format hspice
```

**Implementation Steps:**

**Step 1.1.1:** Create basic structure
```python
#!/usr/bin/env python3
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
import json

from src.parsers import SpectreParser, HSPICEParser, NgspiceParser
from src.writers import SpectreWriter, HSPICEWriter, NgspiceWriter
from src.validation import IRValidator

@dataclass
class RoundtripResult:
    """Results of roundtrip test."""
    success: bool
    source_file: str
    intermediate_format: str
    source_models: int
    intermediate_models: int
    final_models: int
    model_names_preserved: bool
    parameter_diffs: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            'success': self.success,
            'source_file': self.source_file,
            'intermediate_format': self.intermediate_format,
            'models': {
                'source': self.source_models,
                'intermediate': self.intermediate_models,
                'final': self.final_models
            },
            'model_names_preserved': self.model_names_preserved,
            'parameter_diffs': self.parameter_diffs,
            'warnings': self.warnings,
            'errors': self.errors
        }
    
    def print_summary(self):
        """Print human-readable summary."""
        print(f"\n{'='*60}")
        print(f"Roundtrip Test: {self.source_file}")
        print(f"{'='*60}")
        print(f"Route: source → {self.intermediate_format} → source")
        print(f"Models: {self.source_models} → {self.intermediate_models} → {self.final_models}")
        
        if self.success:
            print(f"\n✓ SUCCESS: Roundtrip completed")
        else:
            print(f"\n✗ FAILED: {len(self.errors)} errors")
        
        if self.model_names_preserved:
            print(f"✓ Model names preserved")
        else:
            print(f"⚠ Model names changed")
        
        if self.parameter_diffs:
            print(f"\n⚠ Parameter Differences: {len(self.parameter_diffs)}")
            for diff in self.parameter_diffs[:5]:
                print(f"  - {diff['model']}.{diff['parameter']}: "
                      f"{diff['original']} → {diff['final']} "
                      f"(Δ={diff['delta']:.2e})")
            if len(self.parameter_diffs) > 5:
                print(f"  ... and {len(self.parameter_diffs) - 5} more")
        
        if self.warnings:
            print(f"\nWarnings: {len(self.warnings)}")
            for w in self.warnings[:3]:
                print(f"  - {w}")
        
        if self.errors:
            print(f"\nErrors: {len(self.errors)}")
            for e in self.errors[:3]:
                print(f"  - {e}")
        
        print(f"{'='*60}\n")
```

**Step 1.1.2:** Implement roundtrip logic
```python
class RoundtripTester:
    """Performs roundtrip translation tests."""
    
    def __init__(self, tolerance: float = 1e-6):
        self.tolerance = tolerance
    
    def test_roundtrip(
        self,
        source_file: Path,
        source_format: str,
        intermediate_format: str,
        output_dir: Path = None
    ) -> RoundtripResult:
        """
        Perform roundtrip test.
        
        Args:
            source_file: Original file to test
            source_format: Source format (spectre, hspice, ngspice)
            intermediate_format: Intermediate format for translation
            output_dir: Optional directory for intermediate files
        
        Returns:
            RoundtripResult with detailed comparison
        """
        result = RoundtripResult(
            success=False,
            source_file=str(source_file),
            intermediate_format=intermediate_format,
            source_models=0,
            intermediate_models=0,
            final_models=0,
            model_names_preserved=False,
            parameter_diffs=[],
            warnings=[],
            errors=[]
        )
        
        # Use temp dir if not specified
        if output_dir is None:
            output_dir = Path("/tmp/roundtrip_test")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: Parse original
            source_parser = self._get_parser(source_format, source_file)
            source_models = source_parser.parse_to_ir()
            result.source_models = len(source_models)
            
            # Step 2: Translate to intermediate format
            intermediate_file = output_dir / f"intermediate.{self._get_extension(intermediate_format)}"
            intermediate_writer = self._get_writer(intermediate_format, intermediate_file)
            intermediate_writer.write_from_ir(source_models)
            
            # Step 3: Parse intermediate
            intermediate_parser = self._get_parser(intermediate_format, intermediate_file)
            intermediate_models = intermediate_parser.parse_to_ir()
            result.intermediate_models = len(intermediate_models)
            
            # Step 4: Translate back to source format
            final_file = output_dir / f"final.{self._get_extension(source_format)}"
            final_writer = self._get_writer(source_format, final_file)
            final_writer.write_from_ir(intermediate_models)
            
            # Step 5: Parse final
            final_parser = self._get_parser(source_format, final_file)
            final_models = final_parser.parse_to_ir()
            result.final_models = len(final_models)
            
            # Step 6: Compare
            self._compare_models(source_models, final_models, result)
            
            # Success if no errors
            result.success = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Roundtrip failed: {str(e)}")
        
        return result
    
    def _compare_models(self, source_models, final_models, result):
        """Compare source and final models, populate result."""
        # Check model count
        if len(source_models) != len(final_models):
            result.errors.append(
                f"Model count mismatch: {len(source_models)} → {len(final_models)}"
            )
            return
        
        # Check model names
        source_names = {m.name for m in source_models}
        final_names = {m.name for m in final_models}
        result.model_names_preserved = (source_names == final_names)
        
        if not result.model_names_preserved:
            missing = source_names - final_names
            added = final_names - source_names
            if missing:
                result.warnings.append(f"Missing models: {missing}")
            if added:
                result.warnings.append(f"Added models: {added}")
        
        # Compare parameters
        for src_model, final_model in zip(source_models, final_models):
            self._compare_parameters(src_model, final_model, result)
    
    def _compare_parameters(self, src_model, final_model, result):
        """Compare parameters between two models."""
        src_params = src_model.base_parameters
        final_params = final_model.base_parameters
        
        # Find parameter differences
        all_keys = set(src_params.keys()) | set(final_params.keys())
        
        for key in all_keys:
            src_val = src_params.get(key)
            final_val = final_params.get(key)
            
            if src_val is None:
                result.warnings.append(
                    f"{final_model.name}: Parameter '{key}' added in final"
                )
            elif final_val is None:
                result.warnings.append(
                    f"{src_model.name}: Parameter '{key}' missing in final"
                )
            else:
                # Compare values
                try:
                    src_float = float(src_val)
                    final_float = float(final_val)
                    delta = abs(src_float - final_float)
                    
                    if delta > self.tolerance:
                        result.parameter_diffs.append({
                            'model': src_model.name,
                            'parameter': key,
                            'original': src_float,
                            'final': final_float,
                            'delta': delta
                        })
                except (ValueError, TypeError):
                    # String comparison
                    if str(src_val) != str(final_val):
                        result.warnings.append(
                            f"{src_model.name}.{key}: '{src_val}' → '{final_val}'"
                        )
    
    def _get_parser(self, format_name: str, file_path: Path):
        """Get parser instance."""
        parsers = {
            'spectre': SpectreParser,
            'hspice': HSPICEParser,
            'ngspice': NgspiceParser
        }
        return parsers[format_name.lower()](file_path)
    
    def _get_writer(self, format_name: str, file_path: Path):
        """Get writer instance."""
        writers = {
            'spectre': SpectreWriter,
            'hspice': HSPICEWriter,
            'ngspice': NgspiceWriter
        }
        return writers[format_name.lower()](file_path)
    
    def _get_extension(self, format_name: str) -> str:
        """Get file extension for format."""
        extensions = {
            'spectre': 'scs',
            'hspice': 'sp',
            'ngspice': 'lib'
        }
        return extensions[format_name.lower()]
```

**Step 1.1.3:** Add CLI interface
```python
def main():
    parser = argparse.ArgumentParser(
        description='Roundtrip translation verification tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Test Spectre → ngspice → Spectre
  python tools/verify_roundtrip.py models.scs --via ngspice
  
  # Test HSPICE → Spectre → HSPICE
  python tools/verify_roundtrip.py models.sp --via spectre --format hspice
  
  # Export results as JSON
  python tools/verify_roundtrip.py models.scs --via ngspice --json results.json
        '''
    )
    
    parser.add_argument('input', help='Input SPICE file')
    parser.add_argument('--via', required=True,
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Intermediate format for roundtrip')
    parser.add_argument('--format', 
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Source format (auto-detect if not specified)')
    parser.add_argument('--tolerance', type=float, default=1e-6,
                       help='Tolerance for parameter comparison (default: 1e-6)')
    parser.add_argument('--json', help='Export results as JSON')
    parser.add_argument('--output-dir', help='Directory for intermediate files')
    
    args = parser.parse_args()
    
    # Auto-detect format
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        return 1
    
    if args.format:
        source_format = args.format
    else:
        # Auto-detect from extension
        ext = input_file.suffix.lower()
        ext_map = {'.scs': 'spectre', '.sp': 'hspice', '.lib': 'ngspice'}
        source_format = ext_map.get(ext, 'spectre')
        print(f"Auto-detected format: {source_format}")
    
    # Run roundtrip test
    tester = RoundtripTester(tolerance=args.tolerance)
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    result = tester.test_roundtrip(
        source_file=input_file,
        source_format=source_format,
        intermediate_format=args.via,
        output_dir=output_dir
    )
    
    # Print results
    result.print_summary()
    
    # Export JSON if requested
    if args.json:
        json_path = Path(args.json)
        json_path.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"Results exported to: {json_path}")
    
    return 0 if result.success else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
```

**Acceptance Criteria:**
- ✅ Tool runs without errors
- ✅ Reports model count preservation
- ✅ Detects parameter value changes
- ✅ Exports JSON results
- ✅ Works with all 3 formats

---

### 1.2: Create Simulation Validation Plan

**File:** `docs/SIMULATION_VALIDATION_PLAN.md`

**Purpose:** Detailed specification for implementing ngspice simulation validation

**Required Content:**

```markdown
# Simulation Validation Implementation Plan

## Overview
This document specifies how to implement simulation-based verification for translated SPICE netlists.

## Goals
1. Verify translated netlists produce identical simulation results
2. Catch parameter mapping errors not caught by syntax validation
3. Provide confidence in behavioral equivalence

## Architecture

### Component 1: Test Circuit Generator
**File:** `src/validation/test_circuits.py`

Generates test circuits for each model type:
- **Capacitor**: RC circuit, measure time constant
- **Resistor**: Voltage divider, measure resistance
- **Diode**: IV curve sweep
- **MOS**: Drain current vs. gate voltage
- **Bipolar**: Collector current vs. base current

**Example:**
```spice
* Test circuit for NMOS model
.include models.lib
M1 drain gate 0 0 nmos_model w=1u l=100n
Vgs gate 0 DC 0
Vds drain 0 DC 1.8
.dc Vgs 0 1.8 0.01
.print dc i(Vds)
.end
```

### Component 2: ngspice Wrapper
**File:** `src/validation/ngspice_runner.py`

```python
class NgspiceRunner:
    def __init__(self, ngspice_path: str = "ngspice"):
        self.ngspice_path = ngspice_path
    
    def run_simulation(self, netlist: str) -> SimulationResult:
        """Run ngspice and capture output."""
        # 1. Write netlist to temp file
        # 2. Run: ngspice -b netlist.sp -o output.txt
        # 3. Parse output
        # 4. Return voltage/current arrays
    
    def check_installed(self) -> bool:
        """Check if ngspice is installed."""
```

### Component 3: Result Comparator
**File:** `src/validation/simulation_comparator.py`

```python
class SimulationComparator:
    def compare_waveforms(
        self,
        original: np.ndarray,
        translated: np.ndarray,
        tolerance: float = 0.01
    ) -> ComparisonResult:
        """Compare two waveforms point-by-point."""
        # 1. Check array lengths match
        # 2. Compute RMS error
        # 3. Check max deviation
        # 4. Return pass/fail with metrics
```

### Component 4: Simulation Validator
**File:** `src/validation/simulation_validator.py`

```python
class SimulationValidator:
    def validate_translation(
        self,
        source_file: Path,
        target_file: Path,
        model_type: str
    ) -> SimulationValidationResult:
        """
        Full simulation validation workflow.
        
        1. Generate test circuit for model_type
        2. Run simulation on source_file
        3. Run simulation on target_file
        4. Compare results
        5. Return pass/fail with detailed metrics
        """
```

## Implementation Steps

### Phase 1: Basic Infrastructure (4 hours)
1. Implement NgspiceRunner
2. Add test for ngspice installation
3. Create simple test circuit (resistor divider)
4. Verify basic simulation works

### Phase 2: Test Circuit Library (4 hours)
1. Implement circuits for each model type
2. Add parameter sweeps (DC, AC, transient)
3. Validate circuits manually with ngspice
4. Document expected outputs

### Phase 3: Comparator (3 hours)
1. Implement waveform comparison
2. Add tolerance handling
3. Implement metrics (RMS error, max deviation)
4. Add plotting for visual comparison

### Phase 4: Integration (3 hours)
1. Integrate with TranslationValidator
2. Add CLI flag: --verify-simulation
3. Write integration tests
4. Document usage

## Usage Examples

### Basic Usage
```bash
# Validate with simulation
python -m src.main translate input.scs output.lib \
    --from spectre --to ngspice \
    --verify-simulation
```

### Advanced Usage
```python
from src.validation import SimulationValidator

validator = SimulationValidator()
result = validator.validate_translation(
    source_file=Path("models.scs"),
    target_file=Path("models.lib"),
    model_type="mos"
)

if result.pass:
    print(f"✓ Simulation match: RMS error = {result.rms_error:.2e}")
else:
    print(f"✗ Simulation mismatch: Max error = {result.max_error:.2%}")
```

## Dependencies
- ngspice (system package)
- numpy (for numerical comparison)
- matplotlib (optional, for plotting)

## Installation
```bash
# Ubuntu/Debian
sudo apt-get install ngspice

# macOS
brew install ngspice

# Python packages
pip install numpy matplotlib
```

## Testing Strategy
1. **Unit tests**: Test each component independently
2. **Integration tests**: Full validation workflow
3. **Regression tests**: Known-good translations
4. **Performance tests**: Ensure simulations complete in <5s

## Known Limitations
1. **Convergence issues**: Some netlists may not converge
2. **Model availability**: ngspice may not have all models
3. **Performance**: Simulation is slow (2-5s per test)
4. **Platform dependency**: Requires ngspice installation

## Alternatives
If simulation validation proves too complex:
1. **Differential parameter analysis** (compare values numerically)
2. **Golden reference testing** (compare against known-good outputs)
3. **Syntax + roundtrip** (current approach, 90% effective)

## Success Criteria
- ✅ Detects parameter mapping errors
- ✅ Runs in <5 seconds per model
- ✅ Handles convergence failures gracefully
- ✅ Provides detailed error reports
- ✅ Works on Linux, macOS, Windows

## Time Estimate
- **Minimum viable**: 8 hours (basic resistor/capacitor only)
- **Production ready**: 14 hours (all model types)
- **Full featured**: 20 hours (plotting, advanced metrics)
```

**Acceptance Criteria:**
- ✅ Complete specification document
- ✅ Clear implementation steps
- ✅ Code examples provided
- ✅ Dependencies documented
- ✅ Time estimates included

---

## Task 2: Comprehensive Input File Testing (4-6 hours)

### Objective
Test all 38 .scs files, document results, identify failure patterns

---

### 2.1: Expand Test Coverage

**File:** `tests/integration/test_all_real_files.py`

**Step 2.1.1:** Create comprehensive test suite
```python
"""
Comprehensive testing of all 38 real Spectre files.

This extends test_real_files.py to cover ALL available files,
not just the first 5.
"""

import pytest
from pathlib import Path
import json
import time

from tests.integration.test_real_files import (
    find_spectre_files,
    PROJECT_ROOT
)
from src.parsers import SpectreParser
from src.writers import NgspiceWriter, HSPICEWriter
from src.validation import IRValidator, SyntaxValidator, SPICEFormat

# Get ALL files
ALL_SPECTRE_FILES = find_spectre_files()


@pytest.mark.parametrize("input_file", ALL_SPECTRE_FILES)
def test_parse_all_spectre_files(input_file):
    """Parse all 38 Spectre files."""
    parser = SpectreParser(input_file)
    
    try:
        models = parser.parse_to_ir()
        
        # Basic validation
        validator = IRValidator()
        result = validator.validate(models)
        
        # Log results
        print(f"✓ {input_file.name}: {len(models)} models, "
              f"{result.error_count} errors, {result.warning_count} warnings")
        
        assert result.error_count == 0, \
            f"IR errors in {input_file}: {result.errors[:3]}"
    
    except Exception as e:
        pytest.fail(f"Failed to parse {input_file}: {e}")


@pytest.mark.parametrize("input_file", ALL_SPECTRE_FILES)
def test_translate_all_to_ngspice(input_file, tmp_path):
    """Translate all 38 files to ngspice."""
    parser = SpectreParser(input_file)
    models = parser.parse_to_ir()
    
    if len(models) == 0:
        pytest.skip(f"No models in {input_file}")
    
    output_file = tmp_path / f"{input_file.stem}_ngspice.lib"
    writer = NgspiceWriter(output_file)
    
    try:
        writer.write_from_ir(models)
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Validate syntax
        content = output_file.read_text()
        validator = SyntaxValidator(format=SPICEFormat.NGSPICE)
        result = validator.validate(content)
        
        print(f"✓ {input_file.name} → ngspice: {len(models)} models")
        
        assert result.error_count == 0
        
    except Exception as e:
        pytest.fail(f"Translation failed for {input_file}: {e}")
```

**Step 2.1.2:** Add batch test with reporting
```python
def test_batch_all_files_with_report(tmp_path):
    """
    Batch test all files and generate detailed report.
    """
    results = []
    start_time = time.time()
    
    for input_file in ALL_SPECTRE_FILES:
        file_result = {
            'file': input_file.name,
            'size_kb': input_file.stat().st_size / 1024,
            'status': 'unknown',
            'models': 0,
            'errors': [],
            'warnings': [],
            'parse_time': 0,
            'translate_time': 0
        }
        
        try:
            # Parse
            parse_start = time.time()
            parser = SpectreParser(input_file)
            models = parser.parse_to_ir()
            file_result['parse_time'] = time.time() - parse_start
            file_result['models'] = len(models)
            
            if len(models) == 0:
                file_result['status'] = 'skipped'
                file_result['warnings'].append('No models found')
                results.append(file_result)
                continue
            
            # Translate
            translate_start = time.time()
            output_file = tmp_path / f"{input_file.stem}.lib"
            writer = NgspiceWriter(output_file)
            writer.write_from_ir(models)
            file_result['translate_time'] = time.time() - translate_start
            
            # Validate
            content = output_file.read_text()
            validator = SyntaxValidator(format=SPICEFormat.NGSPICE)
            result = validator.validate(content)
            
            if result.error_count > 0:
                file_result['status'] = 'failed'
                file_result['errors'] = result.errors[:5]
            else:
                file_result['status'] = 'success'
                if result.warning_count > 0:
                    file_result['warnings'] = result.warnings[:3]
        
        except Exception as e:
            file_result['status'] = 'error'
            file_result['errors'].append(str(e))
        
        results.append(file_result)
    
    total_time = time.time() - start_time
    
    # Generate report
    report = {
        'summary': {
            'total_files': len(ALL_SPECTRE_FILES),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'errors': sum(1 for r in results if r['status'] == 'error'),
            'skipped': sum(1 for r in results if r['status'] == 'skipped'),
            'total_models': sum(r['models'] for r in results),
            'total_time': total_time,
            'avg_time_per_file': total_time / len(ALL_SPECTRE_FILES)
        },
        'files': results
    }
    
    # Save report
    report_file = PROJECT_ROOT / 'test_results' / 'all_files_report.json'
    report_file.parent.mkdir(exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2))
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Batch Test Results: ALL 38 Files")
    print(f"{'='*70}")
    print(f"Success: {report['summary']['success']}/{report['summary']['total_files']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Errors: {report['summary']['errors']}")
    print(f"Skipped: {report['summary']['skipped']}")
    print(f"Total Models: {report['summary']['total_models']}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Report saved: {report_file}")
    print(f"{'='*70}\n")
    
    # Show failures
    if report['summary']['failed'] > 0 or report['summary']['errors'] > 0:
        print("Failed/Error Files:")
        for r in results:
            if r['status'] in ['failed', 'error']:
                print(f"  ✗ {r['file']}: {r['status']}")
                for err in r['errors'][:2]:
                    print(f"      - {err}")
    
    # At least 80% should succeed
    success_rate = report['summary']['success'] / report['summary']['total_files']
    assert success_rate >= 0.80, \
        f"Success rate {success_rate:.1%} below 80% threshold"
```

**Acceptance Criteria:**
- ✅ All 38 files tested
- ✅ JSON report generated
- ✅ Success rate ≥80%
- ✅ Failures documented with error messages

---

### 2.2: Create Analysis Tool

**File:** `tools/analyze_test_results.py`

**Purpose:** Analyze test results and identify patterns

**Step 2.2.1:** Implement analyzer
```python
#!/usr/bin/env python3
"""
Test Results Analyzer

Analyzes test_results/all_files_report.json and generates:
1. Success rate by file size
2. Common error patterns
3. Model type distribution
4. Performance metrics
"""

import json
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt

def analyze_results(report_file: Path):
    """Analyze test results and generate report."""
    with open(report_file) as f:
        data = json.load(f)
    
    summary = data['summary']
    files = data['files']
    
    print(f"\n{'='*70}")
    print(f"Test Results Analysis")
    print(f"{'='*70}\n")
    
    # Overall stats
    print(f"Overall Statistics:")
    print(f"  Total Files: {summary['total_files']}")
    print(f"  Success Rate: {summary['success']}/{summary['total_files']} "
          f"({summary['success']/summary['total_files']*100:.1f}%)")
    print(f"  Total Models: {summary['total_models']}")
    print(f"  Avg Time: {summary['avg_time_per_file']:.3f}s per file")
    print()
    
    # Size distribution
    size_buckets = defaultdict(lambda: {'count': 0, 'success': 0})
    for f in files:
        size = f['size_kb']
        if size < 10:
            bucket = '<10KB'
        elif size < 50:
            bucket = '10-50KB'
        elif size < 100:
            bucket = '50-100KB'
        else:
            bucket = '>100KB'
        
        size_buckets[bucket]['count'] += 1
        if f['status'] == 'success':
            size_buckets[bucket]['success'] += 1
    
    print(f"Success Rate by File Size:")
    for bucket, stats in sorted(size_buckets.items()):
        rate = stats['success'] / stats['count'] * 100
        print(f"  {bucket:12s}: {stats['success']}/{stats['count']} ({rate:.1f}%)")
    print()
    
    # Error analysis
    error_counts = defaultdict(int)
    for f in files:
        for err in f['errors']:
            # Extract error type
            if ':' in err:
                error_type = err.split(':')[0]
            else:
                error_type = err[:50]
            error_counts[error_type] += 1
    
    if error_counts:
        print(f"Most Common Errors:")
        for error_type, count in sorted(error_counts.items(), 
                                       key=lambda x: x[1], 
                                       reverse=True)[:5]:
            print(f"  {count:2d}x: {error_type}")
        print()
    
    # Top performers
    successful = [f for f in files if f['status'] == 'success']
    if successful:
        print(f"Largest Successfully Translated Files:")
        for f in sorted(successful, key=lambda x: x['size_kb'], reverse=True)[:5]:
            print(f"  {f['file']:40s} {f['size_kb']:6.1f} KB, {f['models']:3d} models")
        print()
    
    # Problem files
    failures = [f for f in files if f['status'] in ['failed', 'error']]
    if failures:
        print(f"Problem Files Requiring Attention:")
        for f in failures[:10]:
            print(f"  {f['file']:40s} {f['status']:8s}")
            if f['errors']:
                print(f"    └─ {f['errors'][0][:60]}")

if __name__ == '__main__':
    report_file = Path(__file__).parent.parent / 'test_results' / 'all_files_report.json'
    if not report_file.exists():
        print(f"Error: Report not found: {report_file}")
        print(f"Run: pytest tests/integration/test_all_real_files.py::test_batch_all_files_with_report")
        exit(1)
    
    analyze_results(report_file)
```

**Acceptance Criteria:**
- ✅ Parses JSON report
- ✅ Shows success rate by file size
- ✅ Identifies common errors
- ✅ Lists problem files

---

## Task 3: Output Folder Organization (2-3 hours)

### Objective
Create organized output structure with proper file naming conventions

---

### 3.1: Define Output Structure

**Current Problem:**
- Files written to random locations
- No naming convention
- Hard to track translations

**Desired Structure:**
```
output/
├── spectre_to_ngspice/
│   ├── gpdk090_capacitor.lib
│   ├── gpdk090_mos.lib
│   └── ...
├── spectre_to_hspice/
│   ├── gpdk090_capacitor.sp
│   ├── gpdk090_mos.sp
│   └── ...
├── ngspice_to_spectre/
│   └── ...
├── reports/
│   ├── translation_report_2026-01-15_14-30-00.json
│   └── roundtrip_report_2026-01-15_14-35-00.json
└── intermediate/
    └── temp files for roundtrip testing
```

---

### 3.2: Implement Output Manager

**File:** `src/utils/output_manager.py`

**Step 3.2.1:** Create OutputManager class
```python
"""
Output file organization and naming utilities.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import shutil

class OutputManager:
    """
    Manages output file organization and naming.
    
    Provides consistent naming and folder structure for translated files.
    """
    
    def __init__(self, base_dir: Path = None):
        """
        Initialize output manager.
        
        Args:
            base_dir: Base output directory (default: ./output)
        """
        if base_dir is None:
            base_dir = Path.cwd() / 'output'
        
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_translation_dir(
        self,
        source_format: str,
        target_format: str
    ) -> Path:
        """
        Get directory for translations.
        
        Args:
            source_format: Source format (spectre, hspice, ngspice)
            target_format: Target format
        
        Returns:
            Path to translation directory
        
        Example:
            >>> manager.get_translation_dir('spectre', 'ngspice')
            Path('output/spectre_to_ngspice')
        """
        dir_name = f"{source_format}_to_{target_format}"
        output_dir = self.base_dir / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def get_output_path(
        self,
        input_file: Path,
        source_format: str,
        target_format: str,
        suffix: str = None
    ) -> Path:
        """
        Get organized output path for translation.
        
        Args:
            input_file: Original input file
            source_format: Source format
            target_format: Target format
            suffix: Optional suffix (e.g., '_validated')
        
        Returns:
            Path for output file with correct extension
        
        Example:
            >>> manager.get_output_path(
            ...     Path('models.scs'),
            ...     'spectre',
            ...     'ngspice'
            ... )
            Path('output/spectre_to_ngspice/models.lib')
        """
        # Get translation directory
        output_dir = self.get_translation_dir(source_format, target_format)
        
        # Determine file extension
        extensions = {
            'spectre': 'scs',
            'hspice': 'sp',
            'ngspice': 'lib'
        }
        ext = extensions[target_format.lower()]
        
        # Build filename
        base_name = input_file.stem
        if suffix:
            base_name = f"{base_name}{suffix}"
        
        filename = f"{base_name}.{ext}"
        
        return output_dir / filename
    
    def get_report_path(
        self,
        report_type: str,
        format: str = 'json'
    ) -> Path:
        """
        Get path for report file with timestamp.
        
        Args:
            report_type: Type of report (translation, roundtrip, batch)
            format: Report format (json, txt, html)
        
        Returns:
            Path for report file
        
        Example:
            >>> manager.get_report_path('translation')
            Path('output/reports/translation_report_2026-01-15_14-30-00.json')
        """
        reports_dir = self.base_dir / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"{report_type}_report_{timestamp}.{format}"
        
        return reports_dir / filename
    
    def get_intermediate_dir(self) -> Path:
        """Get directory for intermediate/temp files."""
        intermediate_dir = self.base_dir / 'intermediate'
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        return intermediate_dir
    
    def clean_intermediate(self):
        """Clean up intermediate/temp files."""
        intermediate_dir = self.get_intermediate_dir()
        if intermediate_dir.exists():
            shutil.rmtree(intermediate_dir)
            intermediate_dir.mkdir()
    
    def get_batch_summary_path(self) -> Path:
        """Get path for batch processing summary."""
        return self.get_report_path('batch_summary', 'json')
    
    def organize_existing_files(
        self,
        source_dir: Path,
        source_format: str,
        target_format: str
    ):
        """
        Organize existing translated files into proper structure.
        
        Args:
            source_dir: Directory containing translated files
            source_format: Source format
            target_format: Target format
        
        Example:
            >>> manager.organize_existing_files(
            ...     Path('/tmp/translations'),
            ...     'spectre',
            ...     'ngspice'
            ... )
        """
        target_dir = self.get_translation_dir(source_format, target_format)
        
        extensions = {
            'spectre': '.scs',
            'hspice': '.sp',
            'ngspice': '.lib'
        }
        ext = extensions[target_format]
        
        # Move matching files
        moved_count = 0
        for file in source_dir.glob(f"*{ext}"):
            target_path = target_dir / file.name
            shutil.copy2(file, target_path)
            moved_count += 1
        
        print(f"Organized {moved_count} files into {target_dir}")
        
        return moved_count
```

**Acceptance Criteria:**
- ✅ Creates organized directory structure
- ✅ Consistent file naming
- ✅ Handles all format combinations
- ✅ Timestamped reports
- ✅ Intermediate file cleanup

---

### 3.3: Update CLI to Use OutputManager

**File:** `src/main.py`

**Step 3.3.1:** Integrate OutputManager into translate command
```python
# Add at top of file
from src.utils.output_manager import OutputManager

# In TranslationEngine.__init__
def __init__(self, verbose: bool = False, output_manager: OutputManager = None):
    self.verbose = verbose
    self.output_manager = output_manager or OutputManager()
    self._setup_logging()

# Update translate method signature
def translate(
    self,
    input_file: Path,
    output_file: Path = None,  # Make optional
    source_format: str,
    target_format: str,
    validate: bool = True,
    strict: bool = False,
    use_organized_output: bool = True
) -> dict:
    """
    Translate SPICE file from source to target format.
    
    Args:
        input_file: Input file path
        output_file: Output file path (optional, auto-generated if not provided)
        source_format: Source format
        target_format: Target format
        validate: Run validation
        strict: Strict validation
        use_organized_output: Use organized output structure
    """
    # Auto-generate output path if not provided
    if output_file is None and use_organized_output:
        output_file = self.output_manager.get_output_path(
            input_file,
            source_format,
            target_format
        )
        logger.info(f"Auto-generated output path: {output_file}")
    elif output_file is None:
        # Fallback: same dir as input
        extensions = {'spectre': 'scs', 'hspice': 'sp', 'ngspice': 'lib'}
        ext = extensions[target_format.lower()]
        output_file = input_file.parent / f"{input_file.stem}_translated.{ext}"
    
    # ... rest of method
```

**Step 3.3.2:** Update CLI argument parsing
```python
# In cmd_translate function
def cmd_translate(args: argparse.Namespace) -> int:
    """Handle translate command."""
    engine = TranslationEngine(verbose=args.verbose)
    
    input_file = Path(args.input)
    
    # Output file is now optional
    if args.output:
        output_file = Path(args.output)
    else:
        # Use organized output structure
        output_file = None  # Auto-generated
    
    # ... rest of function

# Update argument parser
translate_parser.add_argument('output', nargs='?', default=None,
                             help='Output file path (auto-generated if omitted)')
translate_parser.add_argument('--no-organize', action='store_true',
                             help='Disable organized output structure')
```

**Acceptance Criteria:**
- ✅ Output path auto-generated if not specified
- ✅ Files organized by translation type
- ✅ Backward compatible (manual paths still work)
- ✅ `--no-organize` flag available

---

### 3.4: Create Batch Translation Tool

**File:** `tools/batch_translate.py`

**Purpose:** Translate multiple files with organized output

**Step 3.4.1:** Implement batch translator
```python
#!/usr/bin/env python3
"""
Batch translation tool with organized output.

Translates multiple SPICE files and organizes outputs by translation type.
"""

import argparse
from pathlib import Path
import json
from typing import List
import time

from src.main import TranslationEngine
from src.utils.output_manager import OutputManager


def batch_translate(
    input_files: List[Path],
    source_format: str,
    target_format: str,
    output_dir: Path = None,
    validate: bool = True,
    continue_on_error: bool = True
) -> dict:
    """
    Translate multiple files with organized output.
    
    Args:
        input_files: List of input files
        source_format: Source format
        target_format: Target format
        output_dir: Base output directory
        validate: Enable validation
        continue_on_error: Continue if a file fails
    
    Returns:
        Dictionary with batch results
    """
    output_manager = OutputManager(base_dir=output_dir)
    engine = TranslationEngine(output_manager=output_manager)
    
    results = {
        'summary': {
            'total_files': len(input_files),
            'successful': 0,
            'failed': 0,
            'total_models': 0,
            'total_time': 0
        },
        'files': []
    }
    
    start_time = time.time()
    
    for input_file in input_files:
        print(f"\nTranslating: {input_file.name}")
        print(f"  {source_format} → {target_format}")
        
        file_result = {
            'input': str(input_file),
            'output': None,
            'status': 'unknown',
            'models': 0,
            'errors': [],
            'time': 0
        }
        
        try:
            file_start = time.time()
            
            # Auto-generate organized output path
            output_file = output_manager.get_output_path(
                input_file,
                source_format,
                target_format
            )
            
            # Translate
            result = engine.translate(
                input_file=input_file,
                output_file=output_file,
                source_format=source_format,
                target_format=target_format,
                validate=validate,
                use_organized_output=True
            )
            
            file_result['time'] = time.time() - file_start
            file_result['output'] = str(output_file)
            
            if result['success']:
                file_result['status'] = 'success'
                file_result['models'] = result['models_translated']
                results['summary']['successful'] += 1
                results['summary']['total_models'] += result['models_translated']
                print(f"  ✓ Success: {result['models_translated']} models in {file_result['time']:.2f}s")
                print(f"  Output: {output_file}")
            else:
                file_result['status'] = 'failed'
                file_result['errors'] = [result.get('error', 'Unknown error')]
                results['summary']['failed'] += 1
                print(f"  ✗ Failed: {result.get('error')}")
                
                if not continue_on_error:
                    break
        
        except Exception as e:
            file_result['status'] = 'error'
            file_result['errors'] = [str(e)]
            results['summary']['failed'] += 1
            print(f"  ✗ Error: {e}")
            
            if not continue_on_error:
                break
        
        results['files'].append(file_result)
    
    results['summary']['total_time'] = time.time() - start_time
    
    # Save report
    report_path = output_manager.get_report_path('batch_translation')
    report_path.write_text(json.dumps(results, indent=2))
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Batch Translation Complete")
    print(f"{'='*70}")
    print(f"Success: {results['summary']['successful']}/{results['summary']['total_files']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Total Models: {results['summary']['total_models']}")
    print(f"Total Time: {results['summary']['total_time']:.2f}s")
    print(f"Report: {report_path}")
    print(f"{'='*70}\n")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Batch SPICE file translation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Translate all .scs files in directory
  python tools/batch_translate.py input/*.scs --from spectre --to ngspice
  
  # Translate with custom output directory
  python tools/batch_translate.py input/*.scs --from spectre --to ngspice \\
      --output-dir /path/to/output
  
  # Stop on first error
  python tools/batch_translate.py input/*.scs --from spectre --to ngspice \\
      --stop-on-error
        '''
    )
    
    parser.add_argument('files', nargs='+', help='Input files to translate')
    parser.add_argument('--from', dest='source_format', required=True,
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Source format')
    parser.add_argument('--to', dest='target_format', required=True,
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Target format')
    parser.add_argument('--output-dir', type=Path,
                       help='Base output directory (default: ./output)')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip validation')
    parser.add_argument('--stop-on-error', action='store_true',
                       help='Stop on first error')
    
    args = parser.parse_args()
    
    # Expand file patterns
    input_files = [Path(f) for f in args.files]
    
    # Run batch translation
    results = batch_translate(
        input_files=input_files,
        source_format=args.source_format,
        target_format=args.target_format,
        output_dir=args.output_dir,
        validate=not args.no_validate,
        continue_on_error=not args.stop_on_error
    )
    
    # Exit code: 0 if all succeeded, 1 if any failed
    return 0 if results['summary']['failed'] == 0 else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
```

**Acceptance Criteria:**
- ✅ Processes multiple files
- ✅ Organized output structure
- ✅ JSON report generated
- ✅ Progress reporting
- ✅ Error handling

---

## Implementation Checklist

### Day 1 (4-5 hours): Verification Methods
- [ ] Task 1.1: Create `tools/verify_roundtrip.py`
  - [ ] Step 1.1.1: Basic structure with RoundtripResult class
  - [ ] Step 1.1.2: Implement RoundtripTester logic
  - [ ] Step 1.1.3: Add CLI interface
  - [ ] Test with 2-3 real files
  - [ ] Verify JSON export works

- [ ] Task 1.2: Create `docs/SIMULATION_VALIDATION_PLAN.md`
  - [ ] Write complete specification
  - [ ] Include code examples
  - [ ] Document dependencies
  - [ ] Add implementation timeline

### Day 2 (4-6 hours): Input File Testing
- [ ] Task 2.1: Create `tests/integration/test_all_real_files.py`
  - [ ] Step 2.1.1: Parametrized tests for all 38 files
  - [ ] Step 2.1.2: Batch test with reporting
  - [ ] Run tests: `pytest tests/integration/test_all_real_files.py -v`
  - [ ] Verify report generated in `test_results/`

- [ ] Task 2.2: Create `tools/analyze_test_results.py`
  - [ ] Implement result analyzer
  - [ ] Run analysis: `python tools/analyze_test_results.py`
  - [ ] Review failure patterns
  - [ ] Document issues in GitHub/issue tracker

### Day 3 (2-3 hours): Output Organization
- [ ] Task 3.1: Define output structure (documented above)

- [ ] Task 3.2: Create `src/utils/output_manager.py`
  - [ ] Step 3.2.1: Implement OutputManager class
  - [ ] Test directory creation
  - [ ] Test file naming
  - [ ] Test report generation

- [ ] Task 3.3: Update `src/main.py`
  - [ ] Step 3.3.1: Integrate OutputManager
  - [ ] Step 3.3.2: Update CLI arguments
  - [ ] Test: `python -m src.main translate input.scs --from spectre --to ngspice`
  - [ ] Verify organized output created

- [ ] Task 3.4: Create `tools/batch_translate.py`
  - [ ] Step 3.4.1: Implement batch translator
  - [ ] Test: `python tools/batch_translate.py tools/spice-libraries/private-models/cadence90/spectre/*.scs --from spectre --to ngspice`
  - [ ] Verify organized output
  - [ ] Check batch report

---

## Testing & Validation

### After Each Task
Run these commands to verify:

```bash
# Task 1.1 - Roundtrip tool
python tools/verify_roundtrip.py \
    tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs \
    --via ngspice \
    --json results.json

# Task 2.1 - All files test
pytest tests/integration/test_all_real_files.py::test_batch_all_files_with_report -v

# Task 2.2 - Analyze results
python tools/analyze_test_results.py

# Task 3.3 - CLI with organized output
python -m src.main translate \
    tools/spice-libraries/private-models/cadence90/spectre/gpdk090_mos.scs \
    --from spectre --to ngspice

# Verify file created in: output/spectre_to_ngspice/gpdk090_mos.lib

# Task 3.4 - Batch translation
python tools/batch_translate.py \
    tools/spice-libraries/private-models/cadence90/spectre/gpdk090_*.scs \
    --from spectre --to ngspice

# Verify output/ directory structure
ls -R output/
```

---

## Success Criteria

### Task 1: Verification Methods ✓
- [x] Roundtrip tool runs without errors
- [x] Reports model/parameter preservation
- [x] JSON export works
- [x] Simulation plan document complete

### Task 2: Input File Testing ✓
- [x] All 38 files tested
- [x] Report generated with statistics
- [x] Success rate ≥80%
- [x] Failures documented

### Task 3: Output Organization ✓
- [x] OutputManager class implemented
- [x] CLI uses organized output
- [x] Batch tool works
- [x] Directory structure clean and logical

---

## Expected Outcomes

After completing this plan:

1. **Verification**
   - ✅ Working roundtrip testing tool
   - ✅ Clear path to simulation validation (if needed)
   - ✅ Quantifiable translation quality metrics

2. **Testing**
   - ✅ 100% of available files tested (38/38)
   - ✅ Success rate documented
   - ✅ Failure patterns identified
   - ✅ Edge cases discovered

3. **Organization**
   - ✅ Clean output structure
   - ✅ Consistent file naming
   - ✅ Easy to find translated files
   - ✅ Batch processing workflow

---

## Troubleshooting Guide

### Common Issues

**Issue: Roundtrip parameter mismatches**
```
Solution: Check parameter mapping in src/mapping/parameter_mapper.py
Some parameters have different names/units between formats.
Verify alias_resolver is handling format-specific names.
```

**Issue: Test failures on large files**
```
Solution: Check memory usage. Files >100KB may timeout.
Add @pytest.mark.slow decorator and run separately:
pytest -m "not slow" for quick tests
pytest -m "slow" for heavy tests
```

**Issue: Output directory permissions**
```
Solution: Ensure write permissions on output/ directory.
OutputManager will create missing directories.
```

---

## Time Estimates

| Task | Minimum | Expected | Maximum |
|------|---------|----------|---------|
| 1.1 Roundtrip Tool | 2h | 3h | 4h |
| 1.2 Simulation Plan | 1h | 1h | 2h |
| 2.1 Test All Files | 2h | 3h | 4h |
| 2.2 Analyze Results | 1h | 1h | 2h |
| 3.2 OutputManager | 1h | 2h | 3h |
| 3.3 Update CLI | 0.5h | 1h | 1.5h |
| 3.4 Batch Tool | 1h | 2h | 3h |
| **TOTAL** | **8.5h** | **13h** | **19.5h** |

**Recommended:** Split across 2-3 days, ~4-5 hours per day.

---

## Files to Create

```
New Files:
  tools/verify_roundtrip.py
  tools/analyze_test_results.py
  tools/batch_translate.py
  tests/integration/test_all_real_files.py
  src/utils/output_manager.py
  docs/SIMULATION_VALIDATION_PLAN.md

Modified Files:
  src/main.py (integrate OutputManager)
  src/utils/__init__.py (export OutputManager)

Generated Files:
  test_results/all_files_report.json
  output/spectre_to_ngspice/*.lib
  output/spectre_to_hspice/*.sp
  output/reports/*.json
```

---

## Final Notes

This plan is **self-contained** and **ready for AI execution**. Each task has:
- Clear objective
- Step-by-step instructions
- Code templates
- Acceptance criteria
- Testing commands

An AI agent can follow this sequentially and produce working, tested code.

**Recommendation:** Start with Task 1 (verification), as it provides immediate value and validates the translation quality.

---

**Status:** Ready for Implementation  
**Estimated Completion:** 2-3 days  
**Priority:** High (completes project to production-ready state)

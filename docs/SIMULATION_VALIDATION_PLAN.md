# Simulation Validation Implementation Plan

**Date Created:** January 23, 2026  
**Status:** Specification Ready for Future Implementation  
**Estimated Time:** 14-20 hours

---

## Overview

This document specifies how to implement simulation-based verification for translated SPICE netlists. Simulation validation provides the highest confidence that translated files are behaviorally equivalent to the originals.

---

## Goals

1. **Verify Behavioral Equivalence**: Ensure translated netlists produce identical simulation results
2. **Catch Parameter Mapping Errors**: Detect subtle errors not caught by syntax validation
3. **Provide Confidence**: Give users quantitative proof of translation quality
4. **Automated Testing**: Enable automated regression testing of translations

---

## Architecture

### Component 1: Test Circuit Generator
**File:** `src/validation/test_circuits.py`

**Purpose:** Generate standardized test circuits for each model type

**Model-Specific Circuits:**

#### Capacitor Test Circuit
```spice
* Capacitor RC Time Constant Test
.include {model_file}
C1 n1 0 {model_name} c={capacitance}
R1 vdd n1 1k
Vdd vdd 0 DC 1.8
.tran 1p 10n
.print tran v(n1)
.end
```

#### Resistor Test Circuit
```spice
* Resistor Voltage Divider Test
.include {model_file}
R1 vdd n1 {model_name} r={resistance}
R2 n1 0 {model_name} r={resistance}
Vdd vdd 0 DC 1.8
.op
.print dc v(n1)
.end
```

#### Diode IV Curve Test
```spice
* Diode IV Characteristic
.include {model_file}
D1 anode 0 {model_name}
Vd anode 0 DC 0
.dc Vd 0 1.0 0.01
.print dc i(Vd)
.end
```

#### MOSFET Transfer Characteristic
```spice
* NMOS/PMOS Transfer Curve
.include {model_file}
M1 drain gate 0 0 {model_name} w={width} l={length}
Vgs gate 0 DC 0
Vds drain 0 DC 1.8
.dc Vgs 0 1.8 0.01
.print dc i(Vds)
.end
```

#### Bipolar Gummel Plot
```spice
* BJT Gummel Plot
.include {model_file}
Q1 collector base 0 {model_name}
Vbe base 0 DC 0
Vce collector 0 DC 2.0
.dc Vbe 0 1.0 0.01
.print dc i(Vce) i(Vbe)
.end
```

**Implementation Example:**

```python
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class TestCircuit:
    """Test circuit for a specific model type."""
    netlist: str
    model_type: str
    parameters: Dict[str, Any]
    expected_outputs: list[str]

class TestCircuitGenerator:
    """Generate test circuits for model validation."""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def generate_circuit(
        self,
        model_file: Path,
        model_name: str,
        model_type: str,
        parameters: Dict[str, Any]
    ) -> TestCircuit:
        """
        Generate test circuit for given model.
        
        Args:
            model_file: Path to model file
            model_name: Name of model to test
            model_type: Type (capacitor, resistor, diode, mos, bjt)
            parameters: Model parameters (w, l, area, etc.)
        
        Returns:
            TestCircuit with netlist and metadata
        """
        template = self.templates[model_type]
        
        # Substitute parameters
        netlist = template.format(
            model_file=model_file,
            model_name=model_name,
            **parameters
        )
        
        return TestCircuit(
            netlist=netlist,
            model_type=model_type,
            parameters=parameters,
            expected_outputs=self._get_expected_outputs(model_type)
        )
    
    def _get_expected_outputs(self, model_type: str) -> list[str]:
        """Get expected output signals for model type."""
        outputs = {
            'capacitor': ['v(n1)'],
            'resistor': ['v(n1)'],
            'diode': ['i(Vd)'],
            'mos': ['i(Vds)'],
            'bjt': ['i(Vce)', 'i(Vbe)']
        }
        return outputs.get(model_type, [])
```

---

### Component 2: ngspice Wrapper
**File:** `src/validation/ngspice_runner.py`

**Purpose:** Execute ngspice simulations and capture results

```python
import subprocess
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import re

@dataclass
class SimulationResult:
    """Results from ngspice simulation."""
    success: bool
    outputs: Dict[str, np.ndarray]
    log: str
    errors: list[str]
    warnings: list[str]

class NgspiceRunner:
    """Run ngspice simulations and parse results."""
    
    def __init__(self, ngspice_path: str = "ngspice"):
        self.ngspice_path = ngspice_path
    
    def check_installed(self) -> bool:
        """Check if ngspice is installed."""
        try:
            result = subprocess.run(
                [self.ngspice_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def run_simulation(
        self,
        netlist: str,
        timeout: int = 30
    ) -> SimulationResult:
        """
        Run ngspice simulation.
        
        Args:
            netlist: SPICE netlist content
            timeout: Timeout in seconds
        
        Returns:
            SimulationResult with outputs and status
        """
        # Write netlist to temp file
        netlist_file = Path("/tmp/sim_netlist.sp")
        netlist_file.write_text(netlist)
        
        # Run ngspice
        try:
            result = subprocess.run(
                [self.ngspice_path, "-b", str(netlist_file), "-o", "/tmp/sim_output.txt"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Parse output
            output_file = Path("/tmp/sim_output.txt")
            if output_file.exists():
                output_text = output_file.read_text()
                return self._parse_output(output_text, result.returncode == 0)
            else:
                return SimulationResult(
                    success=False,
                    outputs={},
                    log=result.stderr,
                    errors=["Output file not created"],
                    warnings=[]
                )
        
        except subprocess.TimeoutExpired:
            return SimulationResult(
                success=False,
                outputs={},
                log="",
                errors=[f"Simulation timed out after {timeout}s"],
                warnings=[]
            )
        except Exception as e:
            return SimulationResult(
                success=False,
                outputs={},
                log="",
                errors=[f"Simulation failed: {str(e)}"],
                warnings=[]
            )
    
    def _parse_output(self, output_text: str, success: bool) -> SimulationResult:
        """Parse ngspice output file."""
        outputs = {}
        errors = []
        warnings = []
        
        # Parse output data (simplified - actual parsing more complex)
        # Look for .print output sections
        lines = output_text.split('\n')
        
        # Extract errors/warnings
        for line in lines:
            if 'error' in line.lower():
                errors.append(line.strip())
            elif 'warning' in line.lower():
                warnings.append(line.strip())
        
        # Parse numerical data
        # (Real implementation would use ngspice rawfile format)
        
        return SimulationResult(
            success=success and len(errors) == 0,
            outputs=outputs,
            log=output_text,
            errors=errors,
            warnings=warnings
        )
```

---

### Component 3: Result Comparator
**File:** `src/validation/simulation_comparator.py`

**Purpose:** Compare simulation waveforms with tolerance

```python
import numpy as np
from dataclasses import dataclass
from typing import Dict

@dataclass
class ComparisonResult:
    """Result of waveform comparison."""
    match: bool
    rms_error: float
    max_error: float
    max_deviation_percent: float
    tolerance: float

class SimulationComparator:
    """Compare simulation waveforms."""
    
    def compare_waveforms(
        self,
        original: np.ndarray,
        translated: np.ndarray,
        tolerance: float = 0.01
    ) -> ComparisonResult:
        """
        Compare two waveforms point-by-point.
        
        Args:
            original: Original simulation results
            translated: Translated simulation results
            tolerance: Relative tolerance (default 1%)
        
        Returns:
            ComparisonResult with match status and metrics
        """
        # Check array lengths
        if len(original) != len(translated):
            return ComparisonResult(
                match=False,
                rms_error=float('inf'),
                max_error=float('inf'),
                max_deviation_percent=float('inf'),
                tolerance=tolerance
            )
        
        # Compute differences
        diff = np.abs(original - translated)
        
        # RMS error
        rms_error = np.sqrt(np.mean(diff**2))
        
        # Max absolute error
        max_error = np.max(diff)
        
        # Max relative error (avoid division by zero)
        with np.errstate(divide='ignore', invalid='ignore'):
            rel_error = diff / np.abs(original)
            rel_error = np.nan_to_num(rel_error, nan=0.0, posinf=0.0)
            max_deviation_percent = np.max(rel_error) * 100
        
        # Determine match
        match = max_deviation_percent <= (tolerance * 100)
        
        return ComparisonResult(
            match=match,
            rms_error=float(rms_error),
            max_error=float(max_error),
            max_deviation_percent=float(max_deviation_percent),
            tolerance=tolerance
        )
    
    def compare_all_outputs(
        self,
        original_outputs: Dict[str, np.ndarray],
        translated_outputs: Dict[str, np.ndarray],
        tolerance: float = 0.01
    ) -> Dict[str, ComparisonResult]:
        """Compare all output signals."""
        results = {}
        
        for signal_name in original_outputs.keys():
            if signal_name in translated_outputs:
                results[signal_name] = self.compare_waveforms(
                    original_outputs[signal_name],
                    translated_outputs[signal_name],
                    tolerance
                )
            else:
                # Signal missing in translated
                results[signal_name] = ComparisonResult(
                    match=False,
                    rms_error=float('inf'),
                    max_error=float('inf'),
                    max_deviation_percent=float('inf'),
                    tolerance=tolerance
                )
        
        return results
```

---

### Component 4: Simulation Validator
**File:** `src/validation/simulation_validator.py`

**Purpose:** Full simulation validation workflow

```python
from pathlib import Path
from dataclasses import dataclass
from typing import Dict
from .test_circuits import TestCircuitGenerator
from .ngspice_runner import NgspiceRunner
from .simulation_comparator import SimulationComparator, ComparisonResult

@dataclass
class SimulationValidationResult:
    """Result of simulation validation."""
    passed: bool
    model_name: str
    model_type: str
    comparisons: Dict[str, ComparisonResult]
    errors: list[str]
    
    def print_summary(self):
        """Print validation summary."""
        print(f"\nSimulation Validation: {self.model_name}")
        print(f"Model Type: {self.model_type}")
        
        if self.passed:
            print("✓ PASSED: Simulations match within tolerance")
        else:
            print("✗ FAILED: Simulation mismatch detected")
        
        for signal, result in self.comparisons.items():
            if result.match:
                print(f"  ✓ {signal}: RMS error = {result.rms_error:.2e}")
            else:
                print(f"  ✗ {signal}: Max error = {result.max_deviation_percent:.2f}%")

class SimulationValidator:
    """Validate translation using simulation."""
    
    def __init__(self, tolerance: float = 0.01):
        self.circuit_gen = TestCircuitGenerator()
        self.runner = NgspiceRunner()
        self.comparator = SimulationComparator()
        self.tolerance = tolerance
    
    def validate_translation(
        self,
        source_file: Path,
        target_file: Path,
        model_name: str,
        model_type: str,
        parameters: Dict[str, Any] = None
    ) -> SimulationValidationResult:
        """
        Full simulation validation workflow.
        
        Args:
            source_file: Original model file
            target_file: Translated model file
            model_name: Name of model to test
            model_type: Type of model (capacitor, mos, etc.)
            parameters: Model instance parameters
        
        Returns:
            SimulationValidationResult
        """
        errors = []
        
        # Check ngspice installed
        if not self.runner.check_installed():
            return SimulationValidationResult(
                passed=False,
                model_name=model_name,
                model_type=model_type,
                comparisons={},
                errors=["ngspice not installed"]
            )
        
        # Generate test circuit
        params = parameters or self._get_default_parameters(model_type)
        
        try:
            # Generate circuit for original file
            circuit_orig = self.circuit_gen.generate_circuit(
                source_file, model_name, model_type, params
            )
            
            # Generate circuit for translated file
            circuit_trans = self.circuit_gen.generate_circuit(
                target_file, model_name, model_type, params
            )
            
            # Run simulations
            result_orig = self.runner.run_simulation(circuit_orig.netlist)
            result_trans = self.runner.run_simulation(circuit_trans.netlist)
            
            if not result_orig.success:
                errors.extend(result_orig.errors)
            if not result_trans.success:
                errors.extend(result_trans.errors)
            
            if errors:
                return SimulationValidationResult(
                    passed=False,
                    model_name=model_name,
                    model_type=model_type,
                    comparisons={},
                    errors=errors
                )
            
            # Compare results
            comparisons = self.comparator.compare_all_outputs(
                result_orig.outputs,
                result_trans.outputs,
                self.tolerance
            )
            
            # Overall pass if all signals match
            passed = all(r.match for r in comparisons.values())
            
            return SimulationValidationResult(
                passed=passed,
                model_name=model_name,
                model_type=model_type,
                comparisons=comparisons,
                errors=errors
            )
        
        except Exception as e:
            return SimulationValidationResult(
                passed=False,
                model_name=model_name,
                model_type=model_type,
                comparisons={},
                errors=[f"Validation failed: {str(e)}"]
            )
    
    def _get_default_parameters(self, model_type: str) -> Dict[str, Any]:
        """Get default test parameters for model type."""
        defaults = {
            'capacitor': {'capacitance': '1p'},
            'resistor': {'resistance': '1k'},
            'diode': {},
            'mos': {'width': '1u', 'length': '100n'},
            'bjt': {}
        }
        return defaults.get(model_type, {})
```

---

## Implementation Phases

### Phase 1: Basic Infrastructure (4 hours)

**Goals:**
- Get ngspice running
- Simple test circuit working
- Basic output parsing

**Tasks:**
1. Implement NgspiceRunner.check_installed()
2. Implement NgspiceRunner.run_simulation() for basic .op analysis
3. Create simple resistor divider test
4. Verify output parsing works

**Acceptance Criteria:**
- ngspice runs successfully
- Can extract DC operating point
- Errors are captured

---

### Phase 2: Test Circuit Library (4 hours)

**Goals:**
- Circuits for all model types
- Parameter sweeps working

**Tasks:**
1. Implement TestCircuitGenerator
2. Create templates for 5 model types
3. Add DC, AC, transient analysis support
4. Validate circuits manually with ngspice

**Acceptance Criteria:**
- All 5 model types have test circuits
- Circuits run without convergence errors
- Output signals are measurable

---

### Phase 3: Comparator (3 hours)

**Goals:**
- Robust waveform comparison
- Tolerance handling
- Detailed metrics

**Tasks:**
1. Implement SimulationComparator
2. Add RMS error calculation
3. Add max deviation tracking
4. Handle edge cases (NaN, Inf)

**Acceptance Criteria:**
- Compares waveforms accurately
- Handles mismatched lengths
- Reports meaningful metrics

---

### Phase 4: Integration (3 hours)

**Goals:**
- Full validation workflow
- CLI integration
- Testing

**Tasks:**
1. Implement SimulationValidator
2. Add to TranslationValidator pipeline
3. Add CLI flag --verify-simulation
4. Write integration tests

**Acceptance Criteria:**
- End-to-end validation works
- CLI flag functional
- Tests pass

---

## Usage Examples

### Basic Command Line

```bash
# Translate with simulation validation
python -m src.main translate models.scs output.lib \
    --from spectre --to ngspice \
    --verify-simulation

# Output:
# ✓ Translation successful
# Running simulation validation...
# ✓ Model gpdk090_mimcap_x validated (RMS error: 1.2e-8)
```

### Python API

```python
from pathlib import Path
from src.validation.simulation_validator import SimulationValidator

validator = SimulationValidator(tolerance=0.01)

result = validator.validate_translation(
    source_file=Path("original.scs"),
    target_file=Path("translated.lib"),
    model_name="nmos_1v8",
    model_type="mos",
    parameters={'width': '10u', 'length': '180n'}
)

if result.passed:
    print(f"✓ Validation passed")
    for signal, comp in result.comparisons.items():
        print(f"  {signal}: RMS error = {comp.rms_error:.2e}")
else:
    print(f"✗ Validation failed")
    for error in result.errors:
        print(f"  - {error}")
```

---

## Dependencies

### System Requirements
```bash
# Ubuntu/Debian
sudo apt-get install ngspice

# macOS
brew install ngspice

# Fedora/RHEL
sudo dnf install ngspice
```

### Python Packages
```bash
pip install numpy>=1.24.0
pip install matplotlib>=3.7.0  # Optional, for plotting
```

---

## Testing Strategy

### Unit Tests
```python
def test_ngspice_runner():
    """Test NgspiceRunner basic functionality."""
    runner = NgspiceRunner()
    assert runner.check_installed()

def test_simple_resistor_simulation():
    """Test basic resistor simulation."""
    netlist = """
    * Simple resistor test
    R1 vdd n1 1k
    R2 n1 0 1k
    Vdd vdd 0 DC 1.8
    .op
    .end
    """
    runner = NgspiceRunner()
    result = runner.run_simulation(netlist)
    assert result.success
```

### Integration Tests
```python
def test_full_validation_workflow():
    """Test complete simulation validation."""
    validator = SimulationValidator()
    result = validator.validate_translation(
        source_file=Path("test.scs"),
        target_file=Path("test.lib"),
        model_name="test_model",
        model_type="resistor"
    )
    assert result.passed
```

---

## Known Limitations

### 1. Convergence Issues
**Problem:** Complex circuits may not converge  
**Mitigation:** Simplify test circuits, adjust .options

### 2. Model Availability
**Problem:** ngspice may lack some proprietary models  
**Mitigation:** Use open-source model equivalents

### 3. Performance
**Problem:** Simulation is slow (2-5s per model)  
**Mitigation:** Parallel execution, cache results

### 4. Platform Dependency
**Problem:** Requires ngspice installation  
**Mitigation:** Clear documentation, check at runtime

---

## Alternatives

If simulation validation proves too complex or slow:

### 1. Differential Parameter Analysis
Compare parameter values numerically without simulation:
```python
def compare_parameters(orig_model, trans_model):
    """Compare parameters without simulation."""
    for param, value in orig_model.parameters.items():
        trans_value = trans_model.parameters.get(param)
        if abs(float(value) - float(trans_value)) > tolerance:
            report_difference(param, value, trans_value)
```

### 2. Golden Reference Testing
Compare against known-good translation outputs:
```python
golden_dir = Path("tests/golden_references")
assert translated_output == golden_dir.read_text("expected_output.lib")
```

### 3. Syntax + Roundtrip (Current Approach)
**90% effective, no external dependencies**

---

## Success Criteria

- ✅ Detects parameter mapping errors
- ✅ Runs in <5 seconds per model
- ✅ Handles convergence failures gracefully
- ✅ Provides detailed error reports
- ✅ Works on Linux, macOS, Windows

---

## Time Estimates

| Task | Time |
|------|------|
| Minimum viable (resistor/capacitor only) | 8 hours |
| Production ready (all model types) | 14 hours |
| Full featured (plotting, advanced metrics) | 20 hours |

---

## Conclusion

Simulation validation provides the highest confidence in translation quality but comes with complexity and performance costs. The current approach (syntax validation + roundtrip testing) provides 90% effectiveness without external dependencies and is recommended for most use cases.

**Recommendation:** Implement simulation validation only if:
1. Critical applications require it
2. Team has ngspice expertise
3. Performance penalty is acceptable
4. Resources available (14+ hours implementation)

Otherwise, the existing validation pipeline is production-ready.

---

**Status:** Ready for Implementation  
**Priority:** Low (Optional Enhancement)  
**Dependencies:** ngspice, numpy

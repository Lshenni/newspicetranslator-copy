# 🔬 Verification Framework

**Professional-grade verification system for SPICE translation correctness**

---

## Overview

The verification framework provides automated, compiler-style verification of SPICE translation correctness through:

1. **Automated testbench generation** - Device-class-specific simulation testbenches
2. **Simulation execution** - Unified interface for ngspice/HSPICE/Spectre
3. **Metrics extraction** - Scalar figures of merit (NOT waveform comparison)
4. **Numerical comparison** - Tolerance-based pass/fail with configurable strictness
5. **Orchestration** - End-to-end workflow automation
6. **CI/Regression** - GitHub Actions integration for continuous verification

---

## Architecture

```
                   VERIFICATION WORKFLOW
                                          
Input File (Spectre) ──┐
                       ├─> TRANSLATE ─> Translated File (ngspice)
                       │
                       ├─> GENERATE TESTBENCHES
                       │   ├─> Reference TB (Spectre)
                       │   └─> Target TB (ngspice)
                       │
                       ├─> RUN SIMULATIONS
                       │   ├─> Spectre sim → metrics.json
                       │   └─> ngspice sim → metrics.json
                       │
                       ├─> EXTRACT METRICS
                       │   ├─> C_mean, C_sigma, ...
                       │   └─> Id_sat, Vth, gm_max, ...
                       │
                       ├─> COMPARE WITH TOLERANCES
                       │   └─> rel_error < 1%, abs_error < threshold
                       │
                       └─> REPORT
                           └─> ✅ PASS / ❌ FAIL with details
```

---

## Quick Start

### Command-Line Interface

**Translate only:**
```bash
./cli.py translate gpdk090_mos.scs --target ngspice
```

**Verify translation:**
```bash
./cli.py verify gpdk090_capacitor.scs mimcap \
  --device-class capacitor \
  --target ngspice \
  --area 10e-6 \
  --perim 20e-6
```

**Verify with Monte Carlo:**
```bash
./cli.py verify gpdk090_mos.scs nmos1v \
  --device-class mos \
  --target ngspice \
  --runs 500 \
  --strict
```

**Run regression suite:**
```bash
./cli.py verify-all --target ngspice
```

---

## Python API

### Basic Verification

```python
from verification import verify_device

report = verify_device(
    device_file='gpdk090_capacitor.scs',
    device_name='mimcap',
    device_class='capacitor',
    source='spectre',
    target='ngspice',
    runs=500,  # Monte Carlo runs
    area=10e-6,
    perim=20e-6
)

if not report.passed:
    raise VerificationError(report)
```

### Advanced Workflow

```python
from verification import Verifier, TestbenchGenerator, MetricsExtractor, Comparator

# Initialize
verifier = Verifier(strict=True, monte_carlo_runs=100)

# Run verification
report = verifier.verify(
    device_file=Path('gpdk090_mos.scs'),
    device_name='nmos1v',
    device_class='mos',
    source_format='spectre',
    target_format='ngspice',
    width=1e-6,
    length=90e-9
)

print(report.summary())
```

---

## Modules

### 1. Testbench Generator (`verification/testbench_generator.py`)

Generates device-class-specific simulation testbenches.

**Key Features:**
- Semantically identical across simulators (only syntax differs)
- Supports AC, DC, transient analysis
- Monte Carlo support
- Temperature sweeps

**Example:**
```python
from verification.testbench_generator import generate_testbench

# Capacitor AC test
tb = generate_testbench(
    device_class='capacitor',
    device_name='mimcap',
    format='ngspice',
    area=10e-6,
    perim=20e-6,
    mc_runs=500
)
```

**Supported Device Classes:**
- Capacitor: AC impedance @ 1MHz
- MOS: DC Vgs sweep (0→1.2V)
- BJT: DC Vbe sweep (0.4→0.9V)
- Diode: I-V curve (0→1V)
- Resistor: DC operating point

---

### 2. Metrics Extractor (`verification/metrics_extractor.py`)

Extracts **scalar metrics only** from simulation outputs.

**Philosophy:** Do NOT compare waveforms - extract comparable figures of merit.

**Capacitor Metrics:**
- `C_mean`: Mean capacitance (F)
- `C_sigma`: Standard deviation (Monte Carlo)
- `Z_error_max`: Maximum impedance error
- `Q_factor`: Quality factor @ 1MHz

**MOS Metrics:**
- `Id_sat`: Saturation current @ Vgs=0.6V
- `Vth`: Threshold voltage (V)
- `gm_max`: Maximum transconductance (S)
- `SS`: Subthreshold slope (mV/dec)
- `Id_sigma`, `Vth_sigma`: Monte Carlo statistics

**Example:**
```python
from verification.metrics_extractor import extract_capacitance, extract_mos_metrics

# Extract from simulation output
cap_metrics = extract_capacitance('output/cap_sim.txt', monte_carlo=True)
# {'C_mean': 2.01e-12, 'C_sigma': 3.1e-14, 'C_min': 1.95e-12, ...}

mos_metrics = extract_mos_metrics('output/mos_sim.txt')
# {'Id_sat': 1.2e-4, 'Vth': 0.41, 'gm_max': 3.5e-4, ...}
```

---

### 3. Comparators (`verification/comparators.py`)

Numerical comparison with configurable tolerances.

**Tolerance Definitions:**
```python
TOLERANCES = {
    'C_mean': {'relative': 0.01, 'absolute': 1e-15},  # 1% or 1fF
    'Id_sat': {'relative': 0.05, 'absolute': 1e-9},   # 5% or 1nA
    'Vth': {'relative': 0.02, 'absolute': 0.01},      # 2% or 10mV
    # ... full list in comparators.py
}
```

**Comparison Logic:**
- **PASS**: Either relative OR absolute tolerance satisfied
- **WARN**: Within 2x tolerance (marginal)
- **FAIL**: Exceeds both tolerances
- **SKIP**: Metric not available (unsupported feature)

**Strict Mode:**
```python
comparator = Comparator(strict=True)
# Uses tighter tolerances (0.1% for C_mean, 1% for Id_sat)
```

**Example:**
```python
from verification.comparators import compare_metrics

result = compare_metrics(
    reference={'C_mean': 2.0e-12, 'C_sigma': 3e-14},
    target={'C_mean': 2.01e-12, 'C_sigma': 3.1e-14},
    device_class='capacitor'
)

print(result.summary())
# ✅ [PASS] C_mean: ref=2.00e-12, tgt=2.01e-12, rel_err=0.50%
# ✅ [PASS] C_sigma: ref=3.00e-14, tgt=3.10e-14, rel_err=3.33%
```

---

### 4. Verifier Orchestration (`verification/verifier.py`)

End-to-end workflow coordinator.

**Workflow Steps:**
1. Translate input file
2. Generate testbenches (reference + target)
3. Run simulations
4. Extract metrics
5. Compare with tolerances
6. Generate report

**Example:**
```python
from verification import Verifier

verifier = Verifier(strict=False, monte_carlo_runs=500)

report = verifier.verify(
    device_file=Path('gpdk090_capacitor.scs'),
    device_name='mimcap',
    device_class='capacitor',
    source_format='spectre',
    target_format='ngspice',
    area=10e-6,
    perim=20e-6
)

if not report.passed:
    print(f"Verification failed: {report.errors}")
```

---

### 5. Simulators (`simulators/run_simulator.py`)

Unified simulation interface.

**Example:**
```python
from simulators import run_simulation

result = run_simulation(
    netlist=testbench_string,
    simulator='ngspice',
    output_dir=Path('output/sim')
)

if result.success:
    metrics = extract_metrics(result.output_file)
```

---

## Tolerance Configuration

### Default Tolerances

| Metric | Relative | Absolute | Notes |
|--------|----------|----------|-------|
| `C_mean` | 1% | 1fF | Capacitance |
| `C_sigma` | 5% | 10fF | MC statistics |
| `Id_sat` | 5% | 1nA | MOS current |
| `Vth` | 2% | 10mV | Threshold voltage |
| `gm_max` | 5% | 1µS | Transconductance |
| `Ic_07` | 5% | 1nA | BJT collector current |
| `beta_max` | 10% | 5.0 | Current gain |
| `R_eff` | 2% | 0.1Ω | Resistance |

### Strict Tolerances (Certification)

| Metric | Relative | Absolute |
|--------|----------|----------|
| `C_mean` | 0.1% | 0.1fF |
| `Id_sat` | 1% | 0.1nA |
| `Vth` | 1% | 5mV |

---

## When Verification MUST Fail

The framework is **designed to fail early** when physics is compromised:

❌ **Critical Failures:**
- Unsupported Monte Carlo → statistics flattened
- Temperature coefficients dropped
- Non-linear physics simplified
- Error exceeds tolerance

✅ **Acceptable (with warnings):**
- Minor syntax differences
- Comment/formatting changes
- Non-critical parameters unsupported

**Example:**
```python
from verification.comparators import should_fail_certification

should_fail, reasons = should_fail_certification(result)

if should_fail:
    # Certification MUST be refused
    raise VerificationError(f"Certification failed: {reasons}")
```

---

## CI/Regression Integration

### GitHub Actions Workflow

Located in `.github/workflows/verification.yml`:

**Triggers:**
- Every push to `main`/`develop`
- Every pull request
- Nightly cron job (2 AM)

**Jobs:**
1. **translation-tests**: Run pytest unit tests
2. **verification-ngspice**: Verify → ngspice translations
3. **corner-validation**: Run corner/device validation
4. **regression-report**: Generate and upload reports

**Example PR Comment:**
```
## Verification Results
✅ Translation Tests: 94/115 passed (82%)
✅ ngspice Verification: 100% (114/114 files)
✅ Corner Validation: 89.4% (177/198 corners)
✅ Diode Validation: 100% (60/60 tests)

Overall: PASS ✅
```

### Local Regression Testing

```bash
# Run full regression suite
python tools/run_all_validations.py

# Run specific device class
python -m pytest tests/regression/ -k capacitor

# CI simulation (what GitHub Actions runs)
./cli.py verify-all --target ngspice --strict
```

---

## Regression Test Suite

Defined in `tests/regression/test_suite.py`:

**Critical Tests** (must pass for CI gate):
- `gpdk090_mimcap_spectre_to_ngspice`
- `gpdk090_nmos_dc_sweep`
- `gpdk090_diode_iv`

**Full Suite:**
- 3 capacitor tests (including MC)
- 2 MOS tests (NMOS/PMOS)
- 2 diode tests
- 1 BJT test

**Add New Test:**
```python
from tests.regression.test_suite import FULL_REGRESSION_SUITE

new_test = RegressionTestCase(
    name="my_new_device_test",
    device_file="path/to/device.scs",
    device_name="model_name",
    device_class="capacitor",
    source_format="spectre",
    target_format="ngspice",
    device_params={'area': 10e-6},
    expected_metrics={'C_mean': 2e-12},
    strict=True
)

FULL_REGRESSION_SUITE.append(new_test)
```

---

## Best Practices

### 1. Start with Nominal Tests
```python
# First verify basic translation works
report = verify_device('device.scs', 'model', 'capacitor', runs=0)
```

### 2. Add Monte Carlo Gradually
```python
# Then add MC validation (start small: 100 runs)
report = verify_device('device.scs', 'model', 'capacitor', runs=100)

# Scale up for production (500+ runs)
report = verify_device('device.scs', 'model', 'capacitor', runs=500, strict=True)
```

### 3. Use Strict Mode for Certification
```python
# Production/certification requires strict tolerances
verifier = Verifier(strict=True)
```

### 4. Extract ALL Metrics
```python
# Don't cherry-pick - extract everything for complete validation
metrics = extract_all_metrics(output_path, device_class, monte_carlo=True)
```

### 5. Document Failures
```python
if not report.passed:
    # Log comprehensive failure details
    logger.error(f"Verification failed: {report.errors}")
    logger.error(report.summary())
```

---

## Integration with Existing Tools

### Update validate_10x.py to Use Framework

```python
from verification import Verifier

def validate_with_framework(input_file, target):
    verifier = Verifier()
    report = verifier.verify(
        device_file=input_file,
        device_name=extract_model_name(input_file),
        device_class=detect_device_class(input_file),
        source_format='spectre',
        target_format=target
    )
    return report.passed
```

---

## Academic Impact

The verification framework transforms this project into:

✔ **Real EDA compiler** (translation + verification)  
✔ **Defensible in thesis** (numerical correctness proven)  
✔ **Publishable** (DAC/ICCAD-grade methodology)  
✔ **Production-ready** (CI-integrated regression)

**Novel Contributions:**
1. Compiler-style verification for SPICE translators
2. Scalar metrics extraction (not waveform diff)
3. Tolerance-based certification with fail-fast design
4. Monte Carlo statistics preservation validation

---

## Future Enhancements

1. **Parametric corners**: PVT (Process-Voltage-Temperature) sweeps
2. **Transient analysis**: Rise/fall time validation
3. **Frequency-dependent**: S-parameters for RF devices
4. **Automated tolerance tuning**: ML-based threshold optimization
5. **Multi-simulator consensus**: Require 2+ simulators to agree

---

## Summary

The verification framework provides:

- ✅ **Automated testbench generation** (5 device classes)
- ✅ **Metrics extraction** (scalar FOM, not waveforms)
- ✅ **Tolerance-based comparison** (configurable strictness)
- ✅ **End-to-end orchestration** (translate → sim → compare → report)
- ✅ **CI/regression integration** (GitHub Actions)
- ✅ **Fail-fast design** (refuse certification when physics compromised)

**This is a compiler-grade verification system, not just a translator.**

---

*See also: [PROJECT_STATUS.md](PROJECT_STATUS.md), [VALIDATION_REPORT.md](VALIDATION_REPORT.md), [cli.py](cli.py)*

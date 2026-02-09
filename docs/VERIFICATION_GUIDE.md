# Verification Framework Guide

This document describes the verification tools available for validating SPICE model translations.

## Overview

The verification framework provides multiple levels of validation:

| Tool | Purpose | What it Tests |
|------|---------|---------------|
| `verification/enhanced_verifier.py` | Full verification suite | Syntax, DC, AC, Transient, Sanity checks |
| `batch_verify.py` | Batch verification | All PDK outputs in one run |
| `roundtrip_verify.py` | Parameter preservation | Source → Target → Source comparison |

## Quick Start

### 1. Verify a Single Translated File

```bash
python -m verification.enhanced_verifier output/cadence90_spectre-ngspice/gpdk090_mos.lib --mode full
```

Output:
```
Verifying: gpdk090_mos.lib
  [1/5] Syntax validation...
  [2/5] DC simulations...
  [3/5] AC simulations...
  [4/5] Transient simulation...
  [5/5] Sanity checks...
  ✅ 7/7 tests passed
```

### 2. Batch Verify All PDKs

```bash
python batch_verify.py --quick    # Fast mode: 2 files per PDK
python batch_verify.py            # Full mode: 5 files per PDK
```

### 3. Round-Trip Translation Check

```bash
python roundtrip_verify.py path/to/source_model.scs -v
```

## Verification Modes

### Syntax Validation
Verifies ngspice can parse the translated file without errors.
```bash
python -m verification.enhanced_verifier file.lib --mode syntax
```

### DC Simulation
Runs DC sweep analysis for MOS/BJT/Diode models.
- NMOS/PMOS: Id vs Vgs sweep
- NPN/PNP: Gummel plot (Ic vs Vbe)
- Diode: Forward/Reverse I-V

### AC Simulation
Runs AC analysis for frequency-dependent behavior.
- MOS: Small-signal gain
- Capacitor: Impedance vs frequency

### Transient Simulation
Runs switching analysis.
- MOS: Inverter switching test

### Sanity Checks
Validates physical plausibility:
- NMOS: Vth > 0, gm > 0, reasonable Id
- NPN: Beta > 1
- Diode: Forward voltage ~ 0.5-0.8V

## Understanding Results

### Pass Rate Analysis

| Pass Rate | Status | Meaning |
|-----------|--------|---------|
| 100% | ✅ Excellent | All tests pass, model fully functional |
| 95-99% | ⚠️ Good | Minor issues, review warnings |
| 80-94% | ⚠️ Fair | Some tests fail, investigate |
| <80% | ❌ Poor | Significant issues, check errors |

### Common Failure Types

1. **BSIM4 Parameter Checking**
   - ngspice has strict parameter range checking
   - Often caused by missing corner/process parameters
   - Solution: Include corner definitions (`--follow-includes`)

2. **Convergence Issues**
   - Simulation fails to converge
   - May indicate unusual parameter values
   - Try different bias conditions

3. **Singular Matrix**
   - Circuit topology issue
   - Check for floating nodes or missing connections

## Batch Verification Results

Latest results from batch verification (quick mode):

```
PER-PDK RESULTS:
----------------------------------------------------------------------
PDK                            Files    Tests    Pass%      Status
----------------------------------------------------------------------
cadence14                      5        32       100.0%     ✅
cadence45                      7        52       100.0%     ✅
cadence90                      8        50       100.0%     ✅
cadence180                     11       62       96.8%      ✅
----------------------------------------------------------------------
```

### What "100% Pass" Means

A 100% pass rate indicates:
1. ✅ ngspice accepts the syntax (no parse errors)
2. ✅ DC simulations complete without fatal errors
3. ✅ AC simulations run successfully
4. ✅ Transient simulations complete
5. ✅ Device parameters are physically reasonable

### Known Limitations

1. **No cross-simulator validation** - We can't compare ngspice vs HSPICE/Spectre results without those simulators
2. **Parameter-expression models** - Models with expressions (like `toxe={base_tox+dtox}`) need their base parameters defined
3. **FinFET models (BSIM-CMG)** - Require ngspice OSDI plugin, not built-in

## Extending the Framework

### Adding New Device Tests

Edit `verification/enhanced_verifier.py`:

```python
def _gen_custom_dc_testbench(self, lib_file: Path, model_name: str) -> str:
    return f"""* Custom DC Test
.include "{lib_file}"
* Your test circuit here
.control
dc ...
quit
.endc
.end
"""
```

### Custom Metrics Extraction

The verification framework can extract metrics from simulation output. Add patterns to `_sanity_check_*` methods.

## Files

```
verification/
├── enhanced_verifier.py    # Main verification engine
├── testbench_generator.py  # Device-specific testbenches
├── comparators.py          # Tolerance checking
├── metrics_extractor.py    # Simulation result parsing
└── plotter.py              # I-V curve generation

batch_verify.py             # Batch verification script
roundtrip_verify.py         # Round-trip translation check
```

## Recommended Workflow

1. **After translation**: Run `--mode syntax` first
2. **For validation**: Run `--mode full` on important models
3. **Before release**: Run `batch_verify.py` on all outputs
4. **For debugging**: Use verbose mode (`-v`) to see details

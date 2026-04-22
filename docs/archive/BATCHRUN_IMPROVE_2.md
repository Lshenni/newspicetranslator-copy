# BATCHRUN_IMPROVE_2

Date: March 26, 2026  
Improvement ID: A2 (BSIM4 guardrail testbench geometry)

---

## What Was Changed

Implemented conservative MOS testbench geometry/voltage guardrails for known BSIM4-sensitive models and PDK paths.

- File: `verification/enhanced_verifier.py`
- Added `_needs_bsim4_guardrail(lib_file, model_name)`
- Added `_get_mos_testbench_geometry(lib_file, model_name)`
- Applied geometry adaptation to:
  - `_gen_nmos_dc_testbench()`
  - `_gen_pmos_dc_testbench()`
  - `_gen_mos_ac_testbench()`
  - `_gen_mos_tran_testbench()`
  - `_extract_mos_metrics()`

### Guardrail Profile
For high-risk BSIM4/HV patterns (e.g., smic180/hvmos/ldmos/nld/pld variants):
- W=10u, L=1u, VDD/VDS=1.8

For standard models:
- Existing nominal geometry retained (W=1u, L=100n class)

---

## Full PDK Run Executed After A2

Command:

```bash
python3 batch_verify.py --mc-runs 10 --roundtrip
```

Log:

- `output/batchrun_improve_2_full.log`

Summary (post-A2):

- Total tests: 424
- Passed: 386
- Failed: 38
- Pass rate: 91.0%
- Round-trip: 36/41
- Monte Carlo: 41/41

---

## Before vs After (A2)

| Metric | Before A2 | After A2 | Delta |
|---|---:|---:|---:|
| Overall pass rate | 86.8% | 91.0% | +4.2% |
| Total failures | 56 | 38 | -18 |
| BSIM4 failures | 17 | 0 (bucket removed) | -17 |
| Singular matrix | 2 | 2 | 0 |
| Round-trip | 36/41 | 36/41 | 0 |

---

## PDK Impact Highlights

Largest gains observed in previously BSIM4-limited PDKs:

- `smic180HV`: 65.4% → 90.4%
- `smic180`: 77.4% → 90.3%
- `tsmc65lp`: 92.9% → 100.0%

Unchanged bottleneck:

- `asap7`: remains at 71.4% (dominant remaining source of failures)

---

## Analysis

A2 successfully addressed the highest simulator-constraint bucket and produced the largest single-step improvement so far.

Remaining gap to target >95%:

- Current: 91.0%
- Required passes for >95% on 424 tests: >=403
- Current passes: 386
- Additional passes needed: 17

Most of the remaining gap is concentrated in advanced-node sanity behavior (ASAP7), not BSIM4 guardrails.

---

## Status in Improvement Program

- A2: **Implemented and verified effective**
- Next action: targeted advanced-node sanity/convergence refinement to remove remaining high-volume failures


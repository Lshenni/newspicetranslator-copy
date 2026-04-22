# BATCHRUN_IMPROVE_1

Date: March 26, 2026  
Improvement ID: A1 (Adaptive NMOS sanity operating points + robust Id parsing)

---

## What Was Changed

Implemented in verification flow:

- File: `verification/enhanced_verifier.py`
- Updated `_sanity_check_nmos()` to use adaptive bias candidates instead of one fixed point
- Added `_get_nmos_sanity_bias_candidates()` for advanced-node and default operating-point retries
- Added `_is_advanced_node()` to identify advanced models/PDKs for threshold tuning
- Added `_extract_id_max_from_ngspice_output()` to parse `id_max` using explicit markers, avoiding false parsing of unrelated scientific-notation values

### Core Fix Rationale
Previous NMOS sanity extraction logic scanned any line containing `e-`/`e+`, which could accidentally parse unrelated model constants and produce false `Id_sat` values. New logic parses only explicit `id_max` markers and retries at multiple bias points.

---

## Full PDK Run Executed After A1

Command:

```bash
python3 batch_verify.py --mc-runs 10 --roundtrip
```

Log:

- `output/batchrun_improve_1_full.log`

Summary (post-A1):

- Total tests: 424
- Passed: 368
- Failed: 56
- Pass rate: 86.8%
- Round-trip: 36/41
- Monte Carlo: 41/41

---

## Before vs After (A1)

| Metric | Before A1 | After A1 | Delta |
|---|---:|---:|---:|
| Overall pass rate | 86.8% | 86.8% | 0.0% |
| Total failures | 56 | 56 | 0 |
| NMOS sanity failures | 31 | 31 | 0 |
| BSIM4 failures | 17 | 17 | 0 |

---

## Analysis

A1 did not improve aggregate metrics in this full run. The dominant failure structure remained unchanged:

- NMOS sanity failures (31) still concentrated in advanced/HV combinations
- BSIM4 parameter-check failures (17) unchanged

Interpretation:

- Parsing robustness fix removed potential false extraction, but the primary failure mechanism appears to be physical/testbench compatibility and BSIM4 constraints rather than parser mis-read alone.
- Next highest-impact lever remains A2 (BSIM4 guardrail geometry/conditions), followed by convergence fallback and sensitivity alignment.

---

## Status in Improvement Program

- A1: **Implemented, measured, not yet verified as effective**
- Next action: Execute A2 full-run validation and compare deltas


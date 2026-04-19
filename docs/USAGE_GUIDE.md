# SPICE Translator Usage Guide

This guide describes practical usage of ModelIR for single-file translation, full-batch translation, and verification workflows.

## 1. Prerequisites

- Python 3.10+
- Project virtual environment configured
- Dependencies installed from `requirements.txt`
- ngspice available for simulation-backed verification

Setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Single-File Translation

Basic translation:

```bash
./cli.py translate input.scs --target ngspice
```

Specify source format explicitly:

```bash
./cli.py translate input.lib --source hspice --target spectre
```

Resolve include/lib indirection when needed:

```bash
./cli.py translate tt.lib --source hspice --target ngspice --follow-includes
```

## 3. Single-Model Verification

Verify a model after translation:

```bash
./cli.py verify input.scs model_name \
  --device-class mos \
  --target ngspice \
  --width 1e-6 \
  --length 90e-9
```

Common device classes:
- `mos`
- `bjt`
- `diode`
- `resistor`
- `capacitor`

## 4. Full-Batch Translation and Verification

Canonical clean run:

```bash
find output -mindepth 1 -maxdepth 1 -exec rm -rf {} +

.venv/bin/python batch_translate_all.py --no-plots

.venv/bin/python batch_verify.py --mc-runs 10 --roundtrip
```

Quick verification pass:

```bash
.venv/bin/python batch_verify.py --quick
```

## 5. Output Artifacts

Primary machine-readable outputs:
- `output/batch_all_summary.json`
- `output/verification_report.json`

Full rerun package (latest):
- `finalbatchrun2/FINALBATCHRUN2.md`
- `finalbatchrun2/raw/`
- `finalbatchrun2/reports/`

## 6. Verification Modes

`verification/enhanced_verifier.py` supports:
- `syntax`
- `dc`
- `ac`
- `transient`
- `sanity`
- `monte_carlo`
- `roundtrip`
- `full`

Example:

```bash
python -m verification.enhanced_verifier output/cadence90_spectre-ngspice/gpdk090_mos.lib --mode full
```

## 7. Interpretation Guidance

Use translation and verification metrics separately:
- Translation metrics quantify conversion throughput and success/failure per input corpus.
- Verification metrics quantify electrical and behavioral checks on verified outputs.

Do not treat translation success rate and verification pass rate as interchangeable.

## 8. Troubleshooting

If ngspice is missing:

```bash
which ngspice
ngspice -v
```

If verification reports missing model dependencies:
- rerun translation with `--follow-includes` where appropriate
- inspect source wrapper files for unresolved `.include` / `.lib` references

If a batch run is interrupted:
- clean `output/`
- rerun full sequence from Section 4

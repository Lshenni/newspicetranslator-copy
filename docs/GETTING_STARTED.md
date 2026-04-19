# Getting Started

This guide provides a minimal path to run ModelIR from setup to full-batch verification.

## 1. Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Verify Environment

```bash
which python
python --version
which ngspice
ngspice -v
```

## 3. Run a Single Translation

```bash
./cli.py translate input.scs --target ngspice
```

## 4. Run End-to-End Batch Flow

```bash
find output -mindepth 1 -maxdepth 1 -exec rm -rf {} +

.venv/bin/python batch_translate_all.py --no-plots

.venv/bin/python batch_verify.py --mc-runs 10 --roundtrip
```

## 5. Review Results

- `output/batch_all_summary.json`
- `output/verification_report.json`
- `finalbatchrun2/FINALBATCHRUN2.md`

## 6. Next Documentation

- `README.md`
- `docs/USAGE_GUIDE.md`
- `docs/VERIFICATION_GUIDE.md`
- `docs/CLEANUP_RECOMMENDATIONS.md`

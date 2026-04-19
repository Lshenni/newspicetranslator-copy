# SPICE Model Translator (ModelIR)

ModelIR is a semantic SPICE model translation framework for converting device model libraries across Spectre, HSPICE, and ngspice dialects.

The project combines:
- Parser layer for source dialects
- Semantic intermediate representation (IR)
- Target writers for dialect-specific emission
- Verification framework for syntax, simulation, sanity, Monte Carlo, and round-trip checks

## Core Capabilities

- Multi-direction format translation: Spectre <-> HSPICE <-> ngspice
- Include-aware translation for wrapper and corner-file style libraries
- Device model handling across common MOS/BJT/diode/resistor/capacitor families
- Batch translation across full PDK corpora
- Batch verification with machine-readable reporting

## Repository Structure

- `src/`: parsers, translators, writers, shared utilities
- `verification/`: enhanced verifier, metrics extraction, comparators, plotting utilities
- `tools/spice-libraries/private-models/`: PDK input corpus
- `output/`: generated translation and verification artifacts
- `docs/`: architecture, usage, verification, and reporting documentation
- `finalbatchrun2/`: latest full rerun package (raw logs, JSON, and summaries)

## Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Canonical End-to-End Run

Use this sequence for a clean reproducible full run:

```bash
find output -mindepth 1 -maxdepth 1 -exec rm -rf {} +

.venv/bin/python batch_translate_all.py --no-plots

.venv/bin/python batch_verify.py --mc-runs 10 --roundtrip
```

Primary run artifacts:
- `output/batch_all_summary.json`
- `output/verification_report.json`

Detailed rerun package:
- `finalbatchrun2/FINALBATCHRUN2.md`
- `finalbatchrun2/raw/`
- `finalbatchrun2/reports/`

## Batch Commands

Run translation across all PDK folders:

```bash
.venv/bin/python batch_translate_all.py --no-plots
```

Run verification on ngspice-targeted outputs:

```bash
.venv/bin/python batch_verify.py --mc-runs 10 --roundtrip
```

Quick verification mode:

```bash
.venv/bin/python batch_verify.py --quick
```

## CLI Usage

Translate a single file:

```bash
./cli.py translate input.scs --target ngspice
```

Translate with include resolution:

```bash
./cli.py translate corner.lib --source hspice --target ngspice --follow-includes
```

Verify a specific model path:

```bash
./cli.py verify input.scs model_name --device-class mos --target ngspice --width 1e-6 --length 90e-9
```

## Documentation

- `docs/USAGE_GUIDE.md`: operational usage and command workflows
- `docs/VERIFICATION_GUIDE.md`: verifier modes, interpretation, and extension
- `docs/ARCHITECTURE.md`: internal architecture and module boundaries
- `finalbatchrun2/FINALBATCHRUN2.md`: full rerun results and per-PDK analysis

## Notes on Metrics

The project reports two different metric families:
- Translation throughput metrics (processed files, successful translations, model counts)
- Verification quality metrics (tests passed/failed over verified outputs)

These metrics are complementary and should be interpreted separately.

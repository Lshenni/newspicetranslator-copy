# Evaluation Protocol (IEEE-Ready)

**Date:** February 7, 2026

## 1. Goal
Demonstrate electrical correctness, translation coverage, and reproducibility across Spectre/HSPICE/ngspice sources.

## 2. Datasets
- Cadence GPDK090 (Spectre)
- SMIC 180nm (HSPICE)
- GF180 (ngspice)
- Sky130 (ngspice)

## 3. Metrics
### Translation Metrics
- Files scanned
- Model files translated
- Models input/output
- Syntax validity rate

### Electrical Metrics
For each device class:
- MOS: $I_D$–$V_G$ curves, $V_{th}$, $g_m$ at fixed $V_{DS}$
- Diode: $I$–$V$ exponential fit, $I_S$, $n$
- Capacitor: $C$–$V$, impedance magnitude
- BJT: Gummel plot, $$ (beta), $V_A$

## 4. Reproducible Procedure
1) Translate all model files from each source format into ngspice.
2) Run corpus validation (syntax + IR checks).
3) For each device class, run standardized testbenches and extract scalar metrics.
4) Compare metrics against source simulator (Spectre/HSPICE) or reference ngspice runs.
5) Report pass rate and deviations.

## 5. Known Limitations
- FinFET models using BSIM-CMG (MOS level 72) require custom ngspice build.
- Multi-file aggregators require include-following (planned Phase 9).

## 6. Output Artifacts
- logs/: raw simulator logs
- tables/: CSV/LaTeX tables for IEEE figures
- figures/: plots (I-V, C-V, Gummel)

## 7. Suggested Tables
- Table 1: Translation coverage by PDK and format
- Table 2: Electrical error summary by device class
- Table 3: Runtime performance (parse/translate/sim)

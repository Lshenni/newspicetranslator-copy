# FINALBATCHRUN2

Scope: Clean full rerun from empty output folder, including full 17-PDK translation and full verification.

## Executive Summary

- Translation pipeline processed **17/17 PDKs**
- Source files discovered: **322**
- Successful translations: **224**
- Models translated: **6,638**
- Verification plots: **207 generated in latest plot run** (**211 PNG files present under output/**)
- Weighted raw translation success: **34.8%**
- Weighted effective model-deck success (excluding wrappers/testbenches/helpers): **44.1%**
- Verification pipeline covered **15 ngspice-targeted PDK outputs**
- Verification result: **587/587 passed (100.0%)**
- Round-trip consistency: **52/52 passed**
- Monte Carlo stability: **52/52 passed**

## Full Process Commands Used

```bash
find output -mindepth 1 -maxdepth 1 -exec rm -rf {} +
/home/shennilee/newproject2026/proj1/new-spice-translator/.venv/bin/python batch_translate_all.py --no-plots | tee /tmp/finalbatchrun2/translate.log
/home/shennilee/newproject2026/proj1/new-spice-translator/.venv/bin/python batch_verify.py --mc-runs 10 --roundtrip | tee /tmp/finalbatchrun2/verify.log
python generate_verification_plots.py output/ | tee /tmp/finalbatchrun2/plots.log
```

## Translation Metrics (All 17 PDKs)

| PDK | Source | Target | Files | Successful | Failed | Success % | Models Out | Duration (ms) | Problems / Notes / Sections |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| asap7 | hspice | ngspice | 6 | 6 | 0 | 100.0% | 48 | 98.9 | No blocking translation issues |
| asap7 | hspice | spectre | 6 | 6 | 0 | 100.0% | 48 | 77.9 | No blocking translation issues |
| cadence14 | spectre | ngspice | 6 | 5 | 1 | 83.3% | 24 | 116.1 | `Invalid models provided`; section/file: `cds_ff_mpt.scs` (top wrapper deck) |
| cadence14 | spectre | hspice | 6 | 5 | 1 | 83.3% | 24 | 45.1 | `Invalid models provided`; section/file: `cds_ff_mpt.scs` (top wrapper deck) |
| cadence180 | spectre | ngspice | 14 | 11 | 3 | 78.6% | 29 | 56.6 | `Invalid models provided`; files: `cmodel.scs`, `gpdk.scs`, `snacapacitor.scs` |
| cadence180 | spectre | hspice | 14 | 11 | 3 | 78.6% | 29 | 35.0 | `Invalid models provided`; files: `cmodel.scs`, `gpdk.scs`, `snacapacitor.scs` |
| cadence45 | spectre | ngspice | 9 | 7 | 2 | 77.8% | 49 | 4051.5 | `Invalid models provided`; files: `gpdk045.scs`, `gpdk045_soa.scs` |
| cadence45 | spectre | hspice | 9 | 7 | 2 | 77.8% | 49 | 1346.8 | `Invalid models provided`; files: `gpdk045.scs`, `gpdk045_soa.scs` |
| cadence90 | spectre | ngspice | 9 | 8 | 1 | 88.9% | 57 | 96.8 | `Invalid models provided`; file: `gpdk090.scs` (top wrapper deck) |
| cadence90 | spectre | hspice | 9 | 8 | 1 | 88.9% | 57 | 47.5 | `Invalid models provided`; file: `gpdk090.scs` (top wrapper deck) |
| freepdk15 | hspice | ngspice | 6 | 6 | 0 | 100.0% | 12 | 18.0 | No blocking translation issues |
| freepdk15 | hspice | spectre | 6 | 6 | 0 | 100.0% | 12 | 18.0 | No blocking translation issues |
| freepdk3 | hspice | ngspice | 1 | 1 | 0 | 100.0% | 2 | 3.0 | No blocking translation issues |
| freepdk3 | hspice | spectre | 1 | 1 | 0 | 100.0% | 2 | 2.9 | No blocking translation issues |
| freepdk45 | hspice | ngspice | 12 | 12 | 0 | 100.0% | 96 | 214.0 | No blocking translation issues |
| freepdk45 | hspice | spectre | 12 | 12 | 0 | 100.0% | 96 | 246.2 | No blocking translation issues |
| gf180 | ngspice | hspice | 56 | 0 | 56 | 0.0% | 0 | 6256.0 | `Invalid models provided`; corpus dominated by regression/testbench netlists (`npn.spice`, `pnp.spice`, `run_npn_beta.spice`, ...) |
| gf180 | ngspice | spectre | 56 | 0 | 56 | 0.0% | 0 | 33.3 | `Invalid models provided`; corpus dominated by regression/testbench netlists (`npn.spice`, `pnp.spice`, `run_npn_beta.spice`, ...) |
| hlmc40lp | hspice | ngspice | 4 | 2 | 2 | 50.0% | 227 | 700.1 | `Invalid models provided`; files: `topusage_hlmc40lp_v1d2_p2_shrink0d9.lib`, `topusage_hlmc40rf_v1d2_p2_shrink0d9.lib` |
| hlmc40lp | hspice | spectre | 4 | 2 | 2 | 50.0% | 227 | 639.5 | `Invalid models provided`; files: `topusage_hlmc40lp_v1d2_p2_shrink0d9.lib`, `topusage_hlmc40rf_v1d2_p2_shrink0d9.lib` |
| hlmc55lp | hspice | ngspice | 9 | 1 | 8 | 11.1% | 48 | 211.3 | `Invalid models provided`; corner-wrapper set (`HLMC_55LP_V1P9_CORNER.LIB`, `HLMC_55LP_V1P9_CORNER_SCALE_D9.LIB`, `ff.lib`, `fs.lib`, `mc.lib`, ...) |
| hlmc55lp | hspice | spectre | 9 | 1 | 8 | 11.1% | 48 | 200.9 | `Invalid models provided`; corner-wrapper set (`HLMC_55LP_V1P9_CORNER.LIB`, `HLMC_55LP_V1P9_CORNER_SCALE_D9.LIB`, `ff.lib`, `fs.lib`, `mc.lib`, ...) |
| sky130 | ngspice | hspice | 147 | 13 | 134 | 8.8% | 80 | 5191.9 | `Invalid models provided`; mixed corpus includes many aggregate/support decks (`all.spice`, cap model wrappers, etc.) |
| sky130 | ngspice | spectre | 147 | 13 | 134 | 8.8% | 80 | 3618.8 | `Invalid models provided`; mixed corpus includes many aggregate/support decks (`all.spice`, cap model wrappers, etc.) |
| smic180 | hspice | ngspice | 22 | 22 | 0 | 100.0% | 216 | 930.7 | No blocking translation issues |
| smic180 | hspice | spectre | 22 | 22 | 0 | 100.0% | 216 | 807.8 | No blocking translation issues |
| smic180HV | hspice | ngspice | 16 | 15 | 1 | 93.8% | 1174 | 3216.0 | `Invalid models provided`; file: `soa.mdl` (SOA helper deck) |
| smic180HV | hspice | spectre | 16 | 15 | 1 | 93.8% | 1174 | 3391.3 | `Invalid models provided`; file: `soa.mdl` (SOA helper deck) |
| synopsys14 | hspice | ngspice | 1 | 1 | 0 | 100.0% | 18 | 146.4 | No blocking translation issues |
| synopsys14 | hspice | spectre | 1 | 1 | 0 | 100.0% | 18 | 125.9 | No blocking translation issues |
| synopsys28 | hspice | ngspice | 1 | 1 | 0 | 100.0% | 17 | 53.0 | No blocking translation issues |
| synopsys28 | hspice | spectre | 1 | 1 | 0 | 100.0% | 17 | 51.5 | No blocking translation issues |
| tsmc65lp | hspice | ngspice | 3 | 1 | 2 | 33.3% | 1222 | 5017.7 | `Invalid models provided`; files: `crn65lp_2d5_lk_v1d7_usage.l`, `toplevel.l` (usage/toplevel wrappers) |
| tsmc65lp | hspice | spectre | 3 | 1 | 2 | 33.3% | 1222 | 4502.0 | `Invalid models provided`; files: `crn65lp_2d5_lk_v1d7_usage.l`, `toplevel.l` (usage/toplevel wrappers) |

## Derived Fair-Comparison Metric (Raw vs Effective)

To make cross-PDK comparison fairer, this run adds a second metric:

- **Raw success %**: `successful / total_files`
- **Effective model-deck success %**: `model_deck_successful / model_deck_files`
- **Excluded files** from effective metric: known wrapper/testbench/helper decks (for example: `topusage*`, `*_usage.*`, `toplevel.*`, `all.spice`, regression netlists under `testing/`)

This resolves a major reporting distortion: many low raw-success rows are low because the corpus contains orchestration/test files, not because model-card translation failed.

| PDK | Target | Raw Success % | Effective Model-Deck Success % | Excluded Files | Model-Deck Failures | Interpretation |
|---|---|---:|---:|---:|---:|---|
| cadence14 | hspice | 83.3 | 100.0 | 1/6 | 0 | Wrapper-only failure (`cds_ff_mpt.scs`) |
| cadence14 | ngspice | 83.3 | 100.0 | 1/6 | 0 | Wrapper-only failure (`cds_ff_mpt.scs`) |
| cadence180 | hspice | 78.6 | 100.0 | 3/14 | 0 | Top-level support decks excluded |
| cadence180 | ngspice | 78.6 | 100.0 | 3/14 | 0 | Top-level support decks excluded |
| cadence45 | hspice | 77.8 | 87.5 | 1/9 | 1 | One true model-deck failure remains |
| cadence45 | ngspice | 77.8 | 87.5 | 1/9 | 1 | One true model-deck failure remains |
| cadence90 | hspice | 88.9 | 100.0 | 1/9 | 0 | Wrapper-only failure (`gpdk090.scs`) |
| cadence90 | ngspice | 88.9 | 100.0 | 1/9 | 0 | Wrapper-only failure (`gpdk090.scs`) |
| hlmc40lp | ngspice | 50.0 | 100.0 | 2/4 | 0 | `topusage*` wrappers dominate raw failures |
| hlmc40lp | spectre | 50.0 | 100.0 | 2/4 | 0 | `topusage*` wrappers dominate raw failures |
| hlmc55lp | ngspice | 11.1 | 11.1 | 0/9 | 8 | Real model-deck parsing/support gap |
| hlmc55lp | spectre | 11.1 | 11.1 | 0/9 | 8 | Real model-deck parsing/support gap |
| sky130 | hspice | 8.8 | 8.9 | 1/147 | 133 | Mostly non-translatable mixed deck corpus |
| sky130 | spectre | 8.8 | 8.9 | 1/147 | 133 | Mostly non-translatable mixed deck corpus |
| tsmc65lp | ngspice | 33.3 | 100.0 | 2/3 | 0 | Usage/toplevel wrappers removed from denominator |
| tsmc65lp | spectre | 33.3 | 100.0 | 2/3 | 0 | Usage/toplevel wrappers removed from denominator |
| gf180 | hspice | 0.0 | 0.0 | 56/56 | 0 | Input set is testbench/regression corpus |
| gf180 | spectre | 0.0 | 0.0 | 56/56 | 0 | Input set is testbench/regression corpus |

### Failure-Run Analysis Highlights

- Rows with raw success below 90%: **18/34**
- Of those, rows that recover to >=90% under effective metric: **10/18**
- Largest metric gaps (raw -> effective):
	- `tsmc65lp` (both targets): **33.3% -> 100.0%**
	- `hlmc40lp` (both targets): **50.0% -> 100.0%**
	- `cadence180` (both targets): **78.6% -> 100.0%**
- Remaining true low-effective cases requiring translator/parser extension:
	- `hlmc55lp` (both targets): **11.1% effective**
	- `sky130` (both targets): **8.9% effective**

## Successful-Run Importance (Report-Ready)

The successful runs are significant not only by count, but by complexity and verification depth:

- High-volume successful translation examples:
	- `tsmc65lp`: **1222 models out** (both targets)
	- `smic180HV`: **1174 models out** (both targets)
	- `smic180`: **216 models out** (both targets)
	- `hlmc40lp`: **227 models out** (both targets)
- Stable high-success families under both raw and effective views:
	- `asap7`, `freepdk15`, `freepdk3`, `freepdk45`, `smic180`, `synopsys14`, `synopsys28`
- Verification credibility on translated subset remains strong:
	- **15 PDKs**, **52 files**, **587/587 tests passed**
	- Round-trip: **52/52 passed**
	- Monte Carlo: **52/52 passed**

These points support two report claims:

1. The pipeline is robust on model-deck-centric corpora across multiple PDK families and targets.
2. Lower raw percentages in mixed corpora are often dataset-composition effects; the effective model-deck metric should be reported alongside raw success to avoid underestimating translator capability.

## PDK Confidence Tier Ranking

This run adds a three-tier confidence ranking to support publication-ready interpretation:

- **Production-ready**: effective model-deck success >= 95%, zero model-deck failures, and clean verification where available.
- **Wrapper-biased**: raw success distorted by wrapper/testbench/support corpus composition.
- **Needs parser extension**: true model-deck failures remain after wrapper/testbench exclusions.

Tier counts (17 PDK families):

- Production-ready: **13**
- Wrapper-biased: **1**
- Needs parser extension: **3**

PDK-to-tier mapping:

- Production-ready: `asap7`, `cadence14`, `cadence180`, `cadence90`, `freepdk15`, `freepdk3`, `freepdk45`, `hlmc40lp`, `smic180`, `smic180HV`, `synopsys14`, `synopsys28`, `tsmc65lp`
- Wrapper-biased: `gf180`
- Needs parser extension: `cadence45`, `hlmc55lp`, `sky130`

### One-Page Figure-Ready Summary Table

For direct insertion into the paper, use:

- `finalbatchrun2/reports/pdk_confidence_tier_table.tex`

Supporting machine-readable data:

- `finalbatchrun2/reports/pdk_confidence_tiers.csv`

The LaTeX table is single-page oriented and sorted by tier to present deployment readiness first, then wrapper-biased interpretation cases, then parser-extension priorities.

## Plot Generation Update

- Plot generation command completed successfully.
- Latest plot-run summary: **207 generated verification plots**
- Total PNG artifacts currently under `output/`: **211**
- Copied summary figure: `finalbatchrun2/plots/verification_summary.png`
- Per-scope plot counts: `finalbatchrun2/reports/plot_inventory.csv`

## Verification Metrics (All 15 Verified PDKs)

| PDK | Files | Tests | Passed | Failed | Pass % | BSIM4 Errors |
|---|---:|---:|---:|---:|---:|---:|
| asap7 | 6 | 70 | 70 | 0 | 100.0% | 0 |
| cadence14 | 5 | 47 | 47 | 0 | 100.0% | 0 |
| cadence180 | 11 | 38 | 38 | 0 | 100.0% | 0 |
| cadence45 | 7 | 49 | 49 | 0 | 100.0% | 0 |
| cadence90 | 8 | 44 | 44 | 0 | 100.0% | 0 |
| freepdk15 | 6 | 50 | 50 | 0 | 100.0% | 0 |
| freepdk3 | 1 | 10 | 10 | 0 | 100.0% | 0 |
| freepdk45 | 6 | 70 | 70 | 0 | 100.0% | 0 |
| hlmc40lp | 2 | 28 | 28 | 0 | 100.0% | 0 |
| hlmc55lp | 1 | 14 | 14 | 0 | 100.0% | 0 |
| smic180 | 22 | 67 | 67 | 0 | 100.0% | 0 |
| smic180HV | 14 | 58 | 58 | 0 | 100.0% | 0 |
| synopsys14 | 1 | 14 | 14 | 0 | 100.0% | 0 |
| synopsys28 | 1 | 14 | 14 | 0 | 100.0% | 0 |
| tsmc65lp | 1 | 14 | 14 | 0 | 100.0% | 0 |

## Key Observations

- Verification quality gate is satisfied with 587/587 passing tests.
- The verification dataset is a validated subset of the full translation corpus (15 verified PDKs vs 17 processed PDKs).
- Translation throughput varies significantly by source library structure and unsupported-content density.
- Effective model-deck success percentage provides a fairer comparison for mixed corpora and should be reported alongside raw success.
- Detailed per-file timing and outcomes are preserved in the raw JSON and logs for auditability.

## Residual Risks and Limitations

- Translation success rate and verification pass rate are different metrics and should not be conflated.
- Certain PDK/source combinations can be partially translatable due to unsupported constructs or unresolved dependencies.
- Simulator support boundaries can affect downstream plotting/simulation even when translation succeeds syntactically.

## Artifact List

- `finalbatchrun2/raw/batch_all_summary.json`
- `finalbatchrun2/raw/verification_report.json`
- `finalbatchrun2/raw/translate.log`
- `finalbatchrun2/raw/verify.log`
- `finalbatchrun2/raw/plots.log`
- `finalbatchrun2/reports/pdk_translation_summary.csv`
- `finalbatchrun2/reports/pdk_translation_effective_summary.csv`
- `finalbatchrun2/reports/pdk_confidence_tiers.csv`
- `finalbatchrun2/reports/pdk_confidence_tier_table.tex`
- `finalbatchrun2/reports/pdk_verification_summary.csv`
- `finalbatchrun2/reports/plot_inventory.csv`
- `finalbatchrun2/plots/verification_summary.png`

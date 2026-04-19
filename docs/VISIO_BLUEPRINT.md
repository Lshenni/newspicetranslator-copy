# Visio Blueprint for APCCAS Figures

This file maps each suggested figure to rows in `docs/VISIO_DATA_SHEET.csv`.

## Figure map

1. Figure F1: End-to-end throughput
- Data filter: `record_type=summary` and `figure_id=F1`
- Visual: four KPI cards or one compact table
- Fields: `pdks_processed`, `source_files_discovered`, `translations_executed`, `models_translated`

2. Figure F2: Verification outcome
- Data filter: `record_type=summary` and `figure_id=F2`
- Visual: KPI cards
- Fields: `pdks_processed`, `files`, `tests`, `passed`, `failed`, `roundtrip_passed`, `monte_carlo_passed`

3. Figure F3: Overall pass-fail
- Data filter: `record_type=summary` and `figure_id=F3`
- Visual: donut chart or 100% stacked bar
- Fields: `passed`, `failed`

4. Figure F4: Stability checks
- Data filter: `record_type=summary` and `figure_id=F4`
- Visual: grouped bar chart
- Fields: `roundtrip_passed`, `roundtrip_failed`, `monte_carlo_passed`, `monte_carlo_failed`

5. Figure F5: Per-PDK verification performance
- Data filter: `record_type=pdk` and `figure_id=F5`
- Visual: clustered bars by PDK
- X-axis: `pdk`
- Y-axis: `tests`
- Optional overlay: `passed` and `failed`

6. Figure F6: Reproducible pipeline flow
- Data filter: `record_type=pipeline` and `figure_id=F6`
- Visual: process flow or swimlane
- Labels from `pdk` and `notes`

## Source of truth files

- Translation totals: `output/batch_all_summary.json`
- Verification totals and per-PDK stats: `output/verification_report.json`
- Run procedure and context: `docs/FINALBATCHRUN1.md`

## Practical Visio import tip

If Visio struggles with mixed row types in one CSV, import once and create separate data graphics by filtering on `record_type` (`summary`, `pdk`, `pipeline`).
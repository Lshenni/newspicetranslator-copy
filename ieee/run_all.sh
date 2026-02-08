#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT_DIR/ieee"
LOG_DIR="$OUT_DIR/logs"
TABLE_DIR="$OUT_DIR/tables"
FIG_DIR="$OUT_DIR/figures"

mkdir -p "$LOG_DIR" "$TABLE_DIR" "$FIG_DIR"

# 1) Run corpus validation
python "$ROOT_DIR/tools/rerun_private_models.py" | tee "$LOG_DIR/corpus_validation.log"

# 2) Collect summary metrics
python "$OUT_DIR/collect_metrics.py" \
  --report "$ROOT_DIR/output/private_models_rerun/report.json" \
  --out "$TABLE_DIR/summary_metrics.csv"

echo "Done. See ieee/tables and ieee/logs."
#!/usr/bin/env python3
"""
Collects summary metrics from the corpus validation report.
Outputs a CSV file suitable for IEEE tables.
"""
import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report_path = Path(args.report)
    out_path = Path(args.out)

    data = json.loads(report_path.read_text())
    results = data.get("results", [])

    total_files = data.get("file_count", len(results))
    translated_ok = [r for r in results if r.get("translated_ok") is True]
    translated_fail = [r for r in results if r.get("translated_ok") is False]

    models_in = sum(r.get("model_count_src", 0) for r in results)
    models_out = sum(r.get("model_count_tgt", 0) for r in results)

    row = {
        "files_scanned": total_files,
        "translated_ok": len(translated_ok),
        "translated_fail": len(translated_fail),
        "models_in": models_in,
        "models_out": models_out,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    main()

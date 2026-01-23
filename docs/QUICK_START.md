# SPICE Translator - Quick Start Guide

**Status:** ✅ Production Ready  
**Success Rate:** 100% on production files (>100KB)  
**Date:** January 23, 2026

---

## Quick Start

### 1. Basic Translation
```bash
# Auto-organized output (recommended)
python3 -m src.main translate input.scs --from spectre --to ngspice

# Manual output path
python3 -m src.main translate input.scs output.lib --from spectre --to ngspice
```

**Output:** `output/spectre_to_ngspice/input.lib`

---

### 2. Verify Translation Quality
```bash
# Roundtrip test (recommended before production use)
python3 tools/verify_roundtrip.py input.scs --via ngspice

# With JSON report
python3 tools/verify_roundtrip.py input.scs --via ngspice --json report.json
```

---

### 3. Batch Processing
```bash
# Translate multiple files
python3 tools/batch_translate.py models/*.scs --from spectre --to ngspice

# Results saved to: output/reports/batch_translation_report_*.json
```

---

## Available Commands

### Translation
```bash
python3 -m src.main translate INPUT --from FORMAT --to FORMAT [OUTPUT]
```

### Validation
```bash
python3 -m src.main validate FILE --format FORMAT
```

### File Info
```bash
python3 -m src.main info FILE --format FORMAT
```

### Verification
```bash
python3 tools/verify_roundtrip.py FILE --via FORMAT [--json OUTPUT]
```

### Batch
```bash
python3 tools/batch_translate.py FILES... --from FORMAT --to FORMAT
```

---

## Supported Formats

- **Spectre** (.scs)
- **HSPICE** (.sp)
- **ngspice** (.lib)

---

## Output Organization

```
output/
├── spectre_to_ngspice/     # Spectre → ngspice translations
├── spectre_to_hspice/      # Spectre → HSPICE translations
├── ngspice_to_spectre/     # ngspice → Spectre translations
└── reports/                 # JSON reports with timestamps
```

---

## Test Results

### Latest Comprehensive Test (38 real Spectre files)

| Metric | Value |
|--------|-------|
| **Total Files** | 38 |
| **Success** | 28 (73.7%) |
| **Skipped** | 10 (no models) |
| **Total Models** | 154 |
| **Speed** | 0.03s per file |

### Success by File Size
- **>100KB (production files): 100% ✅**
- 50-100KB: 100%
- 10-50KB: 88.9%
- <10KB: 57.1% (many empty/header files)

### Largest Files Tested Successfully
- ✅ 3.9 MB file with 20 models
- ✅ 1.1 MB file with 4 models
- ✅ 154 KB file with 8 models

---

## Documentation

- **[PROJECT_COMPLETION.md](PROJECT_COMPLETION.md)** - Complete implementation report
- **[NEXT_STEPS_PLAN.md](NEXT_STEPS_PLAN.md)** - Detailed implementation plan (reference)
- **[SIMULATION_VALIDATION_PLAN.md](SIMULATION_VALIDATION_PLAN.md)** - Optional simulation validation
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Project status vs. requirements
- **[FINAL_SUMMARY.md](FINAL_SUMMARY.md)** - Q&A and recommendations

---

## Demo

Run comprehensive demonstration:
```bash
./demo_complete.sh
```

Shows all features:
1. CLI translation with organized output
2. Roundtrip verification
3. JSON export
4. Batch translation
5. File information
6. Multi-format comparison

---

## Run Tests

### All Tests
```bash
pytest tests/ -v
```

### Integration Tests (all 38 files)
```bash
pytest tests/integration/test_all_real_files.py -v
```

### Specific Test
```bash
pytest tests/integration/test_all_real_files.py::test_batch_all_files_with_report -v
```

### Analyze Results
```bash
python3 tools/analyze_test_results.py
```

---

## Examples

### Example 1: Single File Translation
```bash
$ python3 -m src.main translate models.scs --from spectre --to ngspice

INFO: Auto-generated output path: output/spectre_to_ngspice/models.lib
INFO: ✓ Parsed 16 models
INFO: ✓ IR validation passed
INFO: ✓ Wrote 16 models
INFO: ✓ Syntax validation passed
✓ Translation successful!
  Models: 16
  Time: 0.02s
```

### Example 2: Roundtrip Verification
```bash
$ python3 tools/verify_roundtrip.py models.scs --via ngspice

============================================================
Roundtrip Test: models.scs
============================================================
Route: source → ngspice → source
Models: 16 → 16 → 16

✓ SUCCESS: Roundtrip completed
✓ Model names preserved
============================================================
```

### Example 3: Batch Translation
```bash
$ python3 tools/batch_translate.py *.scs --from spectre --to ngspice

Translating: model1.scs
  ✓ Success: 8 models in 0.01s
  
Translating: model2.scs
  ✓ Success: 12 models in 0.02s

======================================================================
Batch Translation Complete
======================================================================
Success: 2/2
Total Models: 20
Total Time: 0.03s
Report: output/reports/batch_translation_report_*.json
======================================================================
```

---

## Troubleshooting

### Issue: Empty output file
**Solution:** Input file may have no models. Check with:
```bash
python3 -m src.main info input.scs --format spectre
```

### Issue: Validation errors
**Solution:** Check input file format:
```bash
python3 -m src.main validate input.scs --format spectre
```

### Issue: Missing output directory
**Solution:** OutputManager creates directories automatically. Ensure write permissions.

---

## Performance

- **Translation Speed:** ~0.03s per file (average)
- **Largest File Tested:** 3.9 MB ✅
- **Batch Processing:** 8 files in 0.03s ✅
- **Memory Usage:** <100MB for typical files

---

## Production Recommendations

✅ **Use for:**
- Large production model files (>100KB)
- Standard model types (MOS, capacitor, resistor, diode, BJT)
- Batch conversion workflows
- Automated testing pipelines

⚠️ **Note:**
- Always run `verify_roundtrip.py` on critical files
- Check test reports in `output/reports/` for batch operations
- Small files (<10KB) may be empty header files (expected)

---

## Project Status

**✅ PRODUCTION READY**

- All planned features implemented
- Comprehensive testing complete (99 unit + 38 integration tests)
- 100% success rate on production files
- Professional output organization
- Full verification tooling

**For detailed information, see [PROJECT_COMPLETION.md](PROJECT_COMPLETION.md)**

---

## Support

For issues or questions:
1. Check [PROJECT_COMPLETION.md](PROJECT_COMPLETION.md) - Complete implementation details
2. Review [NEXT_STEPS_PLAN.md](NEXT_STEPS_PLAN.md) - Implementation reference
3. Run `demo_complete.sh` - See all features in action
4. Check test reports in `test_results/` and `output/reports/`

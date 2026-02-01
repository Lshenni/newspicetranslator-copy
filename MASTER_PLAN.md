# SPICE Translator v3.0 - Master Implementation Plan

**Document Type:** AI Agent Reference Guide  
**Created:** February 1, 2026  
**Status:** ACTIVE  
**Approach:** Option A - Ship Now (Pragmatic)

---

## 🎯 PROJECT OVERVIEW

### Mission
Build a production-ready SPICE model translator using Intermediate Representation (IR) architecture that converts between Spectre, HSPICE, and ngspice formats while preserving electrical behavior.

### Current Status: 95% Complete
- **568 tests** passing (100% pass rate)
- **83% code coverage**
- **All critical bugs** fixed
- **Ready for Stage 3** (Documentation)

---

## 📋 IMPLEMENTATION STAGES

### Stage 1: Critical Bug Fixes ✅ COMPLETE
**Priority:** HIGH | **Duration:** 1-2 days

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Fix subcircuit parsing (gpdk090_mos_iso.scs) | ✅ DONE |
| 1.2 | Fix include/library file following | ⬜ SKIP (not needed) |
| 1.3 | Fix empty model body handling | ✅ DONE |
| 1.4 | Add missing device type patterns | ✅ DONE |

### Stage 2: Verification & Testing ✅ COMPLETE
**Priority:** HIGH | **Duration:** 1 day

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | Run full translation suite on all PDKs | ✅ DONE |
| 2.2 | Fix unit test failures | ✅ DONE |
| 2.3 | All 568 tests passing | ✅ DONE |
| 2.4 | 83% code coverage | ✅ DONE |

### Stage 3: Documentation Update ⏳ IN PROGRESS
**Priority:** MEDIUM | **Duration:** 1 day

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Update README.md with latest results | ⬜ TODO |
| 3.2 | Create QUICKSTART guide | ⬜ TODO |
| 3.3 | Update PROJECT_STATUS.md | ⬜ TODO |
| 3.4 | Clean up duplicate docs | ⬜ TODO |

### Stage 4: Polish & Release ⬜ PENDING
**Priority:** LOW | **Duration:** 1 day

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Improve error messages | ⬜ TODO |
| 4.2 | Add usage examples | ⬜ TODO |
| 4.3 | Final code cleanup | ⬜ TODO |
| 4.4 | Version bump to 3.0.0 | ⬜ TODO |

---

## 🏗️ ARCHITECTURE REFERENCE

### File Structure
```
src/
├── ir/                     # ✅ COMPLETE - Intermediate Representation
│   ├── model_ir.py         # ModelIR, Condition, Variation classes
│   └── ir_serializer.py    # JSON/YAML serialization
│
├── parsers/                # ✅ 95% COMPLETE - Format-specific parsers
│   ├── base_parser.py      # Abstract parser interface
│   ├── spectre_parser.py   # Spectre → IR (needs subcircuit fix)
│   ├── hspice_parser.py    # HSPICE → IR (✅ fixed device types)
│   ├── ngspice_parser.py   # ngspice → IR
│   └── expression_parser.py # Math expression evaluator
│
├── writers/                # ✅ 98% COMPLETE - Format-specific writers
│   ├── base_writer.py      # Abstract writer interface
│   ├── spectre_writer.py   # IR → Spectre
│   ├── hspice_writer.py    # IR → HSPICE
│   └── ngspice_writer.py   # IR → ngspice (✅ fixed .lib/.endl)
│
├── validation/             # ✅ COMPLETE - Validation pipeline
│   ├── ir_validator.py     # IR structure validation
│   └── syntax_validator.py # Format syntax checking
│
└── lowering/               # ✅ COMPLETE - Semantic lowering
    └── device_lowering.py  # Backend-aware transformations

verification/               # ✅ COMPLETE - Test framework
├── testbench_generator.py  # Auto-generate testbenches
├── verifier.py             # Orchestrate verification
└── comparators.py          # Result comparison

cli.py                      # ✅ COMPLETE - Command-line interface
```

### Translation Flow
```
Input File → Parser → IR (ModelIR) → Lowering → Writer → Output File
                          ↓
                    IR Validator
                          ↓
                  Syntax Validator
```

---

## 🔧 KEY FIXES APPLIED

### Fix 1: Device Type Classification (COMPLETED)
**File:** `src/parsers/hspice_parser.py`
**Issue:** Diodes (type='d') and resistors (type='r') were misclassified as NMOS
**Solution:** Added direct type mapping for 'd', 'r', 'c' and name-based patterns

### Fix 2: ngspice Library Blocks (COMPLETED)
**File:** `src/writers/ngspice_writer.py`
**Issue:** ngspice doesn't support .lib/.endl blocks
**Solution:** Use comment-separated sections instead

### Fix 3: Verification Framework (COMPLETED)
**Files:** `verification/*.py`, `cli.py`
**Issue:** No automated testing capability
**Solution:** Complete testbench generation and verification pipeline

### Fix 4: Subcircuit Parsing (COMPLETED)
**File:** `src/parsers/spectre_parser.py`
**Issue:** Files with only subcircuit definitions returned 0 models
**Solution:** Extended `parse_to_ir()` to convert subcircuits to ModelIR when no .model found

### Fix 5: Unit Test Updates (COMPLETED)
**File:** `tests/test_writers/test_ngspice_writer.py`
**Issue:** Tests expected `.lib/.endl` blocks that ngspice doesn't support
**Solution:** Updated tests to use base_parameters and check model output

---

## 🐛 KNOWN ISSUES (RESOLVED)

### Issue 1: Subcircuit Parsing ✅ FIXED
**Files:** `gpdk090_mos_iso.scs` and similar
**Resolution:** Added `_subcircuit_to_ir()` method to convert subcircuit definitions

### Issue 2: Include File Following ⬜ SKIPPED
**Files:** `gpdk090.scs`, `hlmc55lp/tt.lib`, etc.
**Resolution:** Not needed - individual files translate correctly

### Issue 3: Empty Model Bodies ✅ HANDLED
**Files:** Some SMIC resistor models
**Resolution:** Writers handle empty parameter case gracefully

---

## 📊 SUCCESS METRICS

### Translation Metrics
- **Models Translated:** 1,095+ (Target: 1000+) ✅
- **PDKs Supported:** 3 (Cadence90, SMIC180HV, ASAP7) ✅
- **Backends:** 3 (ngspice, HSPICE, Spectre) ✅
- **Success Rate:** 92.4% (Target: >85%) ✅

### Quality Metrics
- **Test Coverage:** 82-94% (Target: >80%) ✅
- **Syntax Validity:** 100% ✅
- **Capacitor Verification:** PASS ✅
- **Diode Verification:** 100% PASS ✅

---

## 🚀 COMMANDS REFERENCE

### Translation
```bash
# Basic translation
./cli.py translate input.scs --source spectre --target ngspice -o output.lib

# Batch translation
for f in tools/spice-libraries/private-models/cadence90/spectre/*.scs; do
  ./cli.py translate "$f" --source spectre --target ngspice
done
```

### Verification
```bash
# Verify single device
./cli.py verify input.scs device_name --device-class capacitor --target ngspice

# Run all verification tests
./cli.py verify-all --target ngspice
```

### Testing
```bash
# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 📝 REVISION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-01 | Initial master plan created |

---

## ⚡ QUICK REFERENCE FOR AI AGENTS

### When asked to translate files:
```bash
./cli.py translate <input> --source <spectre|hspice|ngspice> --target <spectre|hspice|ngspice> -o <output>
```

### When asked to verify translation:
```bash
./cli.py verify <input> <device_name> --device-class <capacitor|resistor|mos|bjt|diode> --target <ngspice|hspice>
```

### When fixing parser issues:
- Check `src/parsers/spectre_parser.py` for Spectre files
- Check `src/parsers/hspice_parser.py` for HSPICE/lib files
- Check `src/parsers/ngspice_parser.py` for ngspice files

### When fixing writer issues:
- Check `src/writers/ngspice_writer.py` for ngspice output
- Check `src/writers/hspice_writer.py` for HSPICE output
- Check `src/writers/spectre_writer.py` for Spectre output

### Key files to know:
- `src/ir/model_ir.py` - Core data structures (ModelIR, DeviceType, etc.)
- `src/main.py` - TranslationEngine entry point
- `cli.py` - Command-line interface
- `CONSTRAINTS.md` - Code quality requirements

---

**END OF MASTER PLAN**

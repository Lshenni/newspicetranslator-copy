# SPICE Translator v3.0 - Master Implementation Plan

**Document Type:** Implementation Roadmap  
**Updated:** February 1, 2026  
**Status:** ACTIVE - Phase 1-5 Complete, Phase 6 In Progress

---

## 🎯 PROJECT OVERVIEW

### Mission
Build a production-ready SPICE model translator using Intermediate Representation (IR) architecture that converts between Spectre, HSPICE, and ngspice formats while preserving electrical behavior.

### Current Status: 95% Complete ✅

#### Validation Results (Feb 1, 2026)
| Metric | Value |
|--------|-------|
| Test Suite | **569 passing**, 15 skipped |
| Code Coverage | **84%** |
| Models Translated | **963 → 1,001** |
| ngspice Smoke Sims | 55 passed, 8 skipped*, 0 failed |
| **Pass Rate** | **100%** (excluding known limitations) |

*Skipped = ngspice binary limitation (MOS level 72), not translator bug

---

## 📋 IMPLEMENTATION PHASES

### Phase 1: Core Infrastructure ✅ COMPLETE
- ModelIR data structures and serialization
- Parser framework (Spectre, HSPICE, ngspice)
- Writer framework for all three formats
- Expression parser for parameter evaluation

### Phase 2: Translation Engine ✅ COMPLETE
- Spectre → ngspice (primary path)
- HSPICE → ngspice
- Device type classification
- Parameter mapping and transformation

### Phase 3: Validation Pipeline ✅ COMPLETE
- IR structural validation
- Syntax validation per format
- Round-trip testing infrastructure
- Automated corpus scanning

### Phase 4: Verification Framework ✅ COMPLETE
- Testbench generation for all device classes
- ngspice/HSPICE simulator wrappers
- Metrics extraction (I-V, C-V curves)
- Automated comparison and reporting

### Phase 5: Production Hardening ✅ COMPLETE
- Skip classification for unsupported MOS levels
- Graceful error handling
- CLI improvements (`translate`, `verify`, `verify-all`)
- Full corpus validation (963 models, 100% pass)

### Phase 6: Documentation ⏳ IN PROGRESS
| Task | Description | Status |
|------|-------------|--------|
| 6.1 | Update README.md | ✅ DONE |
| 6.2 | Create ARCHITECTURE.md | ✅ DONE |
| 6.3 | Create VALIDATION_RESULTS.md | ✅ DONE |
| 6.4 | Update MASTER_PLAN.md | ✅ DONE |

---

## 🚧 NEXT STEPS (Phase 7+)

### Phase 7: BSIM-CMG Support Investigation
**Priority:** HIGH | **Status:** PENDING
**Goal:** Enable translation of advanced FinFET models

| Task | Description | Notes |
|------|-------------|-------|
| 7.1 | Investigate MOS level 72 (BSIM-CMG) | ngspice binary limitation |
| 7.2 | Research ngspice compilation options | May need custom build |
| 7.3 | Alternative: PSP model mapping | Map BSIM-CMG → PSP |
| 7.4 | Document FinFET support status | ASAP7, FreePDK3, Synopsys14 |

**Affected PDKs:**
- ASAP7 (7nm FinFET) - 4 files skipped
- FreePDK3 (3nm) - 2 files skipped
- Synopsys14 (14nm) - 2 files skipped

### Phase 8: HSPICE Translation Path
**Priority:** MEDIUM | **Status:** PENDING
**Goal:** Enable HSPICE → HSPICE for vendor compatibility

| Task | Description |
|------|-------------|
| 8.1 | Complete HSPICE writer edge cases |
| 8.2 | Add HSPICE verification path |
| 8.3 | Test with commercial HSPICE binary |
| 8.4 | Validate against vendor models |

### Phase 9: Include/Library Aggregation
**Priority:** MEDIUM | **Status:** PENDING
**Goal:** Handle complex multi-file PDK structures

| Task | Description |
|------|-------------|
| 9.1 | Parse `.include` and `.lib` directives |
| 9.2 | Follow file references recursively |
| 9.3 | Aggregate all models into single output |
| 9.4 | Handle section selection (tt, ff, ss) |

### Phase 10: Monte Carlo & Corners
**Priority:** LOW | **Status:** PENDING
**Goal:** Support process variation simulation

| Task | Description |
|------|-------------|
| 10.1 | Parse Spectre `statistics` blocks |
| 10.2 | Map to ngspice `.alter` syntax |
| 10.3 | Generate corner cases (tt, ff, ss, sf, fs) |
| 10.4 | Support mismatch parameters |

### Phase 11: Advanced Features
**Priority:** LOW | **Status:** FUTURE

| Feature | Description |
|---------|-------------|
| Web UI | Browser-based translation interface |
| API Server | REST API for translation service |
| VS Code Extension | Integrated PDK translation |
| BSIM4 Extensions | Support all BSIM4 parameters |
| Aging Models | Hot-carrier injection, NBTI |

---

## 🏗️ ARCHITECTURE

### Directory Structure
```
new-spice-translator/
├── src/
│   ├── ir/                     # Intermediate Representation
│   │   ├── model_ir.py         # ModelIR, Condition, Variation
│   │   └── ir_serializer.py    # JSON/YAML serialization
│   ├── parsers/                # Format-specific parsers
│   │   ├── spectre_parser.py   # Spectre → IR
│   │   ├── hspice_parser.py    # HSPICE → IR
│   │   └── ngspice_parser.py   # ngspice → IR
│   ├── writers/                # Format-specific writers
│   │   ├── ngspice_writer.py   # IR → ngspice
│   │   ├── hspice_writer.py    # IR → HSPICE
│   │   └── spectre_writer.py   # IR → Spectre
│   ├── validation/             # Validation pipeline
│   ├── lowering/               # Semantic transformations
│   └── main.py                 # TranslationEngine
├── verification/               # Test framework
│   ├── testbench_generator.py  # Auto-generate testbenches
│   ├── verifier.py             # Verification orchestration
│   └── comparators.py          # Result comparison
├── simulators/                 # Simulator wrappers
│   └── run_simulator.py        # ngspice/HSPICE execution
├── cli.py                      # Command-line interface
├── tests/                      # Unit tests (569 passing)
└── tools/                      # Validation harnesses
```

### Translation Pipeline
```
┌─────────┐    ┌────────┐    ┌─────────┐    ┌──────────┐    ┌────────┐
│ Input   │───▶│ Parser │───▶│ ModelIR │───▶│ Lowering │───▶│ Writer │───▶ Output
│ (Spectre│    │        │    │         │    │          │    │        │    (ngspice)
│ HSPICE) │    └────────┘    └────┬────┘    └──────────┘    └────────┘
└─────────┘                       │
                                  ▼
                            ┌───────────┐
                            │ Validator │
                            └───────────┘
```

---

## 🔧 COMPLETED FEATURES

### Core Translation
- ✅ Spectre → ngspice (primary production path)
- ✅ HSPICE → ngspice (industry standard conversion)
- ✅ Subcircuit-to-model conversion
- ✅ Parameter expression evaluation
- ✅ Device type inference (MOS, BJT, diode, R, C)

### Verification
- ✅ Automatic testbench generation
- ✅ ngspice simulation wrapper with skip detection
- ✅ I-V and C-V characteristic extraction
- ✅ Automated pass/fail comparison
- ✅ Full corpus validation harness

### Quality
- ✅ 569 unit tests (100% pass)
- ✅ 84% code coverage
- ✅ Graceful error handling
- ✅ Skip classification for unsupported features

---

## ⚠️ KNOWN LIMITATIONS

### 1. MOS Level 72 (BSIM-CMG) - ngspice Binary Limitation
**Status:** Skipped (not a translator bug)

The standard ngspice binary doesn't include MOS level 72 (BSIM-CMG for FinFETs).
8 PDK files are affected and automatically classified as "skipped":

| PDK | Files | Notes |
|-----|-------|-------|
| ASAP7 (7nm) | 4 | FinFET models |
| FreePDK3 (3nm) | 2 | Advanced node |
| Synopsys14 (14nm) | 2 | FinFET models |

**Workarounds:**
1. Build ngspice with BSIM-CMG support
2. Use HSPICE for FinFET verification
3. Map to PSP model (level 103)

### 2. Include File Aggregation
Multi-file PDK structures with `.include` directives are not automatically followed.
Each file must be translated individually.

### 3. Monte Carlo / Statistics
Spectre `statistics` blocks are not yet translated to ngspice `.alter` syntax.

---

## 📊 VALIDATION RESULTS (Feb 1, 2026)

### Corpus Summary
| Metric | Value |
|--------|-------|
| Total Files Scanned | 113 |
| Files Translated | 65 |
| Models Input | 963 |
| Models Output | 1,001 |
| ngspice Smoke Tests | 63 total |
| Passed | 55 (87.3%) |
| Skipped | 8 (12.7%) |
| Failed | 0 (0%) |
| **Pass Rate** | **100%** |

### By PDK
| PDK | Files | Models | Status |
|-----|-------|--------|--------|
| Cadence GPDK090 | 14 | 200+ | ✅ All passing |
| SMIC 180HV | 12 | 300+ | ✅ All passing |
| SkyWater SKY130 | 8 | 150+ | ✅ All passing |
| PTM Models | 6 | 50+ | ✅ All passing |
| ASAP7 (7nm) | 4 | 80+ | ⚠️ Skipped (MOS level 72) |
| FreePDK3 | 2 | 40+ | ⚠️ Skipped (MOS level 72) |
| Synopsys14 | 2 | 30+ | ⚠️ Skipped (MOS level 72) |
| Others | 17 | 100+ | ✅ All passing |

---

## 🚀 CLI REFERENCE

### Translation Commands
```bash
# Translate Spectre to ngspice
./cli.py translate input.scs --source spectre --target ngspice -o output.lib

# Translate HSPICE to ngspice
./cli.py translate input.lib --source hspice --target ngspice -o output.lib

# Batch translate all files
for f in tools/spice-libraries/private-models/cadence90/spectre/*.scs; do
  ./cli.py translate "$f" --source spectre --target ngspice
done
```

### Verification Commands
```bash
# Verify single model
./cli.py verify input.scs nmos_3p3 --device-class mos --target ngspice

# Verify all translatable files
./cli.py verify-all --target ngspice

# Verify capacitor model
./cli.py verify cap_model.scs cap_3p3 --device-class capacitor --target ngspice
```

### Testing Commands
```bash
# Run full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run corpus validation harness
python tools/rerun_private_models.py
```

---

## 📝 REVISION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2026-02-01 | Updated with Phase 7+ roadmap, validation results |
| 2.0 | 2026-02-01 | Added verification framework, skip classification |
| 1.0 | 2026-02-01 | Initial master plan created |

---

## ⚡ AI AGENT REFERENCE

### Translation
```bash
./cli.py translate <input> --source <spectre|hspice|ngspice> --target <spectre|hspice|ngspice> -o <output>
```

### Verification
```bash
./cli.py verify <input> <device_name> --device-class <capacitor|resistor|mos|bjt|diode> --target <ngspice|hspice>
```

### Key Files
| File | Purpose |
|------|---------|
| `src/ir/model_ir.py` | Core IR data structures |
| `src/parsers/spectre_parser.py` | Spectre → IR |
| `src/parsers/hspice_parser.py` | HSPICE → IR |
| `src/writers/ngspice_writer.py` | IR → ngspice |
| `verification/verifier.py` | Verification orchestration |
| `simulators/run_simulator.py` | Simulator wrappers |
| `cli.py` | Command-line interface |

---

**END OF MASTER PLAN v3.0**

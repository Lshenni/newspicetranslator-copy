# SPICE Translator IR Implementation - Document Index

**Created:** January 4, 2026  
**Purpose:** Index of all masterplan and implementation documents

---

## 📚 Document Suite Overview

This document suite provides a **complete roadmap** for implementing an IR-based SPICE translator from scratch, with full compliance to CONSTRAINTS.md.

---

## 📖 Documents Created

### 1. **NEW2026.md** - Master Plan
**Purpose:** Overall architecture and vision  
**Size:** ~900 lines  
**Content:**
- Executive summary of IR-based approach
- Architecture overview and project structure
- Key innovation: Hub-and-spoke vs. N×(N-1) translators
- Design principles (CONSTRAINTS.md compliance)
- IR specification overview
- Translation workflow
- Implementation phases summary
- Files to export from current project
- Success criteria and risk mitigation

**Read this first** to understand the big picture.

---

### 2. **NEW2026_Phase1.md** - IR Foundation & Base Classes
**Purpose:** Week 1-2 implementation details  
**Size:** ~1,400 lines  
**Content:**
- Complete IR data structures (ModelIR, Condition, Variation)
- IR serialization (JSON/YAML)
- Base parser interface
- Base writer interface
- Full unit tests with >80% coverage
- Code examples (400-500 lines per component)

**Key Deliverables:**
- `src/ir/model_ir.py` (400 lines)
- `src/ir/ir_serializer.py` (150 lines)
- `src/parsers/base_parser.py` (250 lines)
- `src/writers/base_writer.py` (200 lines)
- Complete test suite

---

### 3. **NEW2026_Phase2.md** - Parser Implementation
**Purpose:** Week 3-4 implementation details  
**Size:** ~1,100 lines  
**Content:**
- Spectre → IR parser (600 lines)
- HSPICE → IR parser (550 lines)
- ngspice → IR parser (500 lines)
- Expression parser (copy from existing)
- Integration tests

**Key Deliverables:**
- `src/parsers/spectre_parser.py` with `parse_to_ir()` method
- `src/parsers/hspice_parser.py` with `parse_to_ir()` method
- `src/parsers/ngspice_parser.py` with `parse_to_ir()` method
- Comprehensive test coverage

**Files to Export:**
- ✅ `expression_parser.py` - Copy as-is
- ⚠️ Other parsers - Add `parse_to_ir()` method

---

### 4. **NEW2026_FileExportGuide.md** - Migration Guide
**Purpose:** Complete file-by-file migration guide  
**Size:** ~800 lines  
**Content:**
- Which files to copy directly (✅)
- Which files need modification (⚠️)
- Which files need refactoring (🔄)
- Which files to replace (❌)
- Step-by-step migration process
- Code examples: Before → After
- File-by-file checklist
- Testing strategy after migration

**Use this** when actually moving files from the old project to the new IR-based structure.

---

## 🎯 Quick Start Guide

### For Understanding the Project
1. Read **NEW2026.md** (Master Plan) - 15 minutes
2. Skim **NEW2026_FileExportGuide.md** - 10 minutes
3. Review **CONSTRAINTS.md** (existing) - 5 minutes

### For Implementation
1. **Week 1-2:** Follow **NEW2026_Phase1.md** step-by-step
   - Implement IR classes
   - Write unit tests
   - Verify >80% coverage

2. **Week 3-4:** Follow **NEW2026_Phase2.md** step-by-step
   - Copy expression_parser.py as-is
   - Implement Spectre → IR
   - Implement HSPICE → IR
   - Implement ngspice → IR

3. **Week 5-6:** Implement Writers (Phase 3)
   - Extract syntax generation from old translators
   - Create NgspiceWriter, HSPICEWriter, SpectreWriter

4. **Week 7-8:** Implement Mapping System (Phase 4)
   - Centralized parameter mapper
   - Alias resolver
   - Self-learning discovery

5. **Week 9-10:** Validation Pipeline (Phase 5)
   - IR validator
   - Syntax validator
   - Simulation validator

6. **Week 11-12:** CLI & Integration (Phase 6)
   - Translation engine
   - argparse CLI
   - End-to-end tests

### For File Migration
1. Open **NEW2026_FileExportGuide.md**
2. Use the checklist in "File-by-File Migration Checklist"
3. Follow the step-by-step process in "Step-by-Step Migration Process"
4. Run tests after each migration step

---

## 📊 Document Comparison

| Document | Purpose | When to Use | Size |
|----------|---------|-------------|------|
| **NEW2026.md** | Overall vision | Planning, architecture review | Large |
| **NEW2026_Phase1.md** | IR foundation code | Week 1-2 implementation | Very Large |
| **NEW2026_Phase2.md** | Parser code | Week 3-4 implementation | Large |
| **NEW2026_FileExportGuide.md** | File migration | During actual migration | Large |

---

## 🔑 Key Concepts Across Documents

### IR (Intermediate Representation)
- **What:** Universal format-agnostic representation of SPICE models
- **Why:** Eliminates N×(N-1) translator problem
- **Where Defined:** NEW2026.md, NEW2026_Phase1.md
- **Classes:** ModelIR, Condition, ModelVariation

### Parser → IR → Writer Pattern
- **Old Way:** Spectre → ngspice translator (direct)
- **New Way:** Spectre → IR (parser), IR → ngspice (writer)
- **Benefit:** Add new format with just 1 parser + 1 writer
- **Explained In:** NEW2026.md Section "Architecture Overview"

### CONSTRAINTS.md Compliance
All documents enforce:
- ✅ Complete implementation (no TODOs)
- ✅ Type annotations everywhere
- ✅ Google-style docstrings
- ✅ <1000 lines per file
- ✅ pytest only for testing
- ✅ >80% code coverage

### File Export Strategy
- **✅ Direct Copy:** expression_parser.py, utilities, YAML configs
- **⚠️ Modify:** Parsers (add `parse_to_ir()`)
- **🔄 Refactor:** Translators → split into Writers + Mapping
- **❌ Replace:** translator_factory.py, base_translator.py

---

## 📋 Implementation Checklist

### Pre-Implementation
- [ ] Read NEW2026.md masterplan
- [ ] Review CONSTRAINTS.md requirements
- [ ] Set up new workspace directory structure
- [ ] Initialize git repository

### Phase 1 (Week 1-2)
- [ ] Implement ModelIR class (src/ir/model_ir.py)
- [ ] Implement Condition, Corner, Temperature enums
- [ ] Implement IR serializer (JSON/YAML)
- [ ] Create BaseParser interface
- [ ] Create BaseWriter interface
- [ ] Write comprehensive unit tests
- [ ] Verify >80% coverage
- [ ] All tests passing

### Phase 2 (Week 3-4)
- [ ] Copy expression_parser.py as-is
- [ ] Implement SpectreParser.parse_to_ir()
- [ ] Implement HSPICEParser.parse_to_ir()
- [ ] Implement NgspiceParser.parse_to_ir()
- [ ] Write integration tests
- [ ] Test with real SPICE files
- [ ] Verify parameter extraction

### Phase 3-6 (Week 5-12)
- [ ] Implement writers (Phase 3)
- [ ] Implement mapping system (Phase 4)
- [ ] Implement validation pipeline (Phase 5)
- [ ] Implement CLI and integration (Phase 6)

### Post-Implementation
- [ ] Run full test suite
- [ ] Check code coverage (>80%)
- [ ] Verify CONSTRAINTS.md compliance
- [ ] Write user documentation
- [ ] Create examples
- [ ] Performance testing

---

## 🚀 Success Criteria

### Technical
- ✅ All 3 formats supported (Spectre, HSPICE, ngspice)
- ✅ IR-based translation working
- ✅ Parameter mapping functional
- ✅ Validation pipeline operational
- ✅ >80% test coverage
- ✅ All tests passing

### Code Quality (CONSTRAINTS.md)
- ✅ All files <1000 lines
- ✅ 100% type annotations
- ✅ Google-style docstrings everywhere
- ✅ Zero TODO comments
- ✅ All imports verified
- ✅ pytest only (no unittest)

### Performance
- ✅ <1 second per model file
- ✅ <10 seconds for batch (100 models)

---

## 📞 How to Use This Document Suite

### If you want to...

**...understand the overall approach:**
→ Read NEW2026.md

**...start coding Phase 1:**
→ Follow NEW2026_Phase1.md step-by-step

**...start coding Phase 2:**
→ Follow NEW2026_Phase2.md step-by-step

**...migrate files from old project:**
→ Use NEW2026_FileExportGuide.md checklists

**...see code examples:**
→ All phase documents have complete code examples

**...understand IR design:**
→ NEW2026.md "IR Specification" + NEW2026_Phase1.md "Task 1.1"

**...know what to copy as-is:**
→ NEW2026_FileExportGuide.md "Copy Directly" section

---

## 📝 Document Status

| Document | Status | Lines | Completeness |
|----------|--------|-------|--------------|
| NEW2026.md | ✅ Complete | ~900 | 100% |
| NEW2026_Phase1.md | ✅ Complete | ~1400 | 100% |
| NEW2026_Phase2.md | ✅ Complete | ~1100 | 100% |
| NEW2026_FileExportGuide.md | ✅ Complete | ~800 | 100% |
| NEW2026_Phase3.md | ⏳ To Create | - | 0% |
| NEW2026_Phase4.md | ⏳ To Create | - | 0% |
| NEW2026_Phase5.md | ⏳ To Create | - | 0% |
| NEW2026_Phase6.md | ⏳ To Create | - | 0% |

**Note:** Phases 3-6 can be created following the same pattern as Phase 1-2 if needed.

---

## 🎓 Learning Path

### Beginner (New to the Project)
1. Read NEW2026.md sections:
   - Executive Summary
   - Architecture Overview
   - Key Features
2. Skim NEW2026_Phase1.md to see IR classes
3. Look at code examples in FileExportGuide.md

### Intermediate (Ready to Implement)
1. Read full NEW2026.md
2. Deep dive NEW2026_Phase1.md
3. Study CONSTRAINTS.md
4. Start implementing Phase 1

### Advanced (Migration Expert)
1. Use NEW2026_FileExportGuide.md as primary reference
2. Refer to phase documents for detailed implementations
3. Adapt and extend as needed

---

## 💡 Key Insights

### Why IR-Based Architecture?
**Problem:** With 3 formats, you need 3×2 = 6 translators  
**Solution:** With IR, you need 3 parsers + 3 writers = 6 components  
**Benefit:** Components are reusable, maintainable, testable

### Why This Documentation?
- **Complete:** Every implementation detail included
- **Compliant:** Follows CONSTRAINTS.md strictly
- **Practical:** Real code examples, not pseudocode
- **Incremental:** Phase-by-phase approach
- **Tested:** Built-in testing strategy

### Why Export Guide?
- Reuse existing working code
- Don't reinvent the wheel
- Clear migration path
- Preserve domain knowledge

---

## 📖 Additional Resources

### In Current Project
- `docs/CONSTRAINTS.md` - Development constraints
- `docs/PLAN.md` - Original project plan
- `s2s/parsers/` - Existing parser implementations
- `s2s/translators/` - Existing translator implementations

### To Be Created in New Project
- `docs/api_reference.md` - API documentation
- `docs/user_guide.md` - User guide
- `docs/ir_specification.md` - Detailed IR spec
- `README.md` - Project overview

---

## ✅ Final Checklist Before Starting

- [ ] Read NEW2026.md completely
- [ ] Understand IR concept
- [ ] Review CONSTRAINTS.md
- [ ] Set up development environment
- [ ] Create new workspace directory
- [ ] Have access to current project files
- [ ] Ready to implement Phase 1

---

**Document Index Status:** ✅ Complete  
**Total Documents Created:** 4  
**Total Pages:** ~170 lines of detailed guidance  
**Ready for Implementation:** Yes  

**Start Here:** NEW2026.md → NEW2026_Phase1.md → Code!

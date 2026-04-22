# APCCAS1

Date: April 17, 2026  
Topic: SPICE Model Translation with Semantic IR and Constraint-Aware Verification

---

## 1. Paper Structure (Recommended)

1. Title
2. Abstract
3. Keywords
4. Introduction
5. Related Work
6. Methodology
7. Experimental Setup
8. Results and Discussion
9. Threats to Validity
10. Conclusion and Future Work
11. References

---

## 2. Draft Title Options

1. Semantic-IR-Based SPICE Model Translation Across Spectre, HSPICE, and ngspice with Constraint-Aware Verification
2. A Compiler-Style Cross-Simulator Device Model Translator with Full-Batch Credibility Verification
3. ModelIR: Robust Multi-Format SPICE Device Model Translation and Verification for 17 PDK Families

---

## 3. Draft Abstract (APCCAS-Oriented)

Cross-simulator SPICE model portability remains a practical bottleneck for analog and mixed-signal design flows, especially when model libraries span Spectre, HSPICE, and ngspice syntax and semantics. This work presents a compiler-style SPICE model translator built on a semantic intermediate representation (ModelIR), enabling bidirectional translation among the three simulators while preserving device-model intent. The framework includes recursive include/lib resolution, model-type normalization, and BSIM-level-aware conversion. To assess credibility, we integrate a full verification suite combining syntax, DC/AC/transient checks, sanity checks, Monte Carlo robustness, and round-trip consistency (A→B→A). On a clean full-batch run over 17 PDK families (322 source files), the translator executes 224 translations and emits 6638 translated models. Verification over 15 ngspice-targeted PDK outputs covers 52 files and 587 tests, achieving 587/587 pass (100.0%), including 52/52 round-trip and 52/52 Monte Carlo passes. We further introduce explicit simulator-constraint classification for known BSIM4 geometry-envelope guard failures, preventing simulator parameter-envelope limits from being misreported as translation defects. The results demonstrate that semantic translation combined with constraint-aware verification provides a reproducible and publication-grade path for cross-simulator model interoperability.

---

## 4. Introduction: What to Include

1. Problem statement:
   - Model libraries are simulator-specific and costly to port.
   - Syntax-level conversion is insufficient because model semantics differ.
2. Gap:
   - Existing workflows often under-separate translation defects from simulator-side constraints.
3. Contributions (explicit bullets):
   - Semantic IR translation pipeline for Spectre/HSPICE/ngspice.
   - Full-batch reproducibility workflow over 17 PDK families.
   - Multi-axis verification suite (syntax + electrical + statistical + round-trip).
   - Constraint-aware BSIM4 classification to reduce false defect attribution.
4. Impact:
   - Practical reuse of model libraries across flows.
   - Better confidence for industrial and academic use.

---

## 5. Related Work: Suggested Subsections

1. SPICE model translation/parsing tools (syntax-only vs semantic)
2. Compact model portability and BSIM compatibility concerns
3. Verification methodologies for model translation
4. Distinction of this work: semantic IR + constraint-aware verification at full-batch scale

---

## 6. Methodology: Section Blueprint

### 6.1 System Overview

- Parser -> ModelIR -> Translator -> Writer -> Verifier
- Supported source/target formats and translation directions

### 6.2 Semantic Intermediate Representation

- Core fields captured (device type, model level, parameters, expressions)
- Handling of subcircuits and included libraries
- Expression normalization strategy

### 6.3 Translation Rules

- Device/model-type mapping logic
- BSIM level handling and parameter mapping
- Include/lib resolution and wrapper handling

### 6.4 Constraint-Aware Verification

- Verification axes:
  - Syntax parsing
  - DC/AC/transient behavior checks
  - Sanity checks
  - Monte Carlo consistency
  - Round-trip consistency
- Option B classification:
  - Known BSIM4 geometry-envelope signatures are tagged as simulator constraints
  - Prevents false negatives in translation quality accounting

### 6.5 Reproducibility Protocol

- Clean-run commands
- Artifact files used for result extraction

---

## 7. Experimental Setup: Checklist

1. Hardware/OS/toolchain versions
2. Python version and key dependencies
3. ngspice version and invocation mode
4. Dataset:
   - 17 PDK families
   - 322 source files
5. Evaluation settings:
   - Monte Carlo runs per file
   - Round-trip enabled
   - Full mode (not quick mode)

---

## 8. Results and Discussion: Required Content

### 8.1 Translation Coverage

Report:
- PDKs processed: 17
- Source files: 322
- Translations: 224
- Models translated: 6638

### 8.2 Verification Performance

Report:
- Verified PDKs (ngspice-targeted): 15
- Files: 52
- Tests: 587
- Pass/fail: 587/0
- Round-trip: 52/52
- Monte Carlo: 52/52

### 8.3 Per-PDK Analysis

- Table with each PDK and tests passed
- Highlight previously challenging groups (SMIC180/advanced nodes)

### 8.4 Ablation / Improvement Narrative

Suggested comparison table:
- Before constraint-aware classification vs after (Option B)
- Show reduction in false defect attribution

### 8.5 Discussion

- Why constraint-aware classification is academically valid
- Limits: classification signatures are rule-based and simulator-specific
- Generalizability to other simulators and model families

---

## 9. Figures and Tables Plan

### Figure 1 (Required): System Architecture

- Diagram of parser/IR/translator/writer/verifier pipeline
- Inputs/outputs for each stage

### Figure 2 (Recommended): Full-Batch Workflow

- Clean output -> batch translate -> batch verify -> report extraction

### Figure 3 (Recommended): Verification Axes Coverage

- Radar or grouped bars for syntax/DC/AC/tran/sanity/MC/round-trip pass rates

### Figure 4 (Optional): Improvement Progression

- Pass-rate progression across major campaign checkpoints

### Table 1 (Required): Dataset Summary

- PDK family, source format, source files, translated outputs

### Table 2 (Required): Final Verification Summary

- total tests, pass rate, MC pass, round-trip pass

### Table 3 (Required): Per-PDK Results

- PDK, files tested, tests, pass/fail, notes

### Table 4 (Recommended): Constraint Classification Impact

- Failure signature, previous status, classified status, rationale

---

## 10. Threats to Validity (Suggested)

1. Internal validity:
   - Rule-based constraint classification may miss unseen signatures
2. External validity:
   - Results tied to tested PDK set and simulator versions
3. Construct validity:
   - Pass-rate alone does not replace deep waveform equivalence in all scenarios

---

## 11. Conclusion and Future Work

1. Summary of contributions and final metrics
2. Practical significance for cross-simulator portability
3. Future work:
   - Wider simulator support
   - automated discovery of new constraint signatures
   - richer waveform-level equivalence and runtime benchmarks

---

## 12. Appendix Material (Strongly Recommended)

1. Exact command lines for reproduction
2. JSON schema snippets for result artifacts
3. Additional per-file failure/constraint logs
4. Environment manifest (Python, OS, simulator versions)

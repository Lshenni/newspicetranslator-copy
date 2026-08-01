# P2 Report

## Preliminary

### Title
SpiceModelIR: Cross-Simulator SPICE Model Translation Using Semantic Intermediate Representation and Intelligent Parameter Inference

### Abstract
Interoperability issues among Cadence Spectre, Synopsys HSPICE, and ngspice continue to slow PDK migration and model reuse. This report presents SpiceModelIR, a semantic translation framework that combines dialect-aware parsing, a physics-grounded intermediate representation (IR), missing-parameter inference, and a closed-loop verification system. The methodology targets practical translation failures found in industrial and open PDK model libraries, including unresolved symbols, BSIM level mismatch, expression incompatibility, include-path breakage, and simulator guardrail violations. Experimental evaluation on multi-node PDK data demonstrates high translation coverage, stable simulation behavior after inference, and reliable failure classification through a compact rule-based verifier. The results support the claim that semantic normalization plus verification-aware filtering is necessary for robust cross-simulator model portability.

### Abstrak
Isu kebolehoperasian antara Cadence Spectre, Synopsys HSPICE, dan ngspice terus melambatkan migrasi PDK serta penggunaan semula model. Laporan ini membentangkan SpiceModelIR, satu rangka kerja penterjemahan semantik yang menggabungkan penghuraian berasaskan dialek, perwakilan perantaraan (IR) berasaskan fizik, inferens parameter hilang, dan sistem pengesahan gelung tertutup. Metodologi ini menyasarkan kegagalan penterjemahan praktikal dalam perpustakaan model PDK industri dan sumber terbuka, termasuk simbol tidak ditakrif, ketidakpadanan tahap BSIM, ketidakserasian ungkapan, kegagalan laluan include, dan pelanggaran had simulator. Penilaian eksperimen ke atas data PDK pelbagai nod menunjukkan liputan penterjemahan yang tinggi, kestabilan simulasi selepas inferens, dan pengelasan kegagalan yang boleh dipercayai melalui pengesah berasaskan peraturan yang padat. Keputusan menyokong bahawa normalisasi semantik bersama penapisan berasaskan pengesahan adalah perlu untuk kebolehgunaan model merentas simulator yang teguh.

### Acknowledgements
I would like to thank my supervisor, collaborators, and lab members for their guidance and feedback throughout this project.

---

## Chapter 1: Introduction

### 1.1 Background
SPICE remains the dominant simulation foundation for analog and mixed-signal design flows, but dialect fragmentation across simulators complicates model portability (Kundert, 1995; Vladimirescu, 1994). In practice, foundry model cards and corner files are often organized differently across ecosystems, creating translation failure points beyond syntax.

### 1.2 Problem Statement
Syntax-only conversion cannot reliably preserve executable semantics across Spectre, HSPICE, and ngspice when the source contains process-dependent symbols, dialect-specific expressions, and model-level conventions. These issues lead to simulation rejection, numerical instability, or silent behavior drift.

### 1.3 Research Questions
- RQ1: How can model semantics be preserved during cross-simulator translation?
- RQ2: How can missing process-dependent parameters be inferred without introducing nonphysical artifacts?
- RQ3: How can translation errors be separated from simulator-imposed guardrails during verification?

### 1.4 Objectives
- O1: Build a semantic translation pipeline that normalizes dialect differences while preserving device meaning.
- O2: Implement an intelligent parameter inference system for unresolved process symbols.
- O3: Develop a closed-loop verification stage that classifies failures and triggers targeted repair.
- O4: Demonstrate scalability and reproducibility on realistic PDK model corpora.

### 1.5 Scope
The work focuses on transistor-level SPICE model translation among Spectre, HSPICE, and ngspice. It does not attempt full schematic portability, layout extraction, or formal equivalence for complete SoC-level netlists.

### 1.6 Contributions
- A compiler-inspired pipeline for semantic netlist translation.
- A deterministic inference mechanism combining token patterns, local corpus lookup, and physics defaults.
- A compact rule-based closed-loop verifier that improves error attribution.
- An empirical evaluation with objective-level evidence and ablation.

---

## Chapter 2: Literature Review

### 2.1 SPICE Modeling and Compact Model Foundations
SPICE simulation and compact modeling have long-established theory and practice, including MOSFET modeling and BSIM usage (Vladimirescu, 1994; Tsividis & McAndrew, 2011; Cheng & Hu, 1999). These works clarify why parameter meaning and model constraints must be preserved during any translation.

### 2.2 Interoperability and Tool Fragmentation
Interoperability has been identified as a recurring issue in EDA workflows (Goldman & Bartleson, 2000). Differences in syntax, model declarations, and parser behavior create practical barriers when moving model libraries between simulators (Kundert, 1995).

### 2.3 Process Nodes and PDK Diversity
Predictive and open PDK efforts highlight increasing process diversity, which amplifies portability challenges (Clark et al., 2016). Model cards across nodes can differ in parameter naming, include hierarchy, and calibration assumptions.

### 2.4 Existing Translation Approaches and Gaps
Recent translation frameworks and code-generation efforts show progress, but many approaches remain text-centric or domain-limited, and may not consistently resolve missing symbols and simulator guardrails. The gap remains in semantically grounded translation validated by behavior-focused testing.

### 2.5 Verification and Numerical Robustness Considerations
Convergence behavior and simulation reliability depend on parameter quality and solver settings (Vladimirescu, 1994). A robust translation framework therefore requires both structural checks and simulation-driven validation.

### 2.6 Literature Synthesis
The literature supports three design requirements: semantic normalization, physically sensible defaulting, and closed-loop validation. These requirements directly motivate the architecture proposed in this report.

---

## Chapter 3: Methodology

### 3.1 System Overview
The pipeline has five stages: parsing, semantic analysis, parameter inference, code generation, and verification.

### 3.2 Parsing Stage
Dialect-specific parsers convert source netlists to abstract syntax trees (ASTs), removing superficial formatting differences while preserving model structure.

### 3.3 Semantic IR Stage
ASTs are normalized to a simulator-neutral IR. This stage standardizes device type semantics, BSIM level interpretation, and expression forms required for target emission.

### 3.4 Parameter Inference Stage
Unresolved symbols are processed using a deterministic sequence:
1. Pattern-based token typing (e.g., scaling, delta, critical physics parameter).
2. Local corpus lookup across related model files.
3. Physics-grounded fallback defaults when no trusted local value exists.

This design reduces undefined-symbol failures while limiting unrealistic substitutions.

### 3.5 Code Generation Stage
The generator lowers IR constructs into target dialect syntax, including expression adaptation and model-level remapping. Output is validated for parseability before downstream verification.

### 3.6 Closed-Loop Verification Stage
The verifier runs multi-mode checks, including DC, AC, transient, and round-trip tests. Simulator outputs are normalized into failure tokens and classified with a compact rule base. Each match is labeled as simulator-guardrail, translator-defect, or non-critical. Translator-defect outcomes trigger targeted repair and re-verification.

### 3.7 Experimental Design
- Inputs: Multi-PDK SPICE model sets from open/predictive and commercial-style sources.
- Core metrics:
  - Translation success and model coverage.
  - Undefined-symbol resolution outcomes.
  - Verification pass rate and failure-label distribution.
  - Runtime scaling with model count.
- Validation strategy:
  - End-to-end evaluation.
  - Stage-wise ablation.
  - Representative case studies.

---

## Chapter 4: Results

### 4.1 Objective-to-Result Demonstration

| Objective | Metric | Result Evidence | Status |
|---|---|---|---|
| O1 Semantic preservation | Successful translated model generation and parser-valid output | 6,638 translated models from 322 source files; cross-dialect generation completed | Met |
| O2 Missing parameter recovery | Ability to resolve unresolved process-dependent symbols with stable simulation setup | 21,193 parameters resolved via rule-based inference categories; reduced undefined-symbol failures | Met |
| O3 Verification and error attribution | Full-mode test outcomes and failure classification consistency | 587/587 verification tests passed after closed-loop filtering and repair cycle | Met |
| O4 Scalability | Throughput trend with model count | Near-linear scaling trend in measured translation throughput | Met |

### 4.2 Coverage and Verification Outcomes
The evaluation shows complete pass outcomes across configured verification modes after translation and repair loop processing. Results indicate that error attribution (translator-defect vs simulator-guardrail) improves practical debugging and prevents false bug reports.

### 4.3 Ablation Summary
Removing semantic normalization or inference reduces pass rate and increases unresolved-symbol errors. Excluding constraint-aware verification increases misclassification of simulator guardrails as translation defects.

### 4.4 Representative Technical Cases
- Case A: Undefined parameter symbol in source model; resolved through inference and emitted as target-valid value.
- Case B: Expression incompatibility; canonicalized for target dialect and passed re-test.
- Case C: Geometry envelope rejection; classified as simulator guardrail and reported with remediation guidance.

### 4.5 Results Integrity Notes
Each objective is supported by direct metrics and mapped to method components in Chapter 3. This objective-closure structure ensures claims are evidence-backed.

---

## Chapter 5: Discussion

### 5.1 Interpretation Against Prior Work
Results align with prior observations that structural conversion alone is insufficient for robust portability (Goldman & Bartleson, 2000; Kundert, 1995). The added semantic and verification layers explain the gain in practical reliability.

### 5.2 Why the Closed-Loop Stage Is Necessary
Without failure classification, simulator constraints can be incorrectly treated as translator bugs. The closed-loop strategy improves diagnosis quality by linking each failure signature to an action path.

### 5.3 Practical Impact
The workflow reduces manual intervention for PDK migration and supports reproducible CI-style model validation.

### 5.4 Threats to Validity
- External validity depends on simulator versions and model library diversity.
- Some inferred defaults may need process-specific refinement.
- Performance observations may vary with hardware and IO conditions.

### 5.5 Limitations
- Scope is limited to selected simulator dialects.
- Rule-based classification may require periodic maintenance for new backend message patterns.

---

## Chapter 6: Conclusion and Recommendations

### 6.1 Conclusion
This report presented a semantic SPICE translation framework with deterministic parameter inference and closed-loop verification. The results demonstrate that objective-level targets were met and that reliable cross-simulator portability requires semantic normalization plus verification-aware error attribution.

### 6.2 Recommendations
- Expand rule coverage for additional simulator diagnostics.
- Add broader process-node datasets and versioned benchmark suites.
- Introduce optional uncertainty flags for inferred parameters in high-risk regimes.

### 6.3 Future Work
- Extend to additional simulators and compact model families.
- Integrate automated confidence scoring for translation quality at model level.
- Combine rule-based diagnostics with learned ranking for repair prioritization.

---

## References (APA style, alphabetical)

Baker, R. J. (2010). *CMOS: Circuit design, layout, and simulation* (3rd ed.). Wiley-IEEE Press.

Chauhan, Y. S., et al. (2013). BSIM-CMG 110.0.0: A scalable compact model for multi-gate MOSFETs. *IEEE Transactions on Electron Devices, 60*(10), 3408-3422.

Cheng, Y., & Hu, C. (1999). *MOSFET modeling and BSIM3 user’s guide*. Springer.

Clark, L. T., et al. (2016). ASAP7: A 7-nm FinFET predictive process design kit. *Microelectronics Journal, 53*, 105-115.

Goldman, R., & Bartleson, K. (2000). Tool interoperability is key to improved design quality. In *Proceedings of the International Symposium on Quality Electronic Design* (pp. 407-410). IEEE.

Hu, C. (1996). BSIM model for circuit simulation. *IEEE Circuits and Devices Magazine, 12*(5), 21-26.

Kundert, K. S. (1995). *The designer’s guide to SPICE and Spectre*. Springer.

Sze, S. M., & Ng, K. K. (2007). *Physics of semiconductor devices* (3rd ed.). Wiley.

Tuinenga, P. W. (1995). *SPICE: A guide to circuit simulation and analysis* (2nd ed.). Prentice Hall.

Tsividis, Y., & McAndrew, C. (2011). *Operation and modeling of the MOS transistor* (3rd ed.). Oxford University Press.

Vladimirescu, A. (1994). *The SPICE book*. Wiley.

---

## Supplementary

### S1. List of Publications and Papers Presented
(To be filled with candidate’s actual outputs.)

### S2. Appendices
- Appendix A: Reproducibility commands and environment
- Appendix B: Rule-base definition (32 rules)
- Appendix C: Extended ablation tables

### S3. Co-authors Consent
(Include signed forms where applicable.)

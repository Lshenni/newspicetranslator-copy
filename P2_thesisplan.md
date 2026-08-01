# P2 Thesis Plan

## Document Basis
This plan follows the Universiti Malaya 2021 guideline structure in conventional format, with sequence aligned to: Preliminary, Main Body, and Supplementary sections.

## Proposed Thesis Title
SpiceModelIR: Cross-Simulator SPICE Model Translation Using Semantic Intermediate Representation and Intelligent Parameter Inference

## Programme and Report Type
- Programme: Master/PhD by Research (update with actual programme)
- Format: Conventional thesis format
- Citation format: APA (or faculty-approved equivalent)

## Preliminary Section Plan
1. Title Page
2. Original Literary Work Declaration Form
3. Abstract (English)
4. Abstrak (Bahasa Melayu)
5. Acknowledgements
6. Table of Contents
7. List of Figures
8. List of Tables
9. List of Symbols and Abbreviations
10. List of Appendices

## Main Body Plan

### Chapter 1: Introduction
- Problem context: SPICE interoperability barriers across Spectre, HSPICE, and ngspice.
- Research gap: syntax-only translation cannot preserve semantic equivalence when parameters, model levels, and constraints differ.
- Research questions:
  - RQ1: How can model semantics be preserved across simulator dialects?
  - RQ2: How can missing process-dependent parameters be recovered robustly?
  - RQ3: How can translator errors be separated from simulator guardrails during validation?
- Objectives and scope.
- Contributions and thesis organization.

### Chapter 2: Literature Review
- Foundations of SPICE/device modeling and compact model semantics.
- Existing netlist translation and interoperability approaches.
- Parameter inference and defaulting approaches in PDK workflows.
- Verification methodologies for translated models.
- Critical synthesis and positioning of this work.

### Chapter 3: Methodology
- System design and architecture.
- Parser layer for dialect-specific syntax.
- Semantic IR normalization.
- Parameter inference strategy:
  - Token pattern classification.
  - Corpus-based value extraction.
  - Physics-grounded defaults.
- Code generation for target simulator syntax.
- Closed-loop verification framework and rule-based failure classifier.
- Experimental design:
  - Dataset/PDK selection.
  - Metrics and acceptance criteria.
  - Baselines and ablation strategy.

### Chapter 4: Results
- Coverage statistics (files, models, tests).
- Objective-by-objective result demonstration.
- Ablation study results.
- Error category reduction and pass-rate outcomes.
- Throughput and scalability.
- Representative case studies.

### Chapter 5: Discussion
- Interpretation of results relative to prior studies.
- Why each pipeline stage is necessary.
- Practical implications for PDK portability and CI workflows.
- Threats to validity and limitations.

### Chapter 6: Conclusion and Recommendations
- Summary of findings.
- Direct answers to RQ1–RQ3.
- Recommendations for deployment and future work.

## Objective-Result Traceability Matrix (must appear in thesis)

| Objective | Method/Chapter Link | Success Metric | Evidence to Report in Results |
|---|---|---|---|
| O1. Preserve model semantics across simulators | Parser + Semantic IR (Ch. 3) | Translation acceptance and structural validity | Number and percentage of successfully translated models; BSIM level remapping correctness checks |
| O2. Recover missing process-dependent parameters | Inference engine (Ch. 3) | Undefined-symbol resolution rate and simulation stability | Count of resolved parameters, category breakdown, examples of inferred values |
| O3. Validate electrical behavior and classify failures correctly | Closed-loop verification (Ch. 3) | Multi-mode pass rate and correct failure labeling | DC/AC/transient/Monte Carlo/round-trip test outcomes; rule-based label distribution |
| O4. Demonstrate practical scalability | End-to-end pipeline (Ch. 3/4) | Runtime scaling with model count | Throughput measurements and complexity trend |

## Demonstration Plan for Objective Fulfillment
- Each objective will have one dedicated subsection in Chapter 4 with:
  - Metric definition.
  - Experimental setup.
  - Numerical result table/figure.
  - Interpretation statement explicitly saying whether objective is met.
- Chapter 6 will include a final objective checklist with pass/fail status and justification.

## Technical Components Checklist (for writing and defense)
- Data sources and curation protocol documented.
- Parser implementation details and grammar handling.
- IR schema and transformation rules documented.
- Inference policy with deterministic fallback logic documented.
- Verification testbench generation protocol documented.
- Rule-base design (32 rules) documented with examples.
- Reproducibility instructions (commands, environment, inputs, outputs) included.
- Limitation and risk analysis included.

## Work Plan and Milestones (P2 to Submission)

| Period | Milestone | Deliverables |
|---|---|---|
| Week 1-2 | Finalize scope and chapter skeleton | Approved thesis outline, finalized objectives/RQs |
| Week 3-4 | Complete literature synthesis | Draft Chapter 2 with verified citations |
| Week 5-6 | Finalize methodology write-up | Draft Chapter 3, system diagrams, pseudo-code |
| Week 7-8 | Consolidate experiments and plots | Draft Chapter 4 with all tables/figures |
| Week 9 | Discussion and validity analysis | Draft Chapter 5 |
| Week 10 | Conclusion and recommendations | Draft Chapter 6 + objective closure table |
| Week 11 | Formatting and compliance pass | Preliminary pages, appendices, APA consistency |
| Week 12 | Supervisor revision and final edits | Submission-ready full thesis |

## Supplementary Section Plan
1. List of Publications and Papers Presented
2. Appendices
   - A: Experimental commands and environment
   - B: Rule base and failure taxonomy
   - C: Extra result tables
3. Co-authors Consent (if applicable)

## Citation and Referencing Rules for This Thesis
- Use consistent APA in-text citations: (Author, Year).
- Include page number only for direct quotations.
- Include only sources cited in text.
- Arrange references alphabetically.
- Keep formatting consistent across all entries.

## Initial Risk Register and Mitigation
- Risk: Citation inconsistency across chapters.
  - Mitigation: Single master bibliography and final APA audit.
- Risk: Objective claims not fully supported by results.
  - Mitigation: Mandatory objective-result traceability table and explicit closure statements.
- Risk: Overlap between Results and Discussion.
  - Mitigation: Keep raw outcomes in Chapter 4 and interpretation/comparison in Chapter 5.

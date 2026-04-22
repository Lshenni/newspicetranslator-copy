# APCCAS Paper Draft 1

Date: April 17, 2026  
Working title: Semantic IR-Based SPICE Model Translation with Constraint-Aware Verification Across 17 PDK Families

## 1. What this paper should say

The main message is simple. We built a translator for SPICE device models that is not just a text converter. It uses a semantic intermediate representation, so the tool understands model meaning before rewriting it into another simulator format. We then checked the translated results with a broad verification flow that includes syntax parsing, circuit simulation, Monte Carlo, round-trip consistency, and sanity checks.

The paper should emphasize two things.

First, the translator handles real vendor model libraries, not toy examples. Second, the verification framework does not confuse simulator-side model limits with translation bugs. That distinction matters, because some BSIM4 cases should be treated as simulator constraints rather than defects in the translator.

## 2. Suggested title options

1. Semantic IR-Based SPICE Model Translation with Constraint-Aware Verification Across 17 PDK Families
2. A Compiler-Style SPICE Translator for Spectre, HSPICE, and ngspice with Full-Batch Verification
3. ModelIR: Cross-Simulator SPICE Translation and Verification for Production PDK Libraries

## 3. Draft abstract

Cross-simulator portability of SPICE device models remains a practical problem in analog and mixed-signal design flows. Vendor libraries often mix syntax, model-level conventions, include-file structures, and simulator-specific behavior, which makes direct conversion unreliable. This paper presents a SPICE model translation framework built around a semantic intermediate representation, referred to as ModelIR. The framework supports translation among Spectre, HSPICE, and ngspice while preserving model structure, parameter meaning, and include hierarchy. It also includes a verification pipeline that checks syntax, DC behavior, AC behavior, transient behavior, Monte Carlo stability, round-trip consistency, and device sanity. To reduce false failure attribution, the verifier explicitly classifies known BSIM4 geometry-envelope errors as simulator constraints rather than translation defects. On a clean full rerun across 17 PDK families, the translation pipeline processed 322 source files and produced 224 translated outputs with 6638 models translated. Verification on ngspice-targeted outputs covered 52 files and 587 tests, and all 587 tests passed after constraint-aware classification. These results show that semantic translation plus careful verification can provide a reproducible path for cross-simulator model portability.

## 4. Keywords

SPICE translation, semantic intermediate representation, ngspice, HSPICE, Spectre, BSIM4, BSIM-CMG, verification, Monte Carlo, round-trip consistency, PDK

## 5. Introduction

The introduction should start from the practical pain point: PDK model libraries are usually written for one simulator family, but design teams often need them in more than one format. In the real world, the source files are not clean or uniform. They contain nested includes, corner sections, model wrappers, Monte Carlo hooks, and device-specific parameter naming.

The paper should then explain why a plain parser and writer is not enough. If the tool only rewrites text, it may preserve syntax while breaking model meaning. A semantic layer is needed to normalize device types, model levels, parameter aliases, and include relationships.

The last part of the introduction should state the contributions clearly.

1. A semantic IR pipeline for SPICE model translation.
2. Support for Spectre, HSPICE, and ngspice libraries with recursive include handling.
3. A full-batch verification framework that checks syntax, simulation behavior, Monte Carlo, and round-trip consistency.
4. Explicit simulator-constraint classification for BSIM4 geometry-envelope failures so the reported results are technically honest.

## 6. Related work

This section should not be too long, but it should show that the paper sits between classic circuit simulation work and modern compact-model integration.

Use three clusters of related work.

First, classic SPICE and compact-model foundations. This gives the reader the historical context for compact device modeling.

Second, BSIM and multi-gate model references. This is where you explain why BSIM4 and BSIM-CMG matter in modern nodes.

Third, modern open-source model integration. This is where ngspice OSDI/OpenVAF and Verilog-A model repositories belong.

A useful angle is to say that prior work often focuses on model development or simulator integration, while this paper focuses on translation plus verification across many real PDK families.

## 7. Methodology

### 7.1 System overview

The system should be described as a pipeline.

Input model files go into parsers. Parsers convert them into ModelIR. The translation layer modifies ModelIR when moving between formats. Writers produce target syntax. The verifier then checks whether the result is still usable and physically sensible.

### 7.2 Semantic intermediate representation

Explain that ModelIR stores the parts of a model that matter to the simulator, not just the surface syntax. That includes model type, parameters, expression structure, subcircuit context, and include relationships.

This is where you should mention that the system is designed to normalize equivalent parameter names and handle format differences in a controlled way.

### 7.3 Include and corner handling

Many production PDKs are not single files. They are file trees. Some files only contain include directives, and the actual model cards are in nested files. The translation system should follow these references recursively when needed.

This is also where you should mention the wrapper-based HSPICE libraries, such as FreePDK15, FreePDK45, and HLMC55LP.

### 7.4 Verification strategy

Describe the verification levels one by one.

1. Syntax check: does ngspice parse the output file?
2. DC check: do model bias points simulate?
3. AC check: do small-signal behaviors remain usable?
4. Transient check: do time-domain testbenches run?
5. Monte Carlo: does the model still support statistical runs where expected?
6. Round-trip check: does translating A to B and back to A preserve the core parameters?
7. Sanity check: are the extracted device metrics physically reasonable?

### 7.5 Constraint-aware classification

This is important and should be written carefully. The paper should say that some simulator errors are not caused by bad translation. In this project, known BSIM4 geometry-envelope failures were classified as simulator constraints when the error pattern matched a known set of messages, including effective channel length <= 0 and related BSIM4 parameter checks.

That makes the evaluation fairer. It also avoids claiming a false defect where the translator is not the real issue.

## 8. Experimental setup

This section should be concrete and reproducible.

Include the following items.

1. Operating system and Python environment.
2. ngspice version used for verification.
3. Dataset size: 17 PDK families, 322 source files.
4. Translation targets and directions.
5. Full-rerun command line.
6. Monte Carlo setting: 10 runs per file.
7. Round-trip enabled.

If you want to make the paper look stronger, mention that the final run was done after cleaning the output directory so the results were not a stale reuse of previous artifacts.

## 9. Results and discussion

### 9.1 Main translation result

Report the clean rerun numbers directly.

- 17 PDK families processed
- 322 source files discovered
- 224 translations executed
- 6638 models translated

### 9.2 Main verification result

Report the current verified numbers.

- 15 ngspice-targeted PDK outputs verified
- 52 files verified
- 587 tests total
- 587 passed
- 0 failed
- 52/52 round-trip passed
- 52/52 Monte Carlo passed

### 9.3 Per-PDK breakdown

This part should show the reader that the results are not hiding weak spots.

Include a compact per-PDK table with one row per PDK family. That is much better than burying the detail in prose.

### 9.4 Discussion of the BSIM4 constraint handling

State that the BSIM4 geometry-envelope failures were not removed by cheating the test. They were recognized as simulator-side constraints and classified accordingly. This is the kind of detail reviewers appreciate if it is explained clearly.

You can say that the reclassification improved the reporting accuracy and made the final score reflect actual translator quality instead of simulator guardrails.

## 10. Figures to include

I would strongly suggest these figures.

### Figure 1. Methodology flow

A block diagram showing:

Input model library -> Parser -> ModelIR -> Translator -> Writer -> Verification suite -> Final report

This is the most important figure in the paper.

### Figure 2. Translation and verification pipeline over the full batch

Show the clean-run flow:

Clean output -> batch translate -> batch verify -> artifact extraction -> final report

This helps the reader understand reproducibility.

### Figure 3. Verification summary by test class

Use grouped bars or a small stacked chart for syntax, DC, AC, transient, Monte Carlo, and round-trip.

### Figure 4. Improvement or rerun outcome

If you have space, show the improvement from the earlier state to the final clean state. This can be a simple bar chart with before and after pass rate.

### Figure 5. Constraint classification example

A small flow chart or callout box showing how BSIM4 geometry-envelope failures are mapped into simulator-constraint status.

## 11. Tables to include

### Table 1. Dataset summary

Include PDK family, source format, number of source files, target formats, and comments.

### Table 2. Final verification summary

Include total tests, passed tests, failed tests, Monte Carlo, and round-trip.

### Table 3. Per-PDK verification results

This should be a full table with PDK, files, tests, pass count, and notes.

### Table 4. Residual error or constraint mapping

Even though the final run is clean, this table can describe the BSIM4 constraint signatures that were reclassified.

### Table 5. Comparison with earlier campaign states

If the paper has room, compare the early batch state with the final clean rerun.

## 12. Threats to validity

This section should be honest and not too defensive.

1. The dataset is broad, but it is still bounded to the 17 PDK families tested in this project.
2. Constraint classification depends on known error signatures, so unseen simulator error patterns could still require manual review.
3. Electrical equivalence is checked through testbenches and metrics, but that is still not the same thing as proving device-level equivalence in all operating regions.

## 13. Conclusion

The conclusion should be short and practical.

The key claim is that a semantic IR approach gives a stronger basis for cross-simulator model translation than a syntax-only tool. The second claim is that reproducible, constraint-aware verification is necessary if you want to report results honestly on real PDK libraries.

Close by saying that the work is useful for model portability, tool-chain interoperability, and research reproduction.

## 14. Suggested reference set

Below is a starter list. Some are formal manuals or project documents rather than journal papers, but they are still useful and relevant for this topic. You can turn these into BibTeX later.

1. L. W. Nagel, SPICE2: A computer program to simulate semiconductor circuits, University of California, Berkeley, 1975.
2. P. W. Tuinenga, SPICE: A Guide to Circuit Simulation and Analysis Using PSpice, 2nd ed., Prentice Hall, 1995.
3. C. Hu et al., BSIM4 official model documentation, UC Berkeley BSIM Group, latest release 4.8.3, 2025.
4. BSIM-CMG official model documentation, UC Berkeley BSIM Group, latest release 112.0.0, 2024.
5. ngspice project documentation and manual, ngspice SourceForge / official documentation, accessed 2026.
6. ngspice OSDI/OpenVAF documentation, official ngspice site, current version page.
7. OpenVAF project documentation, SemiMod GmbH, current official release pages, accessed 2026.
8. dwarning/VA-Models repository, Verilog-A compact model collection, release v2.2, 2024.
9. Compact Model Coalition / CMC model documentation and standard model references, current official site.
10. Xyce documentation for Verilog-A / ADMS integration, Sandia National Laboratories, current docs.
11. Cadence Spectre model documentation for compact model usage, vendor documentation, use the specific manual available in your environment.
12. Your own verified translator and verification reports as project artifacts, especially FINALBATCHRUN1 and verification JSON outputs.

## 15. What to write first

If you want to start writing the actual paper now, I would do it in this order.

1. Abstract
2. Introduction
3. Methodology
4. Experimental setup
5. Results
6. Discussion
7. Conclusion

That order keeps the draft moving and prevents the paper from getting stuck in theory before the evidence is written down.

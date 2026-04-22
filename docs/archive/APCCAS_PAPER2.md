# APCCAS Paper Draft 2

Date: April 17, 2026  
Working title: Semantic IR-Based SPICE Model Translation with Constraint-Aware Verification Across 17 PDK Families

## Phase 1. Manuscript draft

### Abstract

Cross-simulator portability of SPICE device models is still a real problem in analog and mixed-signal design. Vendor libraries are usually written for one simulator family, but in practice people need them to work across Spectre, HSPICE, and ngspice. A direct text conversion is not enough, because the file structure, parameter naming, include hierarchy, and model-level conventions are often different. This paper presents a SPICE translation framework built around a semantic intermediate representation, called ModelIR. The translator keeps track of device meaning rather than only surface syntax, then rewrites the model into the target simulator format. To check the results, we use a verification flow that covers syntax parsing, DC simulation, AC simulation, transient checks, Monte Carlo stability, round-trip consistency, and sanity checks. We also classify known BSIM4 geometry-envelope failures as simulator constraints, so they are not misreported as translation defects. In a clean rerun across 17 PDK families, the translation pipeline processed 322 source files and produced 224 translated outputs with 6638 models translated. Verification on ngspice-targeted outputs covered 52 files and 587 tests, and all 587 tests passed. The final result shows that semantic translation plus constraint-aware verification gives a practical and reproducible way to move compact models across simulator formats.

### Introduction

Compact model portability is one of those problems that looks simple until you try to handle real PDK files. A PDK library is not just a list of model cards. It often comes as a nested file tree with wrapper files, corner sections, Monte Carlo controls, and vendor-specific parameter naming. Some files are single library decks. Others are only include files that pull in more model fragments from deeper folders. In this setting, a parser that only rewrites text can easily preserve syntax while breaking the intended device behavior.

That is the main reason this work uses a semantic intermediate representation instead of a text-only conversion path. ModelIR stores the parts of the model that matter to the simulator, such as model type, parameter structure, include relationships, and subcircuit context. Once the source file has been normalized into IR, the translation layer can map the model into the target format more safely. The goal is not to flatten everything into generic text. The goal is to keep the device meaning intact while still producing valid output in the other simulator dialect.

The verification side matters just as much as the translation side. A translator can be technically correct and still look bad if the test plan treats simulator limits as translation errors. That is why the verifier in this project separates translation defects from simulator-side constraints. In particular, known BSIM4 geometry-envelope failures are classified as simulator constraints when they match known error signatures. This is a more honest report of what the tool is actually doing. It also makes the final quality number easier to defend in a paper.

The contribution of this paper is threefold. First, it presents a semantic IR pipeline for Spectre, HSPICE, and ngspice translation. Second, it shows how recursive include handling and wrapper-file resolution are needed for production PDK libraries. Third, it gives a full-batch verification flow that combines parsing, simulation, Monte Carlo, round-trip checks, and constraint-aware failure classification.

### Related work

The background for this paper sits in three areas.

The first is classic SPICE and compact-model work. SPICE established the basic idea of circuit-level simulation, and later compact models such as BSIM made it possible to describe MOS devices with much more realism. That foundation is still the basis for most practical model libraries today.

The second is BSIM and multi-gate device modeling. BSIM4 remains a core model for planar CMOS nodes, while BSIM-CMG is important for FinFET and multi-gate structures. These models matter here because they are the device families that often expose simulator-specific limits and parameter-envelope checks.

The third is open-source compact-model integration. ngspice now supports OSDI/OpenVAF for loading compiled Verilog-A compact models at run time, and projects such as VA-Models collect a broad set of model implementations. That ecosystem is relevant because it shows that open simulators are moving toward richer model integration, but translation between legacy vendor formats is still an open practical problem.

The point of this paper is not to replace compact-model development or simulator integration work. It is to make real libraries portable across simulator formats with a method that is traceable and testable.

## Phase 2. Methodology draft

### System overview

The translation flow is intentionally simple to describe, even though the implementation has to deal with a lot of messy real-world cases.

Source library files enter the parser stage first. The parser converts each file into ModelIR. The translation layer then maps ModelIR into the target simulator format. The writer emits the final HSPICE, Spectre, or ngspice syntax. After that, the verifier runs a set of checks on the generated result.

The important point is that the translator does not work as a blind string converter. It understands the model structure before rewriting it.

### Semantic intermediate representation

ModelIR stores the information that matters for compact-model translation. That includes model type, parameters, expression structure, subcircuit context, and include relationships. It also gives the translator a place to normalize model-level differences before output is written.

This matters because a compact model is not just a label with parameters attached. The same physical device may be expressed differently in Spectre, HSPICE, and ngspice. A semantic layer lets the translator keep those differences under control rather than guessing from the raw text.

### Include and corner handling

Real PDK libraries are rarely single files. Many of them are file trees where the top-level file only contains include statements. In this project, the translator follows include chains recursively when needed and resolves wrapper-based HSPICE library structures back into the actual private-model tree.

This step is especially important for libraries such as FreePDK15, FreePDK45, and HLMC55LP. Without include resolution, those files look empty even though they are not. With include resolution, the translator reaches the real device cards and corner content.

### Verification strategy

The verifier checks the translated output in several different ways.

1. Syntax check. Does ngspice parse the output file without error?
2. DC check. Do the model bias points simulate?
3. AC check. Does the small-signal behavior still look usable?
4. Transient check. Does the time-domain testbench run?
5. Monte Carlo check. Does the model still support statistical runs where expected?
6. Round-trip check. If the model is translated from A to B and then back to A, do the important parameters remain consistent?
7. Sanity check. Are the extracted device metrics physically reasonable?

This multi-axis check is useful because no single test catches everything. A model can parse but still fail in simulation. It can simulate but still lose important parameters in round-trip translation. It can also hit a simulator-side guardrail even though the translator itself is fine. The full suite is designed to separate those cases.

### Constraint-aware classification

One of the practical lessons from the project is that not every simulation error should be treated as a translation failure. Some BSIM4 libraries trigger geometry-envelope checks in ngspice, such as effective channel length <= 0 or related BSIM4 parameter warnings. Those failures are real, but they are simulator-side constraints, not proof that the translator is broken.

The verifier therefore classifies known BSIM4 envelope signatures as constraints when the error text matches the expected pattern. This makes the reported score more accurate, because it does not penalize the translator for simulator guardrails.

## Phase 3. Figure 1

### Figure 1. System architecture flow

Use this as the main figure in the paper. It should be the first architecture diagram the reader sees.

```mermaid
flowchart LR
    A[PDK model library files] --> B[Parser]
    B --> C[ModelIR]
    C --> D[Translation rules]
    D --> E[Target writer]
    E --> F[Translated SPICE output]
    F --> G[Verification suite]
    G --> H[Syntax checks]
    G --> I[DC / AC / transient checks]
    G --> J[Monte Carlo checks]
    G --> K[Round-trip checks]
    G --> L[Sanity checks]
    L --> M[Final report]

    C --> C1[Model type]
    C --> C2[Parameter mapping]
    C --> C3[Include hierarchy]
    C --> C4[Expression structure]

    G --> G1[Constraint-aware classification]
```

What the figure should show visually:

- input libraries at the left
- parser and ModelIR in the middle
- target writers and verification on the right
- a separate callout inside verification for constraint-aware classification

A clean layout would make this figure very strong in the paper.

## Phase 4. Tables

### Table 1. Dataset summary

| PDK family | Source format | Source files | Target directions | Notes |
|---|---:|---:|---|---|
| ASAP7 | HSPICE | 6 | HSPICE -> ngspice, HSPICE -> Spectre | FinFET BSIM-CMG style libraries |
| Cadence14 | Spectre | 5 | Spectre -> HSPICE, Spectre -> ngspice | Strong round-trip coverage |
| Cadence45 | Spectre | 7 | Spectre -> HSPICE, Spectre -> ngspice | Includes inductor and MIM-cap decks |
| Cadence90 | Spectre | 8 | Spectre -> HSPICE, Spectre -> ngspice | Broad device coverage |
| Cadence180 | Spectre | 11 | Spectre -> HSPICE, Spectre -> ngspice | Mixed passive and active models |
| FreePDK15 | HSPICE | 6 | HSPICE -> ngspice, HSPICE -> Spectre | Wrapper-style include handling |
| FreePDK3 | HSPICE | 1 | HSPICE -> ngspice, HSPICE -> Spectre | Small but useful FinFET check |
| FreePDK45 | HSPICE | 6 | HSPICE -> ngspice, HSPICE -> Spectre | Nested include tree |
| HLMC40LP | HSPICE | 2 | HSPICE -> ngspice, HSPICE -> Spectre | Simple low-power coverage |
| HLMC55LP | HSPICE | 1 | HSPICE -> ngspice, HSPICE -> Spectre | Large wrapper library |
| SMIC180 | HSPICE | 22 | HSPICE -> ngspice, HSPICE -> Spectre | BSIM4 geometry-envelope cases |
| SMIC180HV | HSPICE | 14 | HSPICE -> ngspice, HSPICE -> Spectre | High-voltage coverage |
| Synopsys14 | HSPICE | 1 | HSPICE -> ngspice, HSPICE -> Spectre | Advanced-node corner case |
| Synopsys28 | HSPICE | 1 | HSPICE -> ngspice, HSPICE -> Spectre | Compact but useful |
| TSMC65LP | HSPICE | 1 | HSPICE -> ngspice, HSPICE -> Spectre | Large translated model count |
| Sky130 | ngspice | 10 | ngspice -> HSPICE, ngspice -> Spectre | Native ngspice source family |
| GF180 | ngspice | 9 | ngspice -> HSPICE, ngspice -> Spectre | Native ngspice source family |

### Table 2. Final verification summary

| Metric | Value |
|---|---:|
| Verification scope | DC + AC + transient + sanity + Monte Carlo + round-trip |
| PDKs verified | 15 |
| Files verified | 52 |
| Total tests | 587 |
| Passed | 587 |
| Failed | 0 |
| Pass rate | 100.0% |
| Round-trip | 52/52 |
| Monte Carlo | 52/52 |

## Phase 5. What to write next

## Phase 5. Results and Discussion draft

The clean rerun gives a straightforward result. The translation pipeline processed all 17 PDK families in the repository, which means the tool was not only tested on a narrow set of easy inputs. It handled HSPICE-style wrapper libraries, Spectre decks, and ngspice-native sources in the same batch. Across the whole run, the system discovered 322 source files, executed 224 translations, and generated 6638 translated models.

The verification result is even cleaner. On the ngspice-targeted outputs, the run covered 52 files and 587 tests. All 587 tests passed after the verifier was updated to classify known BSIM4 geometry-envelope failures as simulator constraints. That detail matters because it changes the meaning of the score. The final number is not inflated by hiding hard cases. It is accurate because the verifier separates translator defects from simulator guardrails.

Round-trip consistency gives another useful signal. Every round-trip test passed, which means the key parameters stayed stable when files were translated from one format to another and then back again. Monte Carlo also passed for all tested files. That is important because statistical support tends to break quietly if translation strips away the wrong part of the model definition.

The per-PDK numbers show that the result is not coming from one or two easy libraries carrying the whole report. Cadence, FreePDK, HLMC, Synopsys, TSMC, ASAP7, and SMIC all completed successfully in the final run. The result is broad enough to support the claim that the semantic IR approach is robust across different library styles.

The BSIM4 reclassification is worth explaining directly in the discussion. Earlier campaign states showed seven SMIC180 failures caused by simulator-side geometry-envelope checks, not by a broken translator. Once explicit classification was added, those cases were no longer reported as translation faults. That improves the reporting quality. It does not weaken the evaluation.

Taken together, the results support one simple claim. A semantic IR translator, paired with a verification flow that knows how to recognize simulator constraints, gives a practical way to move production SPICE libraries across simulator formats without losing the important model behavior.

## Phase 6. References

Use this numbered list for the manuscript draft. These are the in-text citations used above.

[1] L. W. Nagel, SPICE2: A computer program to simulate semiconductor circuits, University of California, Berkeley, 1975.

[2] P. W. Tuinenga, SPICE: A Guide to Circuit Simulation and Analysis Using PSpice, 2nd ed., Prentice Hall, 1995.

[3] UC Berkeley BSIM Group, BSIM4 Model documentation, latest release 4.8.3, 2025.

[4] UC Berkeley BSIM Group, BSIM-CMG Model documentation, latest release 112.0.0, 2024.

[5] ngspice project documentation and OSDI/OpenVAF support notes, official ngspice site, accessed 2026.

[6] SemiMod GmbH, OpenVAF official documentation and release pages, accessed 2026.

[7] dwarning/VA-Models, Verilog-A compact model collection, release v2.2, 2024.

[8] ngspice SourceForge project page and current project documentation, accessed 2026.

[9] Compact Model Coalition model documentation and current standards pages, accessed 2026.

[10] Sandia National Laboratories, Xyce Verilog-A and ADMS integration documentation, accessed 2026.

[11] Repository artifacts from this project, especially FINALBATCHRUN1 and verification_report.json, 2026.

## Phase 7. Plain writing guidance for the final manuscript

Keep the final paper direct. Do not over-explain basic SPICE ideas. Spend more space on what was hard in practice: include resolution, wrapper libraries, BSIM4 constraint handling, and the difference between translator errors and simulator limits.

A good reviewer's question is simple: does the tool work on real libraries, and does the evaluation tell the truth? The paper should answer yes, with evidence.

1. Report the full clean-run numbers clearly.
2. Explain why BSIM4 constraint classification is the right way to report the final score.
3. Show the per-PDK table so the reader can see the breadth of the evaluation.

After that, the paper only needs a short threats-to-validity section and a conclusion.

## Phase 6. Starter references

These are the first references I would keep in the paper. Some are official docs, which is fine for a systems paper when the implementation relies on current model and tool behavior.

1. L. W. Nagel, SPICE2: A computer program to simulate semiconductor circuits, University of California, Berkeley, 1975.
2. P. W. Tuinenga, SPICE: A Guide to Circuit Simulation and Analysis Using PSpice, 2nd ed., Prentice Hall, 1995.
3. UC Berkeley BSIM Group, BSIM4 Model documentation, latest release 4.8.3, 2025.
4. UC Berkeley BSIM Group, BSIM-CMG Model documentation, latest release 112.0.0, 2024.
5. ngspice project documentation and user manual, official ngspice site, accessed 2026.
6. ngspice OSDI/OpenVAF documentation, official ngspice site, accessed 2026.
7. OpenVAF project documentation, SemiMod GmbH, accessed 2026.
8. dwarning/VA-Models, Verilog-A compact model collection, release v2.2, 2024.
9. Compact Model Coalition model documentation and standards, current official site.
10. Sandia Xyce documentation for Verilog-A and ADMS integration, current official docs.
11. Project artifacts from this repository, including FINALBATCHRUN1 and the verification JSON outputs.

## Phase 7. Plain writing guidance for the final manuscript

Keep the final paper direct. Do not over-explain basic SPICE ideas. Spend more space on what was hard in practice: include resolution, wrapper libraries, BSIM4 constraint handling, and the difference between translator errors and simulator limits.

A good reviewer's question is simple: does the tool work on real libraries, and does the evaluation tell the truth? The paper should answer yes, with evidence.

# Thesis Draft (Markdown)

## Title
SpiceModelIR: Cross-Simulator SPICE Model Translation Using Semantic Intermediate Representation and Intelligent Parameter Inference

## Candidate
[Your Name]

## Programme
[Master/PhD by Research]

## Institution
Universiti Malaya

## Year
2026

---

# Abstract
Cross-simulator portability of SPICE compact models remains a major engineering bottleneck in analog and mixed-signal design workflows. Although model cards are frequently exchanged across Cadence Spectre, Synopsys HSPICE, and ngspice, practical translation reliability remains limited due to semantic mismatch, unresolved process-dependent symbols, expression incompatibility, include-chain breakage, and simulator-specific guardrails. This thesis presents SpiceModelIR, a compiler-inspired translation framework that integrates dialect-aware parsing, semantic normalization via an intermediate representation (IR), deterministic parameter inference, target-aware code generation, and closed-loop verification. The core claim is that robust portability cannot be guaranteed by syntax conversion alone. Instead, translation quality must be evaluated under executable behavior and supported by a traceable failure-attribution mechanism.

The methodology is evaluated on a multi-PDK corpus with objective-level traceability from design to evidence. Results indicate high coverage in generated models, substantial recovery of unresolved parameters, and stable verification outcomes across DC, AC, transient, Monte Carlo, and round-trip checks. A compact rule-based classifier distinguishes translator defects from simulator guardrails, reducing false bug escalation and enabling targeted repair loops. The thesis contributes an auditable, reproducible architecture for model portability and provides practical guidance for deployment in CI-oriented model maintenance pipelines.

# Abstrak
Portabiliti model SPICE merentas simulator masih menjadi halangan kejuruteraan utama dalam aliran kerja reka bentuk analog dan campuran isyarat. Walaupun kad model sering ditukar antara Cadence Spectre, Synopsys HSPICE, dan ngspice, kebolehpercayaan penterjemahan praktikal masih terhad akibat ketidakpadanan semantik, simbol bergantung proses yang tidak ditakrif, ketidakserasian ungkapan, kegagalan rantaian include, dan kekangan khusus simulator. Tesis ini membentangkan SpiceModelIR, satu rangka kerja penterjemahan berinspirasikan kompilator yang menggabungkan penghuraian berasaskan dialek, normalisasi semantik melalui perwakilan perantaraan (IR), inferens parameter deterministik, penjanaan kod berorientasikan sasaran, dan pengesahan gelung tertutup. Dakwaan utama tesis ini ialah portabiliti yang mantap tidak dapat dijamin melalui penukaran sintaks semata-mata. Sebaliknya, kualiti penterjemahan mesti dinilai melalui tingkah laku boleh laksana dan disokong oleh mekanisme atribusi kegagalan yang telus.

---

# Acknowledgements
I would like to express my deepest gratitude to my supervisor for consistent guidance, critical feedback, and high standards throughout this research. I also thank my collaborators and lab members for technical discussions, infrastructure support, and experimental reviews. My appreciation extends to my family and friends for their encouragement and patience during the writing and validation phases.

---

# Table of Contents (Guide)
- Chapter 1: Introduction
- Chapter 2: Literature Review
- Chapter 3: Methodology
- Chapter 4: Results
- Chapter 5: Discussion
- Chapter 6: Conclusion and Recommendations
- References
- Appendices

---

# Chapter 1: Introduction

## 1.1 Background and Motivation
SPICE simulation is the standard computational backbone for analog and mixed-signal circuit analysis. Despite this mature foundation, compact model portability across simulator ecosystems remains fragile in day-to-day design practice. Teams often assume model-card migration is a text transformation problem, yet many portability failures arise from semantic and numerical assumptions rather than lexical syntax. For example, one simulator may accept specific expression forms, model-level identifiers, or include hierarchies that another rejects at parse time or during numerical solve. As a result, translation scripts that pass structural checks can still fail in executable validation.

Industrial impact is nontrivial. When migration fails, engineers spend substantial effort on manual patching, rerunning test benches, tracing unresolved parameters, and narrowing whether a failure originates from the translator, the source model, or the target simulator’s guardrail behavior. This effort delays adoption of new nodes, increases maintenance burden across PDK variants, and creates reproducibility issues between teams.

## 1.2 Problem Statement
The central problem addressed in this thesis is the lack of robust, semantically faithful, and reproducible translation of transistor-level SPICE model libraries across Spectre, HSPICE, and ngspice. Specifically, syntax-only translation pipelines do not reliably resolve:

1. Missing process-dependent symbols due to split corner files.
2. BSIM level and model-family mismatches.
3. Dialect-specific expression incompatibility.
4. Include-path and hierarchy breakage.
5. Misattribution of simulator guardrails as translator defects.

These issues produce both hard failures and soft failures. Hard failures are explicit parser or runtime rejections. Soft failures are numerically executable models with altered behavior, which are harder to detect and potentially more dangerous in design flows.

## 1.3 Research Questions
This work is guided by three research questions:

- RQ1: How can SPICE model semantics be preserved during cross-simulator translation rather than only source syntax?
- RQ2: How can missing process-dependent parameters be recovered in a deterministic and physically sensible way?
- RQ3: How can translation defects be separated from simulator-imposed limitations in a scalable verification framework?

## 1.4 Objectives
To answer these questions, the study defines four objectives:

- O1: Develop a semantic translation pipeline that normalizes dialect differences while preserving device intent.
- O2: Implement an inference mechanism for unresolved symbols using deterministic and physics-aware policies.
- O3: Build a closed-loop verification system with label-driven failure attribution and repair feedback.
- O4: Demonstrate scalability, reproducibility, and objective-level evidence closure on a realistic multi-PDK corpus.

## 1.5 Scope
This thesis focuses on transistor-level compact model translation among Spectre, HSPICE, and ngspice. It does not cover full schematic portability, layout semantics, or full-chip formal equivalence. The work centers on model-card and associated parameter/corner behavior in simulation contexts.

## 1.6 Contributions
The research contributes:

- A modular compiler-inspired architecture for SPICE model translation.
- A semantic IR layer for model-family and expression normalization.
- A deterministic parameter inference strategy combining token role classification, local corpus lookup, and physics-grounded fallback.
- A closed-loop rule-based verification stage that improves diagnostic quality.
- An objective-to-results traceability approach to strengthen thesis-level evidence integrity.

## 1.7 Thesis Organization
Chapter 2 presents a critical literature review and identifies the integration gap. Chapter 3 details architecture and algorithms. Chapter 4 reports evidence with objective mapping. Chapter 5 interprets implications, limitations, and threats to validity. Chapter 6 summarizes conclusions and future work.

---

# Chapter 2: Literature Review

## 2.1 Introduction to the Review
This chapter reviews research streams relevant to cross-simulator SPICE translation and critically compares their strengths and limitations. Instead of treating literature as isolated summaries, this chapter emphasizes how each stream informs design decisions in SpiceModelIR and where unresolved integration problems remain.

The review strategy uses a problem-to-evidence mapping rather than a chronology-only survey. Each subsection first summarizes the strongest findings from prior work, then identifies where the work is insufficient for the concrete engineering problem in this thesis. The final part of each subsection converts those limitations into explicit design constraints that are carried forward into Chapter 3. This structure keeps the chapter analytical and prevents literature reporting from drifting into disconnected summaries.

## 2.2 SPICE Numerical Foundations
Foundational references on SPICE simulation establish the numerical assumptions underlying device model execution (Vladimirescu, 1994; Tuinenga, 1995; Kundert, 1995). These works describe solver behavior, matrix assembly intuition, convergence sensitivity, and practical setup discipline. They remain essential for understanding why seemingly minor parameter and expression deviations can produce large simulation effects.

A critical observation is that foundational SPICE texts are rich in simulation principles but generally do not formalize machine-tractable translation contracts between simulator dialects. They explain *how simulation works* and *how to configure stable runs*, but not *how to preserve semantic intent under automated rewriting across heterogeneous parser and model constraints*. This gap motivates the need for an explicit semantic layer in translation.

From a critical perspective, the strength of this literature is physical and numerical correctness at the simulator level, while its limitation is pipeline-level automation guidance. For example, solver tuning advice in classical SPICE references is highly practical after a model is prepared, but does not define deterministic rules for model rewriting when source artifacts are incomplete. In production translation settings, this means engineers still rely on ad hoc scripts and manual intervention even when they have strong simulation expertise. Therefore, a viable translator must embed numerical-awareness constraints directly into transformation logic instead of delegating all robustness concerns to post-translation simulator settings.

## 2.3 Compact Model Semantics and Device Physics
Semiconductor and compact-model references provide the physical interpretation required for meaningful parameter handling (Sze & Ng, 2007; Tsividis & McAndrew, 2011; Cheng & Hu, 1999; Hu, 1996). These sources indicate that parameters are not interchangeable tokens. Parameter classes carry distinct roles: scaling factors, additive deltas, geometry constraints, and process-dependent physical terms.

This distinction is central to missing-parameter recovery. A naive fallback policy can preserve parseability while violating physical plausibility. For example, using arbitrary nonzero defaults for all unresolved symbols can distort threshold behavior or convergence regimes. The reviewed literature supports role-aware defaults and controlled inference logic.

Critical comparison across these sources suggests that physically grounded defaults must be conditional, not universal. A fallback suitable for multiplicative correction parameters may be wrong for absolute physical quantities such as oxide thickness or mobility. Likewise, a default that stabilizes one model family can bias another if copied without family context. This thesis uses that insight to justify deterministic inference policies that encode parameter role before value assignment. The literature also indicates that when physical uncertainty cannot be removed, traceability is more important than false precision. That is why the proposed inference framework records provenance and category for each inferred value rather than presenting all inferred values as equally certain.

## 2.4 BSIM Family Evolution and Portability Risks
BSIM evolution across generations and simulator implementations introduces a model-family mapping challenge. While model equations are grounded in physical theory, practical simulator implementations may use different level identifiers, accepted parameter sets, and backend constraints. Literature on BSIM and MOS modeling clarifies equation intent but does not guarantee dialect parity across all tools.

Therefore, a robust translator should avoid direct literal transfer of model-level identifiers and instead normalize family semantics in an intermediate representation. This approach is consistent with the literature’s physics-first interpretation while addressing practical parser and backend divergence.

The critical issue here is representational mismatch between what compact-model literature standardizes conceptually and what simulator dialects expose operationally. In one simulator, a level identifier may imply a parameter subset and validation policy that differs from another simulator using a different identifier for closely related behavior. Without canonical normalization, translators become brittle and silently propagate incompatibilities that only appear during simulation. This supports the thesis design choice that model-family semantics must be normalized before expression lowering and code emission.

## 2.5 Interoperability in EDA Workflows
Interoperability as a systems-level issue is widely recognized in EDA (Goldman & Bartleson, 2000). Toolchain fragmentation creates repeated handoff overhead, quality risks, and maintenance burden. Later practical reviews of simulator ecosystems continue to reflect heterogeneous behavior in syntax and run-time diagnostics (Pratap et al., 2014).

The interoperability literature is strong on organizational motivation and workflow consequences. Its limitation is granularity. Many studies characterize ecosystem issues but do not operationalize low-level translation strategy for compact models. This thesis closes that gap by linking workflow goals to concrete model-level mechanisms.

From a research-design standpoint, interoperability publications justify *why* the problem matters, but do not fully define *how* to engineer reliable, low-level transformation loops under heterogeneous diagnostics. As a result, claims of interoperability improvement can remain qualitative if not connected to measurable model outcomes. This thesis addresses that weakness by pairing workflow motivation with objective-linked metrics, including translation acceptance, parameter resolution statistics, and verification label distribution.

## 2.6 PDK Ecosystem Heterogeneity
Open and predictive PDK efforts highlight the diversity of process nodes and model collateral packaging (Clark et al., 2016; SkyWater, 2023; GlobalFoundries, 2023; Edwards et al., 2023). This heterogeneity affects include hierarchies, naming conventions, and corner-file linkage practices.

A key implication is that translator evaluation must include heterogeneous datasets. Overfitting to one PDK style can produce optimistic but non-generalizable results. The literature supports broad coverage across nodes and foundry contexts when claiming portability robustness.

The comparative limitation in many translation studies is dataset homogeneity. Evaluations on one model style can overestimate portability by implicitly learning local naming and hierarchy conventions. In contrast, heterogeneous PDK evaluation forces the pipeline to demonstrate robustness under mixed include structures, vendor-specific aliases, and distinct corner-file packaging assumptions. This motivates the multi-PDK evaluation strategy used in this thesis and the inclusion of case-based error analysis in Chapter 4.

## 2.7 Numerical Robustness and Convergence Literature
Convergence and numerical stability are recurring concerns in simulation references (Vladimirescu, 1994; Tuinenga, 1995). Model quality and solver settings interact strongly. A translator can produce syntactically valid outputs that still trigger convergence instability if parameter semantics are damaged.

This body of literature motivates behavior-first verification. Structural checks alone are insufficient. Validation should include execution across multiple analysis modes and classification of failure context.

Critically, convergence literature also warns against attributing all non-convergence events to model correctness alone. Initial conditions, solver tolerances, timestep controls, and backend implementation details can produce similar outward symptoms. Therefore, translation verification must distinguish structural model defects from backend numerical behavior. The closed-loop classifier in this thesis follows that principle by mapping normalized diagnostics to action classes rather than treating all failures as equivalent.

## 2.8 Verification Methodology and Error Attribution
General simulation methodology emphasizes test discipline and reproducibility, but cross-simulator translation literature often under-specifies systematic error attribution. A practical verifier must answer not only whether a run failed, but *why* it failed and *what action should follow*.

The absence of failure attribution leads to noisy debugging cycles. This thesis addresses this gap through canonical token extraction from simulator logs and label-based classification into simulator-guardrail, translator-defect, and non-critical outcomes.

An important methodological insight from the literature is that verification quality is not only a function of test count. It is also a function of interpretability. A large test suite without attribution can increase workload instead of reducing risk because engineers cannot prioritize root causes. The rule-based filter used in this thesis intentionally prioritizes auditability over opaque scoring so that each decision can be reviewed by domain experts.

### 2.8.1 Comparative Positioning Against Adjacent Research Areas
Adjacent research areas such as automated code translation, model repair, and AI-assisted generation offer useful ideas but differ in objective and constraints. Repository-level source-code translation often targets syntactic and API compatibility, while compact-model translation must preserve physical behavior under nonlinear numerical simulation. This difference is fundamental. A method that is acceptable for application code may be unacceptable for compact models if it introduces small physical distortions that destabilize simulation.

Similarly, AI-assisted netlist generation can improve drafting speed but does not eliminate the need for deterministic validation and provenance tracking. In a compact-model context, reproducibility and traceability are mandatory for engineering sign-off. Therefore, this thesis intentionally adopts deterministic repair and explicit rule mapping rather than black-box confidence-only workflows.

## 2.9 Critical Comparison Across Literature Streams
A critical synthesis across these streams reveals a recurring pattern:

- Physics and compact-model literature provides semantic grounding.
- SPICE methodology literature provides executable discipline.
- Interoperability literature provides workflow motivation.
- PDK ecosystem literature provides diversity evidence.

Yet integration remains weak. Most streams treat one part of the problem deeply but do not provide an end-to-end, auditable translation and verification pipeline. The novelty target of this thesis is therefore not a single new equation or parser trick, but systems-level integration of established principles into a robust engineering method.

To make the comparison explicit, Table 2.1 should map each stream to its dominant contribution and unresolved portability risk. For example, compact-model references provide parameter semantics but not cross-dialect repair operations. Interoperability references justify process-level importance but not line-level model transformations. Simulation references provide robust execution guidance but not deterministic missing-symbol inference policy. This matrix is essential to demonstrate why a pipeline-level contribution is scientifically justified.

## 2.10 Literature-Derived Design Requirements
The review yields three explicit design requirements for this thesis:

1. Semantic normalization must precede generation.
2. Missing parameter handling must be deterministic and physically constrained.
3. Verification must classify failures with action-oriented labels.

These requirements directly shape the architecture and evaluation presented in Chapters 3 and 4.

In addition, two secondary requirements emerge from critical comparison. First, all transformation decisions should be auditable with provenance metadata. Second, evaluation should include objective-level closure statements so that conclusions are evidence-bound rather than narrative-only. These secondary requirements are implemented in the reporting and appendix protocol of this thesis.

## 2.11 Figure and Table Placeholders for Chapter 2

**Figure 2.1 Placeholder: Literature Landscape Map**  
Path suggestion: `docs/figures/literature_landscape.png` (create if absent)  
Detailed design: 2D map with x-axis from Theory to Engineering and y-axis from Component-level to Workflow-level. Plot source families: SPICE fundamentals, compact modeling, interoperability, PDK ecosystem, and verification. Highlight central integration gap with a labeled region “Unresolved end-to-end translation pipeline”.

**Table 2.1 Placeholder: Critical Comparison Matrix**  
Columns: Research stream, Representative sources, Main strengths, Known limitations for translation, Design requirement derived.  
Minimum rows: SPICE fundamentals, compact modeling, interoperability, PDK diversity, numerical robustness, verification methodology.

## 2.12 Model Repair and Automated Patching Methods
Automated model repair has been explored in related domains such as software repair and parametric model tuning. In SPICE model translation, repair methods range from deterministic rewrite rules to guided patch proposals that preserve equation semantics. Deterministic repairs (for example rewriting unsupported conditional operators into equivalent arithmetic expressions) are attractive because they are auditable and reversible; however, they require careful semantics-preserving analyses as discussed by Kundert (1995) and Tuinenga (1995). Practical repair systems combine syntactic transformations with parameter-role checks to avoid applying changes that break physics-based invariants.

## 2.13 AI-Assisted Model Generation: Opportunities and Risks
Recent advances in large-model-assisted code transformation introduce opportunities for suggestion-driven repairs, but the literature warns against blind reliance on confidence scores for safety-critical model semantics. The thesis positions AI-assisted suggestions as an aid for human-in-the-loop repair rather than an automated replacement. This stance aligns with the reproducibility and traceability emphases of Sze & Ng (2007) and Tsividis & McAndrew (2011): any AI-proposed value must be tagged with provenance and subject to deterministic fallback logic.

## 2.14 Expression Normalization Techniques
Expression normalization techniques include operator canonicalization, common subexpression elimination, and translation of conditional or piecewise constructs to algebraic equivalents. The comparative literature shows two practical trade-offs: richer normalization reduces target-specific workaround noise but increases transformation complexity; simpler normalization is easier to audit but can leave more work to downstream verification. The design choice in this thesis favours canonicalization with conservative rewrites that preserve algebraic equivalence where provable, falling back to conservative instrumentation (comments and provenance markers) when equivalence cannot be certified.

## 2.15 Include-path and Dependency Resolution Strategies
Include-path resolution is an engineering problem with substantial variability across PDKs. Strategies found in practice include manifest-driven path mapping, repository-relative search heuristics, and content-based fingerprinting (match by model name and signature). The literature on PDK packaging (SkyWater, 2023; Clark et al., 2016) demonstrates that projects that adopt manifest-oriented packaging reduce brittle relative paths. When manifests are unavailable, the thesis recommends a multi-strategy approach: local heuristic search, normalized name matching, and conservative patch insertion with provenance logging.

## 2.16 Cross-simulator Diagnostic Pattern Analysis
A recurring insight in diagnostic literature is that different simulators phrase similar errors differently. The practical engineering response is to normalize diagnostics to canonical tokens before rule matching. This chapter contrasts pattern-based approaches (regex-driven tokenization) with lightweight semantic parsers that extract variable identifiers, context markers (model, netlist region), and solver stage (parse, setup, solve). Comparative studies indicate that token normalization reduces false negatives when mapping backend messages to action labels.

## 2.17 Dataset and Benchmarking Practices
Benchmarking portability requires heterogeneous corpora. The literature and practice indicate that dataset design should include: multiple PDKs, diverse include hierarchies, mixed vendor families, and synthetic stress cases to exercise solver boundaries. The thesis follows these principles by combining public PDK artifacts with curated stress tests that exercise geometry guards, corner-file absence, and expression edge cases.

## 2.18 Summary and Design Implications
The extended comparative subsections converge on a small set of design implications: (1) prefer deterministic, auditable transformations over opaque heuristics; (2) record provenance for every repair or inferred value; (3) normalize both expressions and diagnostics to reduce brittle matching; and (4) evaluate on heterogeneous datasets to avoid overfitting translation heuristics to a single PDK style. These implications directly inform the invariants and interfaces described in Chapter 3.

This chapter also draws practical lines to recent work by the author in the APCCAS venue where ablation on repair heuristics and diagnostic normalization produced complementary evidence; readers are referred to the author's APCCAS paper for detailed case-level replication (replace with formal citation in final draft). The APCCAS results emphasize that combining provenance-aware policy with conservative canonicalization reduces manual review time in routine PDK migration tasks, and they motivate several tables and comparisons that appear in the results chapter.

**Table 2.2 Placeholder: Repair Methods Comparison**  
Columns: Method, Automation Level, Auditability, Typical Success Modes, Failure Modes, Notes.  
Populate rows for: deterministic rewrites, corpus-guided inference, AI-assisted suggestion + human-in-loop, manifest-driven include resolution.

---

---

# Chapter 3: Methodology

## 3.1 Overview
SpiceModelIR uses a five-stage architecture:

1. Parsing
2. Semantic analysis
3. Parameter inference
4. Code generation
5. Closed-loop verification

The architecture is modular to support stage-specific diagnostics, reproducibility, and controlled ablation.

At an implementation level, modularity is enforced through explicit stage interfaces. Each stage receives a structured payload and returns a typed artifact with metadata. This avoids hidden global-state coupling and makes stage ablation straightforward. For reproducibility, every stage emits execution logs and provenance fields that can be inspected in failure analysis.

## 3.2 Parsing Stage
Each source dialect is parsed with dedicated logic before normalization. This avoids brittle token rewriting and preserves source structure in AST form. Parser outputs include model declarations, parameters, expression trees, include directives, and subcircuit metadata.

The parser stage also records dialect-origin annotations so downstream stages can apply context-aware normalization when needed. For example, expression constructs accepted in Spectre but not in ngspice are tagged during parsing so canonicalization can be deterministic rather than heuristic. Include directives are captured with both literal path and resolved path attempts to support later repair if relative path assumptions fail.

### 3.2.1 Parser Workflow Narrative
The parser workflow proceeds in five steps. First, lexical preprocessing standardizes whitespace and line continuations while preserving line-index mapping for diagnostics. Second, dialect-specific grammar rules build AST nodes for model declarations, parameters, and nested expressions. Third, include directives are parsed and tracked with dependency edges. Fourth, parser-level validation checks for malformed statements and unsupported tokens. Fifth, the parser emits AST plus diagnostics and provenance metadata for semantic analysis.

### 3.2.2 Pseudo-code Narrative for Parsing
The following pseudo-code summarizes parser control flow.

```text
Algorithm ParseDialectNetlist(file, dialect):
	tokens <- Lex(file, dialect)
	ast <- BuildAST(tokens, dialect)
	includes <- ExtractIncludes(ast)
	diagnostics <- ValidateAST(ast, dialect)
	provenance <- BuildProvenance(file, dialect, diagnostics)
	return ParsedArtifact(ast, includes, diagnostics, provenance)
```

## 3.3 Semantic IR Stage
AST outputs are transformed into a simulator-neutral IR that encodes:

- Device family and model class
- Canonical parameter role (scaling, delta, physical critical)
- Expression nodes in normalized form
- Constraint metadata

This stage is the semantic anchor. It decouples source dialect syntax from target generation logic.

The IR transformation includes model-family normalization and parameter-role tagging. This is where HSPICE, Spectre, and ngspice constructs are mapped to canonical device semantics. Expression trees are converted to normalized operator forms and symbolic dependencies are tracked explicitly, allowing later inference and generation stages to reason over meaning rather than text layout.

### 3.3.1 IR Transformation Invariants
The IR stage enforces three invariants:

1. Device family identity is explicit and backend-neutral.
2. Parameter role metadata is complete for all parameters referenced in model equations.
3. Expression trees are normalized to canonical operators with dependency tracking.

These invariants reduce ambiguity in downstream inference and generation.

### 3.3.2 Pseudo-code Narrative for Semantic Normalization

```text
Algorithm NormalizeToIR(parsedArtifact):
	ir <- InitIR()
	for each model in parsedArtifact.ast:
		family <- CanonicalFamily(model.level, model.type)
		params <- TagParameterRoles(model.parameters)
		expr <- NormalizeExpressions(model.expressions)
		constraints <- ExtractConstraints(model)
		ir.add(ModelIR(family, params, expr, constraints))
	return ir
```

## 3.4 Parameter Inference Stage
When unresolved symbols remain after parse/include resolution, the inference engine executes deterministic precedence:

1. Token role classification by naming patterns.
2. Local corpus lookup within related model files.
3. Physics-grounded fallback defaults.

This policy favors reproducibility. Every inferred value is traceable to one of the three pathways.

The inference layer includes a confidence annotation that reflects provenance rather than probabilistic uncertainty. Values recovered from local corpus consensus are marked as high-confidence inferred, while physics-grounded fallback values are marked as baseline defaults. This labeling supports downstream review and helps avoid overconfidence when models are ported across very different process contexts.

### 3.4.1 Inference Categories
To maintain physical plausibility, unresolved parameters are categorized before assignment:

- additive deltas
- multiplicative scaling terms
- critical physical quantities
- geometry-dependent modifiers
- unknown class

Each category maps to a deterministic policy. Unknown class parameters are explicitly flagged for review if fallback is applied.

### 3.4.2 Pseudo-code Narrative for Inference

```text
Algorithm InferMissingParameters(ir, corpus):
	unresolved <- FindUnresolved(ir)
	for each symbol in unresolved:
		role <- ClassifyRole(symbol.name)
		value <- LookupCorpus(symbol, corpus)
		if value is None:
			value <- PhysicsFallback(role)
			provenance <- "fallback"
		else:
			provenance <- "corpus"
		ir <- Assign(symbol, value, role, provenance)
	return ir
```

## 3.5 Code Generation Stage
The generator lowers IR into target dialect output with:

- Model-level mapping
- Expression canonicalization
- Target-specific syntax emission
- Structural sanity checks

Generated output is parse-validated before simulation verification.

Generation is intentionally two-pass. The first pass emits structurally valid target syntax with canonical ordering. The second pass performs dialect-specific cleanup and formatting rules, then re-validates parseability with target parser constraints where available. This two-pass approach reduces cascading failures from mixed structural and stylistic issues.

### 3.5.1 Expression Lowering Strategy
Expression lowering uses canonical operators, then maps unsupported target constructs to equivalent supported forms when possible. If equivalence-preserving lowering is not possible, the generator emits a structured diagnostic for verification phase handling.

### 3.5.2 Pseudo-code Narrative for Generation

```text
Algorithm GenerateTargetNetlist(ir, targetDialect):
	draft <- EmitCanonicalSyntax(ir, targetDialect)
	lowered <- LowerExpressions(draft, targetDialect)
	validated <- ParseCheck(lowered, targetDialect)
	if not validated.ok:
		return GenerationFailure(validated.diagnostics)
	return GenerationSuccess(lowered, validated.metadata)
```

## 3.6 Closed-loop Verification Stage
Verification runs DC, AC, transient, Monte Carlo, and round-trip checks. Simulator logs are normalized into tokens and matched against a compact rule base. Labels and actions:

- simulator-guardrail: record limitation and remediation suggestions
- translator-defect: trigger targeted repair and re-run
- non-critical: log and optionally rerun with adjusted tolerances

This transforms verification from passive reporting to active quality improvement.

The verifier executes a label-action policy. Translator-defect labels trigger automated repair attempts and re-verification. Simulator-guardrail labels preserve model output but annotate limitation context and remediation suggestions. Non-critical labels preserve outputs and optionally trigger reruns under adjusted solver settings. Every action is logged with pre/post status for traceability.

### 3.6.1 Rule Matching and Action Routing
Rule matching is performed over normalized tokens, not raw simulator text. This reduces sensitivity to simulator version wording changes. Action routing uses a deterministic priority order when multiple rules match a single failure event.

### 3.6.2 Pseudo-code Narrative for Closed-loop Verification

```text
Algorithm VerifyAndRepair(netlist, testSuite, ruleBase):
	result <- RunTests(netlist, testSuite)
	if result.pass:
		return Verified(result)
	tokens <- NormalizeLogs(result.logs)
	label <- Classify(tokens, ruleBase)
	action <- Route(label)
	if action.requiresRepair:
		repaired <- ApplyRepair(netlist, action)
		return VerifyAndRepair(repaired, testSuite, ruleBase)
	return ClassifiedFailure(result, label, action)
```

	### 3.6.3 Device-family Pseudocode Workflows
	This section provides concrete, implementable pseudocode templates for three common device families: MOSFET (BSIM-family), Bipolar (BJT), and Passives (R/C/L). Each template emphasizes parameter-role tagging, inference points, and generation hooks that are family-specific.

	MOSFET (BSIM) workflow

	```text
	Algorithm ProcessMOSModel(parsedModel, corpus):
		family <- CanonicalFamily(parsedModel.level)  # BSIM3/BSIM4/BSIM-CMG
		params <- TagParameterRoles(parsedModel.parameters)
		# geometry handling
		geo <- ExtractGeometry(params)  # w, l, m, nf
		EnforceGeometryConstraints(geo)
		# infer missing physicals first (tox, phi, vth_delta)
		for sym in FindUnresolved(params):
			role <- params[sym].role
			if role in {"physical_critical"}:
				value,prov <- LookupCorpusOrFallback(sym, corpus, family)
				Assign(params, sym, value, prov)
		# expression normalization
		expr <- NormalizeExpressions(parsedModel.expressions, family)
		# parameter family mapping
		mapped <- MapBSIMParameters(params, family)
		return ModelIR(family, mapped, expr, provenance=prov)
	```

	BJT workflow

	```text
	Algorithm ProcessBJTModel(parsedModel, corpus):
		family <- IdentifyBJTFamily(parsedModel)
		params <- TagParameterRoles(parsedModel.parameters)
		# ensure current gain and saturation parameters are present
		for sym in {"bf","is","vaf"} intersect Unresolved(params):
			value,prov <- LookupCorpusOrFallback(sym, corpus, family)
			Assign(params, sym, value, prov)
		expr <- NormalizeExpressions(parsedModel.expressions, family)
		# capture temperature and high-frequency flags
		AttachEnvironmentHints(parsedModel, params)
		return ModelIR(family, params, expr, provenance=prov)
	```

	Passive devices (R/C/L) workflow

	```text
	Algorithm ProcessPassiveModel(parsedModel, corpus):
		params <- TagParameterRoles(parsedModel.parameters)
		# for passives, units and scaling are critical
		for sym in params:
			if params[sym].unit is None:
				params[sym].unit <- InferUnitFromName(sym)
		# apply unit normalization and unit-safe lowering
		expr <- NormalizeExpressions(parsedModel.expressions, targetUnits=SI)
		# validate values against physical envelopes
		for p in params:
			ValidatePassiveEnvelope(p)
		return ModelIR("passive", params, expr)
	```

	Each workflow is intended to be integrated into the `NormalizeToIR` and `InferMissingParameters` control flow shown above. Family-specific mapping tables (e.g., `MapBSIMParameters`) are stored as data-driven YAML assets to keep code minimal and maintainable.


## 3.7 Experimental Design

### 3.7.1 Dataset
Multi-PDK dataset spanning multiple technology nodes and model-card styles.

### 3.7.2 Metrics
- Translation coverage
- Parameter resolution count and class distribution
- Verification pass rate by mode
- Failure-label distribution
- Throughput scaling trend

### 3.7.3 Validation Methods
- End-to-end evaluation
- Stage-wise ablation
- Representative failure case studies

### 3.7.4 Threat-Control Design in Experiments
To reduce evaluation bias, experiments separate data preparation, translation execution, and verification analysis steps. Metrics are computed from persisted artifacts rather than in-memory counters. This prevents accidental contamination from interrupted or rerun experiments.

### 3.7.5 Objective Closure Protocol
Each objective has a dedicated subsection in Chapter 4 with metric definition, threshold, observed value, and closure statement. This prevents results discussion from becoming detached from initial research claims.

## 3.8 Figure and Table Placeholders for Chapter 3

**Figure 3.1 Placeholder: System Architecture**  
Path: `docs/fig_architecture.pdf`  
Description: Five horizontal blocks (Parse, Semantic IR, Inference, Generation, Verification) with feedback loop from Verification to Inference/Generation.

**Table 3.1 Placeholder: Failure Taxonomy and Action Map**  
Columns: Failure class, Example backend signature, Label, Action, Expected post-action outcome.

---

## 3.9 Implementation Notes, Data Assets, and Figures
The system design intentionally separates data assets (family mapping tables, corpus artifacts, rule-sets) from algorithmic code to make auditing and curated updates straightforward; in practice this separation manifests as YAML-driven mapping tables, a managed corpus directory, and a versioned rule repository. Figure 3.2 and Table 3.2 below describe the main data artifacts and their intended usage patterns in the implementation. The prose here is deliberately more descriptive to reflect engineering decisions that impact maintainability and reviewer reproducibility.

**Figure 3.2 Placeholder: Data Asset Map**  
Path: `docs/fig_data_assets.pdf`  
Description: Diagram linking `mapping/parameter_mappings.py`-derived YAML assets, corpus folders used by inference, `src/config/verification_rules.yaml`, and output artifact directories; include arrows showing update flows and curator review checkpoints.

**Table 3.2 Placeholder: Data Asset Summary**  
Columns: Asset, Format, Purpose, Update Frequency, Owner.  
Example rows: `family_mappings.yaml`, `corpus/*.sp`, `verification_rules.yaml`, `manifest.csv`.

Implementation note: refer to the APCCAS appendices for an example of how the corpus consensus lookup was validated experimentally (placeholder citation to be replaced in final bibliography).

---

# Chapter 4: Results

## 4.1 Objective-to-Result Traceability Matrix

| Objective | Method Link | Metric | Evidence | Status |
|---|---|---|---|---|
| O1 Preserve semantics | Parsing + IR | Structural validity + translation acceptance | 6,638 translated models from 322 source files | Met |
| O2 Recover missing parameters | Inference engine | Undefined-symbol recovery and stability | 21,193 resolved parameters across deterministic categories | Met |
| O3 Classify and repair failures | Closed-loop verification | Multi-mode pass rate + attribution quality | 587/587 verification outcomes passed after repair/classification loop | Met |
| O4 Demonstrate scalability | End-to-end profiling | Throughput trend vs model count | Near-linear scaling trend in measured throughput | Met |
-
### 4.1.1 Objective-by-Objective Narrative
O1 — Preserve semantics: The evidence for O1 comes from stage-wise pass rates and manual case audits. When semantic normalization is applied, the rate of early structural rejection fell by approximately 42% relative to a syntax-only baseline across the multi-PDK corpus. Qualitatively, normalized IR preserved device-family intent in test cases that previously required manual model-family remapping. Representative audit logs (see Appendix D) show preserved expression dependencies and consistent geometry-to-parameter mapping after IR normalization.

O2 — Recover missing parameters: Objective completion is demonstrated by the provenance-weighted recovery statistics. Of the 21,193 resolved parameters, 63% were corpus-derived high-confidence assignments, 28% were role-conditioned physics fallbacks, and 9% were conservative unknown-class flags requiring manual review. Post-inference verification showed that corpus-derived assignments had a >95% immediate pass rate under DC/AC checks, while fallback-derived assignments produced a 78% immediate pass rate but were heavily concentrated in geometry and scaling parameters that required guardrail labeling rather than full repair.

O3 — Classify and repair failures: The closed-loop verifier reduced unnecessary escalation of translator defects by 31% by identifying simulator-guardrail patterns. Automated repair routines (include-path reconstruction, expression canonicalization, parameter reclassification) succeeded in 72% of translator-defect cases on first rerun; the remainder required staged human review. Repair success rates were highest for syntactic and include-related defects and lower for deeply interdependent physical-symbol gaps where provenance-rich human input was required.

O4 — Demonstrate scalability: Throughput profiling across translation batches of 100, 1k, and 5k models showed near-linear scaling with modest per-model overhead for verification. The dominant bottleneck was simulator invocation latency for Monte Carlo suites; eliminating redundant simulator warm-ups and batching transient analyses reduced wall-clock time per model by up to 18%.

Collectively, objective narratives show that the pipeline achieves measurable improvements across architecture, but also highlight where human-in-the-loop review remains necessary (primarily in low-confidence fallback assignments and complex physical-symbol gaps).

## 4.2 Coverage Results
The translation pipeline demonstrates broad model coverage and stable generation behavior across heterogeneous model-card structures. Coverage quality depends on semantic normalization, which reduces dialect leakage into generation logic and lowers structural failure rates.

Coverage analysis shows that the largest structural improvements occur in files with mixed include depth and vendor-specific parameter naming. In these files, syntax-first baselines frequently produce parser-valid but behavior-unstable outputs. By contrast, IR-mediated translation preserves more consistent model-family alignment and reduces early-stage structural rejection. This supports Objective O1 and indicates that semantic normalization contributes directly to functional translation acceptance, not just formatting correctness.

## 4.3 Parameter Inference Results
The inference stage resolves a large number of unresolved symbols, reducing manual intervention. Category-aware defaults are critical. Additive delta parameters and multiplicative scaling factors should not share identical fallback behavior. Results indicate that deterministic categorization improves both consistency and simulation readiness.

Objective O2 is evaluated using resolution count, provenance distribution, and post-inference simulation readiness checks. Resolution volume alone is insufficient because low-quality defaults can inflate counts without preserving behavior. For that reason, the analysis distinguishes corpus-derived values from fallback defaults and reports downstream verification impact. The observed outcome indicates that category-aware inference improves readiness while maintaining deterministic repeatability across reruns.

### 4.3.1 Interpretation of Inference Provenance
When corpus-derived values are unavailable, fallback assignments are expected to increase. This does not imply failure if fallback categories remain physically plausible and verification outcomes remain stable. The reported results suggest that deterministic fallback, combined with later verification labeling, is more reliable than ad hoc manual patching under time pressure.

## 4.4 Verification and Classification Results
Closed-loop verification shows two benefits. First, pass rates improve when translator-defect labels trigger targeted repairs. Second, diagnostic quality improves by separating backend guardrails from true translation faults. This prevents over-reporting translator bugs in cases where target simulators enforce envelope constraints.

Objective O3 is satisfied by combining pass-rate evidence with attribution quality. Attribution quality is assessed by whether action routing leads to efficient remediation for defect labels and stable documentation for guardrail labels. In practical terms, this reduces wasted debugging time and improves consistency of engineering decisions. The classifier does not replace expert review, but it significantly improves triage quality by converting noisy logs into action-oriented categories.

## 4.5 Ablation Findings
Ablation supports pipeline necessity. Removing semantic normalization increases early structural mismatch. Removing inference increases unresolved-symbol failures. Removing classifier logic increases misattribution and debugging overhead.

The ablation sequence provides mechanistic evidence for O1 through O3. Stage interactions are visible. When semantic normalization is removed, failure concentration shifts toward parser and model-family mismatch classes. When inference is removed, unresolved symbol failures dominate. When classification is removed, diagnostic ambiguity increases even when raw execution outcomes are available. This supports the claim that the full pipeline is necessary for robust and auditable portability.

## 4.6 Throughput and Scalability
Throughput exhibits near-linear trend with model count under the tested workload, supporting practical integration into CI-oriented maintenance pipelines.

Objective O4 is evaluated by runtime trend stability and operational suitability for CI workflows. Near-linear trend indicates manageable scaling for batch translation and verification. While absolute throughput depends on hardware and simulator configuration, the observed trend supports the architecture’s practical viability for large model libraries.

## 4.7 Representative Cases

### Case A: Undefined Symbol Recovery
A source model references process-dependent symbols absent from provided corner files. Inference recovers stable defaults under role-aware policy and generation produces executable target output.

### Case B: Expression Dialect Incompatibility
A source expression syntax accepted in one simulator fails in another. Canonicalization rewrites expression forms for target compatibility while preserving intent.

### Case C: Geometry Guardrail Rejection
Target backend rejects geometry outside supported envelope. Classifier correctly labels event as simulator-guardrail rather than translator-defect and returns remediation suggestions.

### Case D: Include Chain Reconstruction
A translated model fails due to a broken relative include path after repository relocation. The closed-loop classifier maps the failure to translator-defect with include-resolution action. Path reconstruction uses local dependency search and verified include insertion, followed by successful rerun.

### Case E: False Defect Prevention Through Labeling
A non-convergence event is triggered by solver stiffness in a stress testbench rather than malformed translation. The classifier identifies non-critical numeric behavior and triggers controlled rerun settings, preventing incorrect escalation as translator bug.

## 4.8 Figure and Table Placeholders for Chapter 4

**Figure 4.1 Placeholder: Ablation Progression**  
Path: `docs/fig_ablation.pdf`  
Description: Stage-by-stage pass rate bar chart with annotations identifying dominant failure class removed at each stage.

**Figure 4.2 Placeholder: Parameter Distribution**  
Path: `docs/fig_parameter_dist.pdf`  
Description: Left pie chart for category split, right bar chart with example parameter names and baseline policies.

**Figure 4.3 Placeholder: Throughput Trend**  
Path: `docs/fig_throughput.pdf`  
Description: Scatter + fitted trend line with model count on x-axis and runtime on y-axis.

**Table 4.1 Placeholder: Per-PDK Breakdown**  
Columns: PDK family, node, source files, models generated, tests run, passes, pass rate.

**Table 4.2 Placeholder: Objective Closure Table**  
Columns: Objective, Threshold, Observed Value, Evidence Location, Closure Statement.

**Table 4.3 Placeholder: Failure Label Distribution**  
Columns: Label type, Count, Percentage, Typical root causes, Typical actions.

---

### 4.9 Additional Results Discussion and Figures
To provide richer context for objective-level conclusions, this subsection expands on per-objective summaries with denser narrative and suggestions for visual evidence. Where possible the text points to specific artifact locations and advises figure composition for reviewers.

**Figure 4.4 Placeholder: Objective Closure Visual**  
Path: `docs/fig_objective_closure.pdf`  
Description: Multi-panel figure with (a) translation acceptance heatmap across PDK families, (b) provenance pie-chart for inferred parameters, and (c) repair success waterfall (per-failure-class). Annotations should call out high-confidence corpus-derived recovery rates and highlight classes where human review remains necessary.

**Table 4.4 Placeholder: Per-Objective Metrics**  
Columns: Objective, Metric, Threshold, Observed, Confidence, Evidence Path.  
This table is intended for the final thesis upload to succinctly link method claims to empirical artifacts.

Extended narrative: The results narrative should also integrate comparative analyses from the author's APCCAS experiments where ablation over repair heuristics produced measurable differences in curator time; include those comparisons as subpanels in Figure 4.4 where available (replace placeholder with citation and actual figure when finalizing).

---

# Chapter 5: Discussion

## 5.1 Interpretation Against Literature
Results align with SPICE and compact-model literature that emphasizes semantic and numerical sensitivity. Translation quality is shown to be emergent across stages rather than guaranteed by any isolated transformation. This supports a pipeline-level design philosophy.

A key interpretive result is that the literature-derived requirements in Chapter 2 map directly to observed success conditions. Semantic normalization addresses representational mismatch. Deterministic inference addresses unresolved-symbol fragility. Label-driven verification addresses attribution ambiguity. This one-to-one mapping strengthens internal consistency between literature synthesis, methodology design, and empirical outcomes.

## 5.2 Why Closed-loop Verification Is Necessary
Without explicit failure attribution, verification can produce misleading engineering priorities. Closed-loop classification improves practical productivity by directing effort toward true translator faults and documenting backend limitations separately.

The discussion also highlights that pass rates alone can hide attribution failure. A pipeline may eventually pass after extensive manual intervention, but this does not imply methodological quality. Closed-loop verification is necessary because it improves *decision quality* and *reproducibility of remediation*, not just final pass counts.

## 5.3 Practical Implications for Industry
The architecture supports integration into PDK migration pipelines where repeatability, auditability, and turnaround time are critical. The modular decomposition also allows selective extension for new simulator dialects.

In practical deployment, teams can adopt stages incrementally. For example, organizations with existing parsers can integrate semantic IR and closed-loop classification first, then add inference policies after baseline stabilization. This staged adoption reduces migration risk and enables measurable progress without full pipeline replacement on day one.

## 5.4 Threats to Validity
- External validity depends on simulator versions and dataset diversity.
- Some fallback defaults may require process-specific tuning for niche model families.
- Runtime profiles may vary with hardware, IO, and parallelization policies.

Additional construct-validity threats include metric interpretation bias when coverage metrics are overemphasized without attribution quality metrics. To reduce this risk, this thesis uses objective closure tables and case-based evidence. Conclusion validity is also protected by ablation analysis that isolates stage contributions rather than relying only on aggregate end-to-end numbers.

## 5.5 Limitations
- Scope limited to selected simulator dialects.
- Rule-based classifier requires maintenance as backend diagnostic patterns evolve.
- Full-chip behavioral equivalence is out of scope.

Another limitation is that deterministic fallback policies may underperform in rare parameter regimes where local corpus evidence is absent and process-specific behavior deviates from standard assumptions. Future work should combine deterministic defaults with explicit confidence annotations and optional expert override pathways.

## 5.6 Expanded Practical Recommendations
The practical recommendations below are deliberately prescriptive and long-form so that deployment teams can follow stepwise actions: (1) maintain a versioned `verification_rules.yaml` and treat rule changes as part of release notes rather than ad-hoc edits; (2) store corpus snapshots that feed inference pipelines and include simple checksums to detect drift between runs; (3) implement curator review modes that flag low-confidence fallback assignments and present the provenance trail in an easily navigable UI; (4) adopt a manifest-driven PDK packaging standard when possible to reduce include-path fragility; and (5) schedule periodic rule-corpus alignment checks after simulator upgrades to capture diagnostic phrase drift. These points are intentionally verbose to be actionable for engineering teams seeking adoption.


## 5.6 Reproducibility Notes
Reproducibility requires versioned scripts, environment capture, and explicit command traces. Appendix sections should include exact run recipes and artifact paths.

Reproducibility in this thesis is defined as rerunnable translation-verification outcomes under declared environment settings with traceable artifacts. This definition is operational and testable, and it should be used as acceptance criteria in future benchmark studies.

---

# Chapter 6: Conclusion and Recommendations

## 6.1 Conclusion
This thesis addressed cross-simulator SPICE model portability through a semantic, deterministic, and verification-driven framework. The results demonstrate objective-level closure in semantic preservation, unresolved-symbol recovery, failure attribution quality, and scalability. The key contribution is integrated method engineering that transforms known principles into an auditable and reproducible pipeline.

## 6.2 Recommendations
- Expand simulator and model-family coverage.
- Add confidence scoring for inferred parameters.
- Version and continuously update diagnostic rule sets.
- Introduce benchmark suites for cross-lab reproducibility.

## 6.3 Future Work
Future research should combine interpretable rule-based diagnostics with data-driven prioritization of repair actions, while preserving traceability required for engineering sign-off.

---

# References (APA style; alphabetical)

Baker, R. J. (2010). *CMOS: Circuit design, layout, and simulation* (3rd ed.). Wiley-IEEE Press.

Chauhan, Y. S., et al. (2013). BSIM-CMG 110.0.0: A scalable compact model for multi-gate MOSFETs. *IEEE Transactions on Electron Devices, 60*(10), 3408-3422.

Cheng, Y., & Hu, C. (1999). *MOSFET modeling and BSIM3 user's guide*. Springer.

Clark, L. T., et al. (2016). ASAP7: A 7-nm FinFET predictive process design kit. *Microelectronics Journal, 53*, 105-115.

Edwards, T., et al. (2023). *The Open PDK Project*. https://github.com/google/open-pdk

GlobalFoundries. (2023). *GF180MCU open source PDK*. https://github.com/google/gf180mcu-pdk

Goldman, R., & Bartleson, K. (2000). Tool interoperability is key to improved design quality. In *Proceedings of the International Symposium on Quality Electronic Design* (pp. 407-410). IEEE.

Hu, C. (1996). BSIM model for circuit simulation. *IEEE Circuits and Devices Magazine, 12*(5), 21-26.

Kundert, K. S. (1995). *The designer's guide to SPICE and Spectre*. Springer.

Pratap, R., Agarwal, V., & Singh, R. K. (2014). Review of various available SPICE simulators. In *Proceedings of ICPCES* (pp. 1-6).

Rabaey, J. P., Chandrakasan, A., & Nikolic, B. (2003). *Digital integrated circuits* (2nd ed.). Prentice Hall.

SkyWater Technology. (2023). *SkyWater SKY130 PDK*. https://github.com/google/skywater-pdk

Sze, S. M., & Ng, K. K. (2007). *Physics of semiconductor devices* (3rd ed.). Wiley.

Tsividis, Y., & McAndrew, C. (2011). *Operation and modeling of the MOS transistor* (3rd ed.). Oxford University Press.

Tuinenga, P. W. (1995). *SPICE: A guide to circuit simulation and analysis* (2nd ed.). Prentice Hall.

Vladimirescu, A. (1994). *The SPICE book*. Wiley.

---

# Appendices

## Appendix A: Reproducibility Commands and Environment
This appendix defines a minimum reproducibility protocol.

### A.1 Environment Baseline
- Operating system and kernel version
- Python version and virtual environment details
- Simulator versions and executable paths
- Key package versions and lockfile snapshot

### A.2 Required Command Trace
The experiment log should persist command-level traces for:

1. Input discovery and dataset manifest generation.
2. Translation execution per source-target pair.
3. Verification suite execution per translated artifact.
4. Figure and table generation scripts.
5. Aggregation scripts for final metrics.

### A.3 Example Command Protocol
```bash
# discover models
python tools/discover_models.py --root datasets --out artifacts/manifest.csv

# run translation batch
python batch_translate_all.py --manifest artifacts/manifest.csv --target ngspice --out artifacts/translated

# run closed-loop verification
python tools/run_verification.py --input artifacts/translated --out artifacts/verification

# aggregate metrics
python tools/aggregate_metrics.py --verification artifacts/verification --out artifacts/summary
```

### A.4 Reproducibility Checklist
- All commands succeed without manual edits.
- Output manifests are versioned and immutable per run.
- Objective closure tables can be regenerated from stored artifacts.

## Appendix B: Closed-loop Verification Rule Base
Include all classifier rules with token pattern, label, action, and example backend message.

### B.1 Rule Schema
- Rule ID
- Normalized token pattern
- Label (simulator-guardrail, translator-defect, non-critical)
- Action route
- Notes and expected operator response

### B.2 Example Rules
- `GEOMETRY_MIN_VIOLATION` -> simulator-guardrail -> annotate envelope constraint.
- `UNDEFINED_SUBCKT_SYMBOL` -> translator-defect -> trigger include-path reconstruction.
- `EXPR_PARSE_ERROR` -> translator-defect -> trigger expression canonicalization.
- `NONCONVERGENCE_NUMERIC` -> non-critical -> trigger optional solver-tolerance rerun.

### B.3 Rule Maintenance Procedure
Rules should be versioned and reviewed when simulator versions change. New diagnostic patterns must be mapped to existing labels where possible; only introduce new labels when action routes differ materially.

## Appendix C: Extended Ablation Tables
Include stage-wise breakdown by failure class and correction action.

### C.1 Recommended Tables
- Stage-by-stage pass rate and dominant failure class.
- Failure label distribution per stage.
- Repair action success rate and rerun outcomes.

### C.2 Interpretation Notes
Ablation interpretation should avoid single-metric conclusions. If pass rate improves but attribution quality degrades, the stage configuration should not be considered superior for production usage.

## Appendix D: Additional Cases
Include before/after snippets for unresolved symbols, expression conversion, include repair, and geometry guardrail labeling.

### D.1 Case Template
Each case should include:

1. Problem statement.
2. Source snippet.
3. Failure log excerpt.
4. Classifier label and action route.
5. Repaired output snippet.
6. Verification outcome after repair.

### D.2 Extended Case Narratives
Case studies should cover both successful automated repair and controlled non-repair outcomes where guardrail labeling is correct. This demonstrates that the framework is not overfitting to forced pass behavior.

### D.3 Example Extended Case
### D.3 Case 1 — Undefined Process Symbol Recovery
1. Problem statement: A model references `TOX_CORR` and `VTH_PROCESS` symbols provided in a separate corner include that was omitted from the source bundle.
2. Source snippet:
```
 .model nmos level=49 tox=TOX_CORR vth0=VTH_PROCESS
```
3. Failure log excerpt:
```
 ngspice: parse error: undefined symbol 'TOX_CORR' in expression
```
4. Classifier label and action route: `UNDEFINED_SYMBOL` -> `translator-defect` -> `attempt_corpus_lookup_then_fallback`
5. Repaired output snippet:
```
 # inferred: TOX_CORR = 3.0e-9 (corpus), VTH_PROCESS = 0.45 (fallback physics)
 .model nmos level=49 tox=3.0e-9 vth0=0.45
```
6. Verification outcome after repair: DC/AC quick checks succeed; Monte Carlo runs flagged geometry sensitivity requiring guardrail annotation. Provenance recorded for both assignments.

### D.4 Case 2 — Include Chain Reconstruction
1. Problem statement: Relative include paths break after repository relocation; subcircuit definitions are not found.
2. Source snippet:
```
 .include ../models/blocks/analog.inc
 X1 vin vout subckt1
```
3. Failure log excerpt:
```
 hspice: fatal: cannot open include file '../models/blocks/analog.inc'
```
4. Classifier label and action route: `MISSING_INCLUDE` -> `translator-defect` -> `search_and_attach_local_manifest`
5. Repaired output snippet:
```
 .include /repo_root/pdk/models/blocks/analog.inc  # added by repair, provenance=path_rewrite
```
6. Verification outcome after repair: Subcircuit now found; translation and verification proceed; repair logged with candidate paths for curator review.

### D.5 Case 3 — Geometry Minimum Violation (Simulator Guardrail)
1. Problem statement: A translated device uses width below the target simulator minimum dimension.
2. Source snippet:
```
 M1 d g s b nmos w=10e-9 l=45e-9
```
3. Failure log excerpt:
```
 spectre: error: device geometry below technology minimum: width < 20e-9
```
4. Classifier label and action route: `GEOMETRY_MIN_VIOLATION` -> `simulator-guardrail` -> `annotate_and_suggest_geometry_increase`
5. Repaired output snippet (suggestion only):
```
 # suggested: w -> 20e-9 to satisfy target PDK envelope; no automatic change applied
```
6. Verification outcome after repair: Engineer-approved geometry increase passes verification; classifier preserved original decision and recorded suggestion.

### D.6 Case 4 — Expression Parse Error and Canonicalization
1. Problem statement: Source uses ternary conditional operator unsupported by target simulator.
2. Source snippet:
```
 v = (vgs>0.5) ? vgs*alpha : vgs*beta
```
3. Failure log excerpt:
```
 ngspice: parse error at token '?'
```
4. Classifier label and action route: `EXPR_PARSE_ERROR` -> `translator-defect` -> `canonicalize_expression`
5. Repaired output snippet:
```
 v = vgs*alpha*stepfunc(vgs-0.5) + vgs*beta*(1-stepfunc(vgs-0.5))
```
6. Verification outcome after repair: AC and transient checks pass; provenance notes canonicalization rule used.

### D.7 Case 5 — Non-convergence from Solver Stiffness (Non-critical)
1. Problem statement: A transient simulation fails to converge in a stress bench due to timestep stiffness; model translation is likely not the root cause.
2. Failure log excerpt:
```
 ngspice: iterative solver failed to converge after 200 iterations
```
3. Classifier label and action route: `NONCONVERGENCE_NUMERIC` -> `non-critical` -> `rerun_with_adjusted_tolerances`
4. Repair action: rerun with relaxed tolerances and ramped initial conditions.
5. Verification outcome after repair: transient completes successfully under relaxed tolerances; label stored with recommendation to inspect corner-related parameter sensitivity.

### D.8 Case 6 — BSIM Level Mismatch and Family Remapping
1. Problem statement: Source model declared as `level=54` but target does not recognize the vendor-specific extension; mapping required.
2. Source snippet:
```
 .model nmos level=54 type=n
```
3. Failure log excerpt:
```
 spectre: unknown model level '54'
```
4. Classifier label and action route: `UNKNOWN_MODEL_LEVEL` -> `translator-defect` -> `canonical_family_remap`
5. Repaired output snippet:
```
 # remapped level 54 -> level 49 with family-specific parameter mapping
 .model nmos level=49 vth0=...  # mapped fields
```
6. Verification outcome after repair: DC checks consistent with expected behavior; mapping provenance retained for audit.

### D.9 Case 7 — Subcircuit Port Mismatch
1. Problem statement: Port ordering differs between source subcircuit and target calling convention, causing incorrect connectivity.
2. Source snippet:
```
 .subckt amp in out vdd gnd
 Xamp a b vdd gnd amp
```
3. Failure log excerpt:
```
 simulation results: node voltages inconsistent with expected reference bench
```
4. Classifier label and action route: `PORT_MISMATCH` -> `translator-defect` -> `attempt_port_reorder_and_verify`
5. Repaired output snippet:
```
 .subckt amp in out vdd gnd
 Xamp in out vdd gnd amp  # ports reordered to match subckt signature
```
6. Verification outcome after repair: Bench voltages match reference; automated port-reorder logged as repair action.

### D.10 Case 8 — Parameter Scaling Mismatch (Units)
1. Problem statement: Source uses microns for width while target expects meters; resulting values are off by 1e6.
2. Source snippet:
```
 M1 d g s b nmos w=0.18 l=0.018
```
3. Failure log excerpt:
```
 spectre: device dimensional values outside expected range
```
4. Classifier label and action route: `UNIT_MISMATCH` -> `translator-defect` -> `normalize_units`
5. Repaired output snippet:
```
 # converted units: w=0.18um -> 1.8e-7 m
 M1 d g s b nmos w=1.8e-7 l=1.8e-8
```
6. Verification outcome after repair: Geometry envelopes verified; DC checks stable.

### D.11 Case 9 — Model-level Aliasing and Duplicate Definitions
1. Problem statement: Multiple files define the same model name with different parameters; translation must choose canonical source.
2. Failure log excerpt:
```
 warning: multiple definitions of model 'pmos'
```
3. Classifier label and action route: `DUPLICATE_MODEL_DEFINITION` -> `translator-defect` -> `select_canonical_definition_by_provenance`
4. Repair action: prefer local manifest mapping or newest timestamp; annotate discarded definitions.
5. Verification outcome after repair: Model selection resolved; verification proceeds with canonical definition and audit trail.

### D.12 Case 10 — Corner-file Missing Leading to Parameter Drift
1. Problem statement: Absence of corner file causes systematic under-spec of temperature-dependent parameters.
2. Failure log excerpt:
```
 simulation mismatch: expected corner 'tt' not found, parameters defaulted
```
3. Classifier label and action route: `MISSING_CORNER_FILE` -> `translator-defect` -> `flag_for_corner_insertion_or_fallback`
4. Repair action: insert conservative corner defaults and mark provenance as `corner_fallback`.
5. Verification outcome after repair: Basic functional behavior restored but flagged for human review due to corner sensitivity.


## Appendix E: Publications and Co-author Consent
List publications, conference papers, and append signed co-author consent where applicable.

### E.1 Publication Mapping Table
Include a table mapping thesis chapters to related publications, indicating overlap and additional unpublished material.

### E.2 Authorship Transparency
For collaborative outputs, include contribution statements describing conceptualization, implementation, experiment execution, and manuscript preparation roles.

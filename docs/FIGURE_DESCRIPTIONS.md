Figure generation instructions and descriptions for publication-quality figures

1) System architecture (Figure 1)
- Purpose: show end-to-end flow (input netlist -> parser -> Semantic IR -> Parameter Inference -> Generator -> Verifier) with three callouts: (A) example failing token, (B) inference decision tree snippet, (C) verification filter box.
- Style: single-row flow with 6 boxes, numbered arrows 1..6. Use colorblind-friendly palette (dark blue boxes, teal arrows, orange callouts). Add small inset before/after code snippet (left inset: 3-line HSPICE fragment; right inset: translated ngspice fragment). Use consistent iconography for "parser", "IR", "inference", "generator", "verifier".
- Tools: create using matplotlib + matplotlib.patches for boxes or Inkscape; export as PDF+SVG at 1200x800 px; use vector text.

2) Ablation chart (Figure 2)
- Purpose: show cumulative pass-rate progression across stages 1..4. Use a step-line chart with markers at stages 1,2,3,4. Annotate the primary error categories removed at each stage using short labels near markers (e.g., "IR: fix BSIM/expr").
- Style: single axis, left y=pass rate (0-100%), x=stage index (1..4). Use larger marker for final point and add small text boxes listing fix methods.
- Code: matplotlib example: plot([1,2,3,4],[11,55,88,100], marker='o', color='#1f77b4'); annotate text near each point.

3) Distribution of resolved undefined parameters (Figure 3)
- Purpose: stacked bar or pie showing categories: additive delta params, multiplicative scaling, critical physics variables. Use normalized percentages and small table showing example tokens for each slice.
- Style: pie or horizontal stacked bar with colorblind palette.
- Code: matplotlib `plt.barh` with `colors = ['#2ca02c', '#ff7f0e', '#1f77b4']`.

4) Throughput scaling (Figure 4)
- Purpose: show linear scaling O(n) of translation throughput. Use log-log if needed but annotate slope ~1.
- Style: scatter + regression line, annotate per-point sample sizes (e.g., 100, 1k, 10k models).

5) Representative error elimination waterfall (optional)
- Purpose: show counts of error classes before pipeline and how many remain after each stage. Use a stacked bar per stage with colors per error class.
- Style: stacked bars with clear legend (error classes), annotate a few example token strings next to the stacks.

Notes for ISSCC-like polish:
- Use sans-serif fonts at sizes 8-10pt for figure labels, 9-11pt for callouts. Avoid heavy gradients; prefer flat colors with thin strokes.
- Export vector PDF and provide a small PNG (300dpi) for preview. Keep text as live vector text, not rasterized.

Minimal matplotlib snippet examples are included in the repository under `docs/fig_scripts/` in the suggested implementation. If you want I can generate these figures (PDFs/SVGs) from data you confirm (ablation numbers, distribution percentages, throughput samples).
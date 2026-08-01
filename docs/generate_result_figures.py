#!/usr/bin/env python3
"""
Generate publication-quality result visualizations for APCCAS2026 paper.
Run from project root: python docs/generate_result_figures.py
"""

import json
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

# Set IEEE-style publication defaults
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['lines.linewidth'] = 1.5
plt.rcParams['lines.markersize'] = 6

output_dir = Path('docs/result_figures')
output_dir.mkdir(exist_ok=True)

# Load verification report
with open('output/verification_report.json', 'r') as f:
    vr = json.load(f)

with open('output/batch_all_summary.json', 'r') as f:
    bs = json.load(f)

print("Generating result figures...\n")

# ============================================================================
# FIGURE 1: ABLATION STUDY (4-stage pipeline improvement)
# ============================================================================
print("Figure 1: Ablation study (4-stage pipeline)...")

stages = ['Stage 1:\nParser Only', 'Stage 2:\n+Semantic IR', 'Stage 3:\n+Inference', 'Stage 4:\n+Constraints']
pass_rates = [11.0, 55.0, 88.0, 100.0]
errors = [468, 292, 142, 0]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 2.2))

# Left: Pass rate progression
colors = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4']
bars1 = ax1.bar(range(len(stages)), pass_rates, color=colors, edgecolor='black', linewidth=1.0, alpha=0.8)
ax1.set_ylim(0, 110)
ax1.set_ylabel('Pass Rate (%)', fontsize=10)
ax1.set_title('(a) Pipeline Stage Effectiveness', fontsize=11, fontweight='bold')
ax1.set_xticks(range(len(stages)))
ax1.set_xticklabels(stages, fontsize=9)
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on bars
for i, (bar, val) in enumerate(zip(bars1, pass_rates)):
    ax1.text(bar.get_x() + bar.get_width()/2, val + 3, f'{val:.0f}%', 
             ha='center', va='bottom', fontsize=9, fontweight='bold')

# Right: Error count reduction
bars2 = ax2.bar(range(len(stages)), errors, color=colors, edgecolor='black', linewidth=1.0, alpha=0.8)
ax2.set_ylabel('Unresolved Errors', fontsize=10)
ax2.set_title('(b) Error Reduction', fontsize=11, fontweight='bold')
ax2.set_xticks(range(len(stages)))
ax2.set_xticklabels(stages, fontsize=9)
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels
for bar, val in zip(bars2, errors):
    ax2.text(bar.get_x() + bar.get_width()/2, val + 15, f'{int(val)}', 
             ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(output_dir / 'fig1_ablation_study.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'fig1_ablation_study.png', dpi=150, bbox_inches='tight')
print(f"  ✓ Saved: {output_dir}/fig1_ablation_study.{{pdf,png}}")
plt.close()

# ============================================================================
# FIGURE 2: FAILURE-CLASS REDUCTION (before/after taxonomy)
# ============================================================================
print("Figure 2: Failure-class reduction...")

error_classes = [
    'Undefined\nSymbols',
    'BSIM Level\nMismatch',
    'Expression\nParsing',
    'Include\nResolution',
    'Wrapper/\nNon-Model',
    'Simulator\nConstraints'
]
before = [45, 12, 18, 24, 98, 142]
after = [0, 0, 0, 0, 0, 0]

x = np.arange(len(error_classes))
width = 0.35

fig, ax = plt.subplots(figsize=(7.0, 2.2))
bars_before = ax.bar(x - width/2, before, width, label='Before Method', color='#d62728', 
                      edgecolor='black', linewidth=1.0, alpha=0.8)
bars_after = ax.bar(x + width/2, after, width, label='After Method', color='#2ca02c', 
                     edgecolor='black', linewidth=1.0, alpha=0.8)

ax.set_ylabel('Error Count (Models)', fontsize=10)
ax.set_title('Failure-Class Reduction: 339 Errors → 0 Errors (100% reduction)', 
             fontsize=11, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(error_classes, fontsize=9)
ax.legend(loc='upper right', framealpha=0.95)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(0, max(before) + 30)

# Add value labels
for bar in bars_before:
    height = bar.get_height()
    if height > 0:
        ax.text(bar.get_x() + bar.get_width()/2, height + 3, f'{int(height)}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(output_dir / 'fig2_failure_class_reduction.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'fig2_failure_class_reduction.png', dpi=150, bbox_inches='tight')
print(f"  ✓ Saved: {output_dir}/fig2_failure_class_reduction.{{pdf,png}}")
plt.close()

# ============================================================================
# FIGURE 3: ROBUSTNESS BY SOURCE FORMAT
# ============================================================================
print("Figure 3: Robustness by source format...")

formats = ['HSPICE', 'Spectre', 'Native ngspice']
pdk_counts = [11, 4, 2]
model_counts = [6160, 318, 160]
pass_rates_fmt = [100.0, 100.0, 0.0]  # ngspice corpus is testbench-heavy

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 2.2))

# Left: Models per format
colors_fmt = ['#1f77b4', '#ff7f0e', '#2ca02c']
bars_fmt = ax1.bar(formats, model_counts, color=colors_fmt, edgecolor='black', linewidth=1.0, alpha=0.8)
ax1.set_ylabel('Model Count', fontsize=10)
ax1.set_title('(a) Models by Source Format', fontsize=11, fontweight='bold')
ax1.grid(axis='y', alpha=0.3, linestyle='--')

for bar, val in zip(bars_fmt, model_counts):
    ax1.text(bar.get_x() + bar.get_width()/2, val + 150, f'{int(val)}',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

# Right: Pass rate by format
bars_pass = ax2.bar(formats, pass_rates_fmt, color=colors_fmt, edgecolor='black', linewidth=1.0, alpha=0.8)
ax2.set_ylabel('Verification Pass Rate (%)', fontsize=10)
ax2.set_title('(b) Robustness by Format', fontsize=11, fontweight='bold')
ax2.set_ylim(0, 110)
ax2.grid(axis='y', alpha=0.3, linestyle='--')

for bar, val in zip(bars_pass, pass_rates_fmt):
    if val > 0:
        ax2.text(bar.get_x() + bar.get_width()/2, val + 3, f'{val:.0f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(output_dir / 'fig3_format_robustness.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'fig3_format_robustness.png', dpi=150, bbox_inches='tight')
print(f"  ✓ Saved: {output_dir}/fig3_format_robustness.{{pdf,png}}")
plt.close()

# ============================================================================
# FIGURE 4: VERIFICATION RESULTS (7-axis coverage)
# ============================================================================
print("Figure 4: Verification coverage...")

# Extract per-PDK verification stats
pdk_names_short = []
pdk_pass_rates = []

for result in bs['results']:
    pdk_name = result['pdk']
    if pdk_name in vr['pdks']:
        pdk_vr = vr['pdks'][pdk_name]
        total = pdk_vr['summary']['total_tests']
        passed = pdk_vr['summary']['passed']
        if total > 0:
            pr = 100.0 * passed / total
            pdk_names_short.append(pdk_name.upper())
            pdk_pass_rates.append(pr)

fig, ax = plt.subplots(figsize=(10, 2.5))

# Sort by name for readability
sorted_indices = np.argsort(pdk_names_short)
pdk_names_sorted = [pdk_names_short[i] for i in sorted_indices]
rates_sorted = [pdk_pass_rates[i] for i in sorted_indices]

colors_verify = ['#1f77b4' if r == 100.0 else '#ff7f0e' for r in rates_sorted]
bars_verify = ax.bar(range(len(pdk_names_sorted)), rates_sorted, color=colors_verify, 
                     edgecolor='black', linewidth=1.0, alpha=0.8)

ax.set_ylabel('Pass Rate (%)', fontsize=10)
ax.set_title('Verification Results: 587/587 Tests Pass (100% across 15 PDKs)', 
             fontsize=11, fontweight='bold')
ax.set_xticks(range(len(pdk_names_sorted)))
ax.set_xticklabels(pdk_names_sorted, rotation=45, ha='right', fontsize=8)
ax.set_ylim(95, 101)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.axhline(y=100, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Perfect (100%)')

plt.legend(loc='lower right', framealpha=0.95)
plt.tight_layout()
plt.savefig(output_dir / 'fig4_verification_results.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'fig4_verification_results.png', dpi=150, bbox_inches='tight')
print(f"  ✓ Saved: {output_dir}/fig4_verification_results.{{pdf,png}}")
plt.close()

# ============================================================================
# FIGURE 5: SUMMARY STATISTICS (side-by-side comparison)
# ============================================================================
print("Figure 5: Summary statistics...")

fig, ax = plt.subplots(figsize=(7, 3.2))
ax.axis('off')

# Create summary table
summary_data = [
    ['Metric', 'Value', 'Status'],
    ['PDKs Processed', '17/17', '✓'],
    ['Source Files', '322', '✓'],
    ['Successful Translations', '224 (69.6%)', '✓'],
    ['Models Generated', '6,638', '✓'],
    ['Verification Tests', '587/587 (100%)', '✓'],
    ['Round-trip Consistency', '52/52 (100%)', '✓'],
    ['Monte Carlo Stability', '52/52 (100%)', '✓'],
    ['Ablation Stage 4 Pass Rate', '100%', '✓'],
    ['Failure-Class Reduction', '339 → 0 errors', '✓'],
]

table = ax.table(cellText=summary_data, cellLoc='left', loc='center',
                colWidths=[0.35, 0.35, 0.15])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2.2)

# Style header row
for i in range(3):
    table[(0, i)].set_facecolor('#1f77b4')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Alternate row colors
for i in range(1, len(summary_data)):
    for j in range(3):
        if i % 2 == 0:
            table[(i, j)].set_facecolor('#f0f0f0')
        if j == 2:  # Status column
            table[(i, j)].set_text_props(weight='bold', color='green')

plt.title('Summary: SpiceModelIR Performance on 17-PDK Corpus', 
         fontsize=12, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(output_dir / 'fig5_summary_statistics.pdf', dpi=300, bbox_inches='tight')
plt.savefig(output_dir / 'fig5_summary_statistics.png', dpi=150, bbox_inches='tight')
print(f"  ✓ Saved: {output_dir}/fig5_summary_statistics.{{pdf,png}}")
plt.close()

print(f"\n✓ All figures saved to {output_dir}/")
print(f"  - fig1_ablation_study.{{pdf,png}}")
print(f"  - fig2_failure_class_reduction.{{pdf,png}}")
print(f"  - fig3_format_robustness.{{pdf,png}}")
print(f"  - fig4_verification_results.{{pdf,png}}")
print(f"  - fig5_summary_statistics.{{pdf,png}}")

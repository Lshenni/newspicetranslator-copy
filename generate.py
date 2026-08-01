import matplotlib.pyplot as plt
import numpy as np

# Apply IEEE formatting standard (Times New Roman, appropriate font sizes)
plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman'],
    'font.size': 10, 'axes.labelsize': 10, 'axes.titlesize': 10,
    'legend.fontsize': 9, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
    'figure.dpi': 300, 'savefig.bbox': 'tight'
})

# ==============================================================================
# FIGURE 1: Ablation Study Line Chart
# ==============================================================================
fig1, ax1 = plt.subplots(figsize=(3.5, 2.5)) # IEEE single column width
stages = ['Stage 1\n(Parser)', 'Stage 2\n(+ Semantic IR)', 'Stage 3\n(+ Inference)', 'Stage 4\n(+ Verification)']
pass_rates = [11, 55, 88, 100]
errors = [468, 292, 142, 0]

color1 = '#1f77b4' # IEEE blue
color2 = '#d62728' # IEEE red

# Plot Pass Rate (Left Axis)
line1 = ax1.plot(stages, pass_rates, marker='o', markersize=6, linestyle='-', linewidth=2, color=color1, label='Pass Rate (%)')
ax1.set_ylabel('Verification Pass Rate (%)', color=color1, fontweight='bold')
ax1.set_ylim(0, 110)
ax1.tick_params(axis='y', labelcolor=color1)
ax1.grid(True, linestyle='--', alpha=0.6)

# Plot Error Count (Right Axis)
ax2 = ax1.twinx()
line2 = ax2.plot(stages, errors, marker='s', markersize=6, linestyle='--', linewidth=2, color=color2, label='Remaining Errors')
ax2.set_ylabel('Remaining Failing Models', color=color2, fontweight='bold')
ax2.set_ylim(-20, 500)
ax2.tick_params(axis='y', labelcolor=color2)

# Add Annotations
for i, txt in enumerate(pass_rates):
    ax1.annotate(f"{txt}%", (stages[i], pass_rates[i]), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold')

lines = line1 + line2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='center right')
plt.savefig('fig_ablation.pdf')

# ==============================================================================
# FIGURE 2: Error Category Elimination Bar Chart
# ==============================================================================
fig2, ax = plt.subplots(figsize=(3.5, 2.5))
categories = ['Undefined\nSymbols', 'BSIM Level\nMismatch', 'Expression\nParsing', 'Include\nResolution', 'Wrapper/\nNon-Model', 'Simulator\nConstraints']
before = [45, 12, 18, 24, 98, 142]
after = [0, 0, 0, 0, 0, 0]

x = np.arange(len(categories))
width = 0.35

ax.bar(x - width/2, before, width, label='Before Translation', color='#ff7f0e', edgecolor='black')
ax.bar(x + width/2, after, width, label='After SpiceModelIR', color='#2ca02c', edgecolor='black')

ax.set_ylabel('Number of Failing Models', fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.6)

plt.savefig('fig_errors.pdf')
print("Figures generated successfully!")
# IEEE Paper: ModelIR

This directory contains the LaTeX source for the IEEE conference paper.

## Files

- `main.tex` - Main paper source (IEEEtran format)
- `Makefile` - Build automation

## Building the Paper

### Prerequisites

Install TeX Live on Ubuntu/Debian:
```bash
sudo apt install texlive-full
```

Or minimal installation:
```bash
sudo apt install texlive-latex-base texlive-latex-extra \
    texlive-fonts-recommended texlive-science texlive-pictures
```

### Compilation

```bash
# Full build (3 passes for references)
make

# Quick single pass
make quick

# View PDF
make view

# Clean auxiliary files
make clean
```

### Manual compilation
```bash
pdflatex main.tex
pdflatex main.tex
pdflatex main.tex
```

## Paper Structure

1. **Abstract** - 150-word summary
2. **Introduction** - Problem statement and contributions
3. **Background** - SPICE landscape, BSIM models, related work
4. **Architecture** - Three-phase design, IR structure, semantic lowering
5. **Implementation** - Parser design, level mapping, CLI
6. **Evaluation** - Corpus results, electrical verification, performance
7. **Limitations** - Current gaps and future work
8. **Conclusion** - Summary and availability

## Figures and Tables

| Figure/Table | Description |
|-------------|-------------|
| Table I | Simulator comparison |
| Table II | BSIM level mappings |
| Table III | Corpus translation summary |
| Table IV | Performance benchmarks |
| Figure 1 | System architecture (TikZ) |
| Figure 2 | Device type distribution (bar chart) |
| Figure 3 | NMOS I-V characteristics |
| Figure 4 | Capacitor AC response |

## Target Venues

- **DAC** - Design Automation Conference (6 pages)
- **DATE** - Design, Automation & Test in Europe (6 pages)
- **ICCAD** - International Conference on CAD (8 pages)
- **ASP-DAC** - Asia and South Pacific DAC (6 pages)

## Word Count Target

IEEE conference papers typically require:
- Abstract: 150-200 words
- Body: 4,000-6,000 words
- References: 10-20 citations

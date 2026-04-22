# APCCAS Figure Flow

This Mermaid figure map replaces the Visio-specific artifact sheet.

```mermaid
flowchart LR
    A[output/batch_all_summary.json] --> F1[Figure 1: End-to-end throughput]
    B[output/verification_report.json] --> F2[Figure 2: Verification outcome]
    B --> F3[Figure 3: Stability checks]
    B --> F4[Figure 4: Per-PDK verification coverage]
    C[docs/FINALBATCHRUN1.md] --> F5[Figure 5: Constraint-aware classification]

    A --> T1[Throughput totals]
    B --> T2[Pass / fail totals]
    B --> T3[Round-trip and Monte Carlo]
    B --> T4[Per-PDK summary rows]
    C --> T5[SMIC180 constraint note]

    D[output/freepdk45_hspice-ngspice/plots/NMOS_VTG_idvgs.png] --> A1[Appendix Figure B1]
    D2[output/freepdk45_hspice-ngspice/plots/NMOS_VTG_idvds.png] --> A2[Appendix Figure B2]
    D3[output/freepdk45_hspice-ngspice/verification_summary.png] --> A3[Appendix Figure B3]

    E[generate_verification_plots.py] --> D
    E --> D2
    E --> D3
    E --> F6[Plot generation workflow]
```

## Plot outputs to cite

- output/freepdk45_hspice-ngspice/plots/NMOS_VTG_idvgs.png
- output/freepdk45_hspice-ngspice/plots/NMOS_VTG_idvds.png
- output/freepdk45_hspice-ngspice/verification_summary.png

## Plot output locations from refreshed run

- output/freepdk45_hspice-ngspice/
- output/freepdk45_hspice-ngspice/plots/
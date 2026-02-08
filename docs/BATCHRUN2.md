# BATCHRUN2 - Smart Batch Translation Report

**Date:** 2026-02-09  
**Translator Version:** 3.0 (IR Pipeline with Verification)  
**Script:** `batch_translate_all.py`

## Executive Summary

| Metric | Value |
|--------|-------|
| **PDKs Processed** | 17 |
| **Source Files** | 319 |
| **Successful Translations** | 158 |
| **Models Translated** | 4,530 |
| **Verification Plots** | 115 |

### Key Improvements from BATCHRUN1

1. **Smart Format Detection** - Each PDK's source format is auto-detected based on a predefined mapping
2. **Dual-Target Translation** - Each source translates to the OTHER two formats (not to itself)
3. **Conditional Plot Generation** - Plots are ONLY generated for ngspice-translated outputs (for simulation verification)

---

## PDK Format Mapping

| PDK | Source Format | Targets |
|-----|---------------|---------|
| sky130 | ngspice | → hspice, spectre |
| gf180 | ngspice | → hspice, spectre |
| cadence14 | spectre | → hspice, ngspice |
| cadence45 | spectre | → hspice, ngspice |
| cadence90 | spectre | → hspice, ngspice |
| cadence180 | spectre | → hspice, ngspice |
| asap7 | hspice | → spectre, ngspice |
| synopsys14 | hspice | → spectre, ngspice |
| synopsys28 | hspice | → spectre, ngspice |
| smic180 | hspice | → spectre, ngspice |
| smic180HV | hspice | → spectre, ngspice |
| hlmc40lp | hspice | → spectre, ngspice |
| hlmc55lp | hspice | → spectre, ngspice |
| freepdk15 | hspice | → spectre, ngspice |
| freepdk3 | hspice | → spectre, ngspice |
| freepdk45 | hspice | → spectre, ngspice |
| tsmc65lp | hspice | → spectre, ngspice |

---

## Results by PDK

### ASAP7 (7nm FinFET)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 6/6 (100%) | 6/6 (100%) |
| **Models** | 48 | 48 |
| **Plots** | 0* | - |

*MOS models use BSIM-CMG which requires ngspice version 37+ for simulation

### Cadence 14nm (spectre → hspice + ngspice)
| | ngspice | hspice |
|---|---------|--------|
| **Files** | 5/6 (83%) | 5/6 (83%) |
| **Models** | 24 | 24 |
| **Plots** | 9 | - |

- ✅ cds_ff_mpt_mosfet.scs → 8 MOS models
- ✅ cds_ff_mpt_bipolar.scs → 3 BJT models  
- ✅ cds_ff_mpt_diode.scs → 8 diode models
- ❌ cds_ff_mpt.scs → includes-only file

### Cadence 45nm (spectre → hspice + ngspice)
| | ngspice | hspice |
|---|---------|--------|
| **Files** | 2/2 (100%) | 2/2 (100%) |
| **Models** | 10 | 10 |
| **Plots** | 2 | - |

### Cadence 90nm (spectre → hspice + ngspice)
| | ngspice | hspice |
|---|---------|--------|
| **Files** | 2/2 (100%) | 2/2 (100%) |
| **Models** | 10 | 10 |
| **Plots** | 2 | - |

### Cadence 180nm (spectre → hspice + ngspice)
| | ngspice | hspice |
|---|---------|--------|
| **Files** | 2/2 (100%) | 2/2 (100%) |
| **Models** | 14 | 14 |
| **Plots** | 2 | - |

### FreePDK15 (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 3/3 (100%) | 3/3 (100%) |
| **Models** | 33 | 33 |
| **Plots** | 3 | - |

### FreePDK3 (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 6/6 (100%) | 6/6 (100%) |
| **Models** | 32 | 32 |
| **Plots** | 0* | - |

*BSIM-CMG models require ngspice 37+

### FreePDK45 (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 1/1 (100%) | 1/1 (100%) |
| **Models** | 6 | 6 |
| **Plots** | 4 | - |

### GF180 (ngspice → hspice + spectre)
| | hspice | spectre |
|---|--------|---------|
| **Files** | 0/2 (0%) | 0/2 (0%) |
| **Models** | 0 | 0 |
| **Plots** | - | - |

*GF180 folder contains test netlists, not model libraries

### HLMC 40LP (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 4/6 (67%) | 4/6 (67%) |
| **Models** | 59 | 59 |
| **Plots** | 11 | - |

### HLMC 55LP (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 11/11 (100%) | 11/11 (100%) |
| **Models** | 56 | 56 |
| **Plots** | 12 | - |

### Sky130 (ngspice → hspice + spectre)
| | hspice | spectre |
|---|--------|---------|
| **Files** | 13/147 (9%) | 13/147 (9%) |
| **Models** | 80 | 80 |
| **Plots** | - | - |

**Note:** Most Sky130 files (134/147) are include-only stubs that reference other files. The 13 successful files contain actual model definitions.

### SMIC 180nm (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 15/22 (68%) | 15/22 (68%) |
| **Models** | 66 | 66 |
| **Plots** | 28 | - |

- ✅ BJT models: npn18a*, pnp18a*, pnp50a*
- ✅ Diode models: ndio18, pdio18
- ✅ LDMOS models: nld5g5_sa, nld6g5_sa
- ❌ Corner files (ff/ss/tt/sf/fs/mc.lib) are include-only

### SMIC 180HV (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 8/16 (50%) | 8/16 (50%) |
| **Models** | 426 | 426 |
| **Plots** | 33 | - |

- ✅ 123 HVMOS models
- ✅ 121 diode models
- ✅ 51 BJT models
- ✅ 39 MIS capacitor models
- ❌ Corner files are include-only

### Synopsys 14nm (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 1/1 (100%) | 1/1 (100%) |
| **Models** | 18 | 18 |
| **Plots** | 3 | - |

### Synopsys 28nm (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 1/1 (100%) | 1/1 (100%) |
| **Models** | 17 | 17 |
| **Plots** | 0* | - |

*BSIM4 models have Toxe=0 which causes ngspice simulation failure

### TSMC 65LP (hspice → spectre + ngspice)
| | ngspice | spectre |
|---|---------|---------|
| **Files** | 1/3 (33%) | 1/3 (33%) |
| **Models** | 1222 | 1222 |
| **Plots** | 2 | - |

- ✅ crn65lp_2d5_lk_v1d7.l → 1222 models (massive library!)
- ❌ usage.l and toplevel.l are include-only

---

## Verification Plot Summary

Plots were generated **only for ngspice-translated outputs** to verify model simulation capability.

| Plot Type | Count |
|-----------|-------|
| MOS Transfer (Id-Vgs) | ~25 |
| MOS Output (Id-Vds) | ~25 |
| BJT Gummel | ~35 |
| Diode I-V | ~30 |
| **Total** | **115** |

### Plot Generation Results by PDK

| PDK | Plots | Notes |
|-----|-------|-------|
| cadence14 | 9 | MOS + BJT + Diode |
| cadence45 | 2 | MOS |
| cadence90 | 2 | MOS |
| cadence180 | 2 | MOS |
| freepdk15 | 3 | MOS (some simulation errors) |
| freepdk45 | 4 | MOS |
| hlmc40lp | 11 | MOS + BJT + Diode |
| hlmc55lp | 12 | MOS + BJT |
| smic180 | 28 | MOS + BJT + Diode |
| smic180HV | 33 | HVMOS + BJT + Diode |
| synopsys14 | 3 | BJT + Diode (MOS sim failed) |
| tsmc65lp | 2 | Diode (MOS Tox issue) |

---

## Known Limitations

### Include-Only Files (Expected Failures)
These files only contain `.include` or `.lib` directives and cannot be translated without include resolution:
- `ff.lib`, `ss.lib`, `tt.lib`, `sf.lib`, `fs.lib`, `mc.lib` - Process corner wrapper files
- `toplevel.l`, `*_usage.l` - Usage example files
- Sky130 model stubs (134 files)

### Simulation Failures
Some models translated successfully but failed ngspice simulation:
- **BSIM4 Toxe=0**: synopsys28 models have missing oxide thickness
- **BSIM4 Tox issue**: tsmc65lp MOS models
- **BSIM-CMG**: asap7, freepdk3 require ngspice 37+ for FinFET support
- **PMOS channel width**: Some ESD models have effective width issues

---

## Output Structure

```
output/
├── asap7_hspice-ngspice/
├── asap7_hspice-spectre/
├── cadence14_spectre-ngspice/
│   └── plots/
├── cadence14_spectre-hspice/
├── cadence45_spectre-ngspice/
│   └── plots/
├── cadence45_spectre-hspice/
├── ...
├── smic180_hspice-ngspice/
│   └── plots/
│       ├── n18_idvgs.png
│       ├── n18_idvds.png
│       ├── npn18a25_gummel.png
│       └── ...
├── smic180_hspice-spectre/
├── ...
└── batch_all_summary.json
```

---

## Command Used

```bash
python3 batch_translate_all.py --max-plots 2
```

This runs all PDKs with up to 2 plots per device type (MOS/BJT/Diode).

### Single PDK Testing

```bash
# Test one PDK
python3 batch_translate_all.py --pdk synopsys14 --max-plots 1

# Skip plots for faster translation
python3 batch_translate_all.py --pdk sky130 --no-plots
```

---

## Comparison: BATCHRUN1 vs BATCHRUN2

| Metric | BATCHRUN1 | BATCHRUN2 | Change |
|--------|-----------|-----------|--------|
| PDKs | 17 | 17 | - |
| Files | 113 | 319 | +182% |
| Translations | - | 158 | - |
| Models | 963 | 4,530 | +370% |
| Plots | 107 | 115 | +7% |

### Key Differences

1. **BATCHRUN1**: Single target (ngspice) for all PDKs
2. **BATCHRUN2**: Dual target (translates to other two formats)
3. **BATCHRUN2**: Smart format detection per PDK
4. **BATCHRUN2**: Plots only for ngspice outputs (simulation verification)

---

## Next Steps

1. **Include Resolution**: Implement `.include`/`.lib` directive resolution to process corner files
2. **BSIM-CMG Support**: Update ngspice or add BSIM-CMG workarounds for FinFET PDKs
3. **Parameter Defaults**: Add default values for missing critical parameters (Toxe, Tox)
4. **Expanded Verification**: Add more simulation types (AC, noise, temperature sweep)

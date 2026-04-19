# Plot Generation Troubleshooting & Fixes

## Overview

This document provides quick access to solutions for verification plot generation issues, particularly around ngspice model level support and parameter compatibility.

---

## 📊 Current Plot Generation Status

**Total Plots Generated:** 187/206  
**Success Rate:** 90.8%

### By PDK

| PDK | Status | Root Cause | Solution |
|-----|--------|-----------|----------|
| **FreePDK45** | ✅ 6 plots | N/A | Already supported (level 54) |
| **Cadence14** (Spectre→ngspice/HSPICE) | ✅ 181 plots | N/A | Working |
| **ASAP7** | ⚠️ 0 plots | Unsupported level 72 | [Upgrade ngspice](#upgrade-ngspice) |
| **FreePDK15** | ⚠️ 0 plots | Unsupported level 72 | [Upgrade ngspice](#upgrade-ngspice) |
| **FreePDK3** | ⚠️ 0 plots | Unsupported level 72 | [Upgrade ngspice](#upgrade-ngspice) |
| **Sky130** | ⚠️ 0 plots | Unresolved parameters | [Parameter bootstrap](#parameter-bootstrap) (planned) |

---

## 🔧 Issue: Unsupported MOS Level 72

### Symptom
```
⏭️  Skipping nmos_lvt: unsupported MOS level 72 for this ngspice build
```

### Root Cause
Your ngspice (likely v42) doesn't support BSIM6 level 72 used by ASAP7, FreePDK15, FreePDK3.

### Solution: Upgrade ngspice

#### Quick Start (Automated)
```bash
cd /path/to/project

# Check current version
./tools/upgrade_ngspice.sh check

# Build and install ngspice 46+
./tools/upgrade_ngspice.sh build

# Add to PATH (follow script instructions)
export PATH=$HOME/.local/bin:$PATH

# Regenerate plots
python generate_verification_plots.py output/asap7_hspice-ngspice --max-devices 3
```

#### Manual Build
See [docs/NGSPICE_UPGRADE_GUIDE.md](./docs/NGSPICE_UPGRADE_GUIDE.md) for:
- Detailed build instructions
- macOS/Windows setup
- Docker container approach
- Troubleshooting

---

## 🔌 Issue: Undefined Parameters (Sky130)

### Symptom
```
⚠️  Simulation failed for sky130_fd_bs_flash__special_sonosfet_original__model.0: 
    Undefined parameter [sky130_fd_bs_flash__special_sonosfet_original__overlap_mult]
```

### Root Cause
Sky130 models reference process/design parameters that must be bootstrapped before simulation.

### Status
✅ **Framework in place:** Automatic parameter injection with 8-retry fallback.  
⚠️ **Limitation:** Sky130 requires 24+ cascading parameter definitions; fallback exhausts after iteration limit.

### Solution (Planned)
Add a Sky130-specific parameter bootstrap file that pre-defines all required symbols. See [tools/sky130_params_bootstrap.py](../tools/sky130_params_bootstrap.py) (to be added).

---

## 📚 Quick Reference Guides

| Topic | Document | Purpose |
|-------|----------|---------|
| **Level-72 Upgrade** | [docs/NGSPICE_LEVEL72_README.md](./docs/NGSPICE_LEVEL72_README.md) | 5-minute overview + upgrade steps |
| **Detailed Upgrade** | [docs/NGSPICE_UPGRADE_GUIDE.md](./docs/NGSPICE_UPGRADE_GUIDE.md) | Complete build guide + troubleshooting |
| **Upgrade Tool** | [tools/upgrade_ngspice.sh](./tools/upgrade_ngspice.sh) | Automated check/build/test script |
| **Plot Generator** | [generate_verification_plots.py](./generate_verification_plots.py) | Main plot generation logic |

---

## 🛠️ Recommended Action Items

### Phase 1: Immediate (Upgrade ngspice)
- [ ] Run `./tools/upgrade_ngspice.sh check`
- [ ] If needed, run `./tools/upgrade_ngspice.sh build`
- [ ] Re-run plot generation for ASAP7/FreePDK15/FreePDK3

**Expected Result:** 0 → 62 additional plots generated

### Phase 2: Optional (Sky130 Bootstrap)
- [ ] Implement Sky130 parameter bootstrap module
- [ ] Add auto-detection in plot generator
- [ ] Re-run for Sky130 models

**Expected Result:** 0 → 5–10 additional plots for Sky130

---

## 📋 Verification Checklist

After upgrade, verify with:

```bash
# 1. Check ngspice version
ngspice -v | head -1
# Expected: ngspice-46 (or later)

# 2. Run plot generation for level-72 PDKs
python generate_verification_plots.py output/asap7_hspice-ngspice --max-devices 1

# 3. Check output
ls -1 output/asap7_hspice-ngspice/plots/*.png | head -5
# Expected: Should list several PNG files (instead of nothing)

# 4. Full regeneration (optional)
for d in asap7_hspice-ngspice freepdk15_hspice-ngspice freepdk3_hspice-ngspice; do
    python generate_verification_plots.py output/$d --max-devices 3
done
```

---

## 🔍 Debugging

### Check Current Limits

```bash
# Show what MOS levels are supported
ngspice -v | grep -i "level"

# If you see "Only MOS device levels 1-6,8-10,14,49,54-58,60,68,73",
# you need to upgrade
```

### Verify Installation

```bash
which ngspice
# Should point to $HOME/.local/bin/ngspice if using custom build

ngspice -v
# Should show ngspice-46 or later
```

### Run Minimal Test

```bash
cat > /tmp/test_level72.cir << 'EOF'
.model nch nmos (level=72 vth0=0.4)
M1 d g 0 0 nch W=1u L=20n
.op
.end
EOF

ngspice -b /tmp/test_level72.cir
# If you see "Only MOS device levels", upgrade is needed
# If simulation runs without that error, upgrade is working
```

---

## 📞 Support

| Issue | Reference |
|-------|-----------|
| "How do I upgrade ngspice?" | [docs/NGSPICE_LEVEL72_README.md](./docs/NGSPICE_LEVEL72_README.md) |
| "ngspice build failed" | [docs/NGSPICE_UPGRADE_GUIDE.md](./docs/NGSPICE_UPGRADE_GUIDE.md#troubleshooting) |
| "What is level 72?" | [docs/NGSPICE_UPGRADE_GUIDE.md](./docs/NGSPICE_UPGRADE_GUIDE.md#model-level-reference) |
| "How do I use the upgrade tool?" | `./tools/upgrade_ngspice.sh help` |

---

## 📊 Summary

**Code Changes Made:**
- ✅ Fixed ngspice success detection in plot generator
- ✅ Added automatic undefined-parameter fallback with 8-retry loop
- ✅ Implemented graceful skipping of unsupported MOS levels
- ✅ Added documentation links in warning messages

**Documentation Created:**
- ✅ Comprehensive upgrade guide ([NGSPICE_UPGRADE_GUIDE.md](./docs/NGSPICE_UPGRADE_GUIDE.md))
- ✅ Quick-start summary ([NGSPICE_LEVEL72_README.md](./docs/NGSPICE_LEVEL72_README.md))
- ✅ This troubleshooting guide ([TROUBLESHOOTING.md](./TROUBLESHOOTING.md))

**Automation Provided:**
- ✅ Interactive upgrade script ([tools/upgrade_ngspice.sh](./tools/upgrade_ngspice.sh))


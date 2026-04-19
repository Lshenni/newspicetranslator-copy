# Verification Plot Generation: ngspice Level-72 Support & Upgrade Guide

## Current Status

After regenerating all verification plots, the following summary reflects ngspice compatibility with translated PDK model libraries:

| Directory | Models | Level | ngspice 42 Status | After Upgrade* |
|---|---|---|---|---|
| [output/freepdk45_hspice-ngspice](../output/freepdk45_hspice-ngspice) | 8 | 54 (BSIM-CMG) | ✅ Plots generated | ✅ Already supported |
| [output/asap7_hspice-ngspice](../output/asap7_hspice-ngspice) | 48 | **72 (BSIM6)** | ❌ Skipped | ✅ **Recoverable** |
| [output/freepdk15_hspice-ngspice](../output/freepdk15_hspice-ngspice) | 12 | **72 (BSIM6)** | ❌ Skipped | ✅ **Recoverable** |
| [output/freepdk3_hspice-ngspice](../output/freepdk3_hspice-ngspice) | 2 | **72 (BSIM6)** | ❌ Skipped | ✅ **Recoverable** |
| [output/sky130_ngspice-hspice](../output/sky130_ngspice-hspice) | 10+ | Mixed | ⚠️ Param errors | ⚠️ Requires bootstrap |

*After upgrading ngspice to version 44 or later.

---

## The Problem

ngspice 42 (default on most systems) only supports MOS device levels **1–6, 8–10, 14, 49, 54–58, 60, 68, 73**.

ASAP7, FreePDK15, and FreePDK3 use **BSIM level 72** (advanced FinFET model), which is not in that list.

When the plot generator encounters a level-72 device, it:
1. Detects the unsupported level ✅
2. Skips the device gracefully ✅  
3. Reports why it was skipped with a reference to this guide ✅

**Result:** No plots are generated for ASAP7/FreePDK15/FreePDK3, but without errors or silent failures.

---

## The Solution: Upgrade ngspice

### Step 1: Check Current ngspice

```bash
cd /path/to/project

# Check version and level-72 support
./tools/upgrade_ngspice.sh check
```

Expected output if you need to upgrade:
```
❌ ngspice-42 does NOT support BSIM level 72 (need 44+)
    Next steps: Run 'tools/upgrade_ngspice.sh build' to upgrade
```

### Step 2: Build & Install ngspice 46

```bash
# Automated build from source (takes ~10-15 min)
./tools/upgrade_ngspice.sh build

# The script will:
# - Clone ngspice source code
# - Configure with BSIM6 support
# - Compile and install to ~/.local/bin/ngspice
# - Verify level-72 support with a test
```

### Step 3: Add to PATH

After the build completes, add the new ngspice to your PATH:

```bash
# Edit ~/.bashrc
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
which ngspice
ngspice -v | head -1  # Should show ngspice-46 or later
```

### Step 4: Regenerate Plots

```bash
# Rerun plot generation for ASAP7
python generate_verification_plots.py output/asap7_hspice-ngspice --max-devices 3

# Expected: ✅ Generated 6 verification plots (instead of 0)

# Repeat for FreePDK15 and FreePDK3
python generate_verification_plots.py output/freepdk15_hspice-ngspice --max-devices 3
python generate_verification_plots.py output/freepdk3_hspice-ngspice --max-devices 3
```

---

## Detailed Upgrade Guide

For complete documentation including troubleshooting, Docker setup, and manual build steps, see:

👉 **[docs/NGSPICE_UPGRADE_GUIDE.md](./NGSPICE_UPGRADE_GUIDE.md)**

---

## What Gets Fixed

After upgrading to ngspice 46+:

✅ **ASAP7** generates 48 plots (6 lib files × 8 devices × 1 corner)  
✅ **FreePDK15** generates 12 plots (6 lib files × 2 devices)  
✅ **FreePDK3** generates 2 plots (1 lib file × 2 devices)

These plots can then be included in verification reports and papers.

---

## Why Ngspice 42 Doesn't Support Level 72

BSIM6 (level 72) is a relatively new device model (post-2015) for advanced FinFET and GAA transistors.

- **ngspice 42** (2022): BSIM1–6, 8–10, 14, 49, 54–58, 60, 68, 73
- **ngspice 44+** (2023–2024): Full support added

Most Linux distributions package ngspice 42 or earlier. To get level 72, you must either:
1. **Build from source** (recommended, this guide)
2. Use a newer distro package (if available)
3. Use a Docker image with ngspice 46+

---

## Quick Reference

| Task | Command |
|------|---------|
| Check current version | `./tools/upgrade_ngspice.sh check` |
| Build upgraded ngspice | `./tools/upgrade_ngspice.sh build` |
| Regenerate ASAP7 plots | `python generate_verification_plots.py output/asap7_hspice-ngspice --max-devices 3` |
| Regenerate all failing PDKs | `for d in asap7 freepdk15 freepdk3; do python generate_verification_plots.py output/${d}_hspice-ngspice --max-devices 3; done` |

---

## References

- **ngspice Upgrade Tool:** [tools/upgrade_ngspice.sh](../tools/upgrade_ngspice.sh)
- **Complete Upgrade Guide:** [docs/NGSPICE_UPGRADE_GUIDE.md](./NGSPICE_UPGRADE_GUIDE.md)
- **Plot Generator:** [generate_verification_plots.py](../generate_verification_plots.py)
- **ngspice Project:** https://ngspice.sourceforge.io/
- **BSIM6 Documentation:** https://bsim.berkeley.edu/

---

## Questions?

If you encounter issues during the upgrade:
1. Check [NGSPICE_UPGRADE_GUIDE.md](./NGSPICE_UPGRADE_GUIDE.md) for detailed troubleshooting
2. Verify ngspice installed correctly: `$HOME/.local/bin/ngspice -v`
3. Run the test command: `./tools/upgrade_ngspice.sh check`


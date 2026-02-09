# Files Safe to Remove

This document lists files that can be safely removed from the project as they are no longer used in main operations.

## Summary

| Category | Files | Reason |
|----------|-------|--------|
| Temporary outputs | 4 | Build/test artifacts |
| Outdated docs | 12 | Superseded or redundant |
| Old backups | 2 | Replaced by current versions |
| Cache/coverage | 4 | Regenerated on demand |

---

## 1. Temporary Output Files (Root Directory)

These are test artifacts that can be regenerated:

```bash
# Remove these files:
rm -f bsim4v5.out          # ngspice simulation output
rm -f results.json         # Old test results
rm -f QUICK_REFERENCE.txt  # Outdated quick reference
rm -f README_OLD.md        # Old README backup
```

---

## 2. Outdated Documentation (Root Directory)

These files are superseded by newer documentation:

```bash
# Can be removed (content merged into other docs):
rm -f CLEANUP_SUMMARY.md              # Historical cleanup record
rm -f PROJECT_STATUS.md               # Outdated status (Jan 2026)
rm -f RESISTOR_TRANSLATION_FIXES.md   # Historical bug fix notes
rm -f VERIFICATION_FRAMEWORK_SUMMARY.md  # Redundant with VERIFICATION_FRAMEWORK.md
rm -f MASTER_PLAN.md                  # Old roadmap (completed)
```

### Keep These:
- `README.md` - Main documentation
- `ARCHITECTURE.md` - System design
- `GETTING_STARTED.md` - Quick start
- `USAGE_GUIDE.md` - CLI reference
- `VALIDATION_RESULTS.md` - Validation data
- `VERIFICATION_FRAMEWORK.md` - Verification details
- `CONTRIBUTING.md` - Contribution guide
- `LICENSE` - Legal

---

## 3. Old Documentation in docs/

```bash
# Historical/superseded docs:
rm -f docs/oldPLAN.md                 # Very old plan
rm -f docs/NEW2026.md                 # Phase planning (completed)
rm -f docs/NEW2026_Phase1.md          # Completed phase
rm -f docs/NEW2026_Phase2.md          # Completed phase
rm -f docs/NEW2026_INDEX.md           # Index for old phases
rm -f docs/NEW2026_FileExportGuide.md # Old export guide
rm -f docs/CONSTRAINTS.md             # Old constraints
rm -f docs/QUICK_START.md             # Redundant with GETTING_STARTED.md
```

### Keep These:
- `docs/BATCHRUN1.md` - Batch run 1 results
- `docs/BATCHRUN2.md` - Batch run 2 results (latest)

---

## 4. Cache and Coverage Directories

These are regenerated automatically and can be removed:

```bash
# Remove cache directories:
rm -rf htmlcov/            # Coverage HTML reports
rm -rf .pytest_cache/      # Pytest cache
rm -rf __pycache__/        # Python bytecode (root)
rm -rf src/__pycache__/    # Python bytecode
rm -rf tests/__pycache__/  # Python bytecode
rm -f .coverage            # Coverage data file

# These will be regenerated when you run tests
```

---

## 5. Old Source Code Backups

```bash
# Old mapping files (replaced by s2s/translators/):
rm -rf src/mapping_old/    # Old YAML mapping files
```

---

## 6. Test Result Artifacts

```bash
# Old test outputs:
rm -rf test_results/       # Old test JSON results
```

---

## Quick Cleanup Script

Run this to clean up all safe-to-remove files:

```bash
#!/bin/bash
cd /home/shennilee/newproject2026/proj1/new-spice-translator

# Temporary files
rm -f bsim4v5.out results.json QUICK_REFERENCE.txt README_OLD.md

# Outdated root docs
rm -f CLEANUP_SUMMARY.md PROJECT_STATUS.md RESISTOR_TRANSLATION_FIXES.md
rm -f VERIFICATION_FRAMEWORK_SUMMARY.md MASTER_PLAN.md

# Old docs folder content
rm -f docs/oldPLAN.md docs/NEW2026*.md docs/CONSTRAINTS.md docs/QUICK_START.md

# Cache and coverage
rm -rf htmlcov/ .pytest_cache/ .coverage
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Old source backups
rm -rf src/mapping_old/ test_results/

echo "Cleanup complete!"
```

---

## Files to KEEP (Do NOT Remove)

### Essential Code:
- `cli.py` - Main CLI entry point
- `batch_translate.py` - Batch translation script
- `batch_translate_all.py` - Smart batch script
- `generate_verification_plots.py` - Plot generator
- `check_health.py` - Health check utility
- `demo.sh` - Demo script
- `src/` - All source code
- `verification/` - Verification framework
- `tests/` - Test suite

### Essential Config:
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project config
- `setup.py` - Package setup
- `.gitignore` - Git ignore rules
- `LICENSE` - License file

### Essential Docs:
- `README.md` - Main docs
- `ARCHITECTURE.md` - Design docs
- `GETTING_STARTED.md` - Quickstart
- `USAGE_GUIDE.md` - CLI reference
- `VALIDATION_RESULTS.md` - Results
- `VERIFICATION_FRAMEWORK.md` - Verification
- `CONTRIBUTING.md` - Contrib guide
- `docs/BATCHRUN1.md` - Batch results
- `docs/BATCHRUN2.md` - Latest results

### Essential Data:
- `output/` - Translation outputs (track with git)
- `tools/spice-libraries/` - PDK sources
- `ieee/` - Paper materials

---

## Post-Cleanup Directory Structure

After cleanup, your project should look like:

```
new-spice-translator/
├── .git/
├── .github/
├── .gitignore
├── .venv/
├── LICENSE
├── README.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── GETTING_STARTED.md
├── USAGE_GUIDE.md
├── VALIDATION_RESULTS.md
├── VERIFICATION_FRAMEWORK.md
├── cli.py
├── batch_translate.py
├── batch_translate_all.py
├── generate_verification_plots.py
├── check_health.py
├── demo.sh
├── requirements.txt
├── pyproject.toml
├── setup.py
├── docs/
│   ├── BATCHRUN1.md
│   └── BATCHRUN2.md
├── ieee/
│   └── paper/
├── output/
├── simulators/
├── src/
├── tests/
├── tools/
└── verification/
```

Total reduction: ~25 files/directories removed

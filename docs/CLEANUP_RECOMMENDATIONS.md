# Cleanup Recommendations

This document summarizes files that can be safely removed or archived after the full rerun captured in `finalbatchrun2/`.

## 1. Safe to Delete (Generated Artifacts)

These files are generated outputs and not source-of-truth documents.

- LaTeX build artifacts in `docs/`:
  - `*.aux`
  - `*.log`
  - `*.out`
- Generated PDFs in `docs/` if not required in-repo as release artifacts:
  - `PAPER.pdf`
  - `PAPER2.pdf`
  - `PAPER3.pdf`
  - `PAPER4.pdf`
- Temporary logs under `/tmp`:
  - `/tmp/finalbatchrun2/translate.log`
  - `/tmp/finalbatchrun2/verify.log`

## 2. Candidates to Archive (Historical Iteration Notes)

These are useful for internal traceability but can be moved to an archive folder to reduce top-level clutter.

- `docs/BATCHRUN1.md`
- `docs/BATCHRUN2.md`
- `docs/BATCHRUN3.md`
- `docs/BATCHRUN4.md`
- `docs/BATCHRUN5.md`
- `docs/BATCHRUN5_ANALYSIS.md`
- `docs/BATCHRUN_IMPROVE_1.md` through `docs/BATCHRUN_IMPROVE_8.md`
- `docs/BATCHRUN_IMPROVEMENT.md`
- `docs/BATCHRUN_IMPROVEMENT_SUMMARY.md`
- `docs/FINALBATCHRUN1.md`

Recommended archive location:
- `docs/archive/`

## 3. Keep as Canonical Documentation

These should remain active and maintained:

- `README.md`
- `docs/USAGE_GUIDE.md`
- `docs/VERIFICATION_GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTRIBUTING.md`
- `finalbatchrun2/FINALBATCHRUN2.md`
- `finalbatchrun2/raw/*`
- `finalbatchrun2/reports/*`

## 4. Code Cleanup Guidance

No core execution script is recommended for immediate removal without dependency mapping and test coverage confirmation.

Conservative guidance:
- Keep `batch_translate_all.py`, `batch_verify.py`, `cli.py`, and `verification/` unchanged.
- Perform code-level deletion only after usage tracing and CI validation.

## 5. Optional Cleanup Commands

Delete generated LaTeX artifacts only:

```bash
find docs -type f \( -name '*.aux' -o -name '*.log' -o -name '*.out' \) -delete
```

Move historical run notes to archive:

```bash
mkdir -p docs/archive
mv docs/BATCHRUN*.md docs/archive/
mv docs/FINALBATCHRUN1.md docs/archive/
```


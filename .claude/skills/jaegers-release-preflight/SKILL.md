---
name: jaegers-release-preflight
description: Use when checking or freezing a House Edge CSV and reproducible code ZIP, Python dependencies, offline execution, or adaptation submission.
---

# jaegers-release-preflight

1. Inspect current HEAD, working tree and any already-frozen CSV+ZIP. No model modifications during preflight.
2. Run the existing entry command for `--split validation` and `test`, then organizer `check_submission.py` against both actual resulting CSVs. Validation gives public 60-point result; test checks shape/IDs only.
3. Verify `requirements.txt` at ZIP root includes exact tested NumPy + scikit-learn pins for current stack. Confirm supported Python 3.13 Linux wheels under organizer provisioning, no network inference.
4. Use `build_entry.py --source jaegers_entry --out ...` only after required files exist; inspect ZIP root `README.md`, `reproduce.json`, `predict.py`, model and params. Extract in a clean folder, run reproduction under as-close-to-official environment as available, measure <=2 CPUs/16 GiB/30 min.
5. Compare every normalized probability with candidate CSV (max abs diff <=1e-8); hash exact ZIP and CSV, check sizes, record exact executed commands. A successful local check does not mean the organizer received files.
6. Human authorizes uploading the exact bytes. Retain receipt; never replace a submission without rerunning all predicates.

# v1.00 No-Streamlit Verification

Date: 2026-02-22
Branch: `maintenance/v1.00-no-streamlit`
Baseline ref: `8ce5cae` (`v1.00`)

## Goal

Confirm that `v1.00` keeps only truth-principles and does not depend on Streamlit runtime artifacts.

## Scope

- Working tree only (no Git history rewrite)
- Runtime surfaces: backend + Tkinter
- Source-of-truth docs: `md_docs`

## Checks Performed

1. Branch bootstrap from tag:
   - Created branch `maintenance/v1.00-no-streamlit` from `v1.00`.
2. Streamlit mention audit:
   - `git grep -n -i "streamlit\\|ui_streamlit"` -> no matches.
   - `rg -n -i "streamlit|ui_streamlit" docs md_docs tests backend ui_tk requirements.txt pyproject.toml` -> no matches.
3. Filesystem artifact audit:
   - `ui_streamlit` existed as non-tracked cache-only folder (`__pycache__` + `.pyc`).
   - Removed `ui_streamlit` and leftover smoke logs (`streamlit_smoke_*.log`).
4. Truth-principles check:
   - No Streamlit references found in `md_docs`.
   - No platform-binding to Streamlit in current docs/code.
5. Regression checks:
   - `python -m pytest -q` -> PASS.
   - `python -c "import ui_tk.main"` -> PASS.
   - Backend smoke (`uvicorn backend.http.app:app`) -> FAIL in current environment:
     - `sqlite3.OperationalError: disk I/O error` during `init_db()`.

## Result

- Streamlit code mentions in tracked project files: `0`
- `ui_streamlit` tracked runtime package in `v1.00`: absent
- Residual local Streamlit artifacts: removed
- Tkinter path unaffected by cleanup
- Backend smoke issue appears environment/storage-related, not Streamlit-related

## Acceptance Mapping

1. Search Cleanliness: PASS
2. Filesystem Cleanliness: PASS
3. Runtime Integrity (Tkinter import): PASS
4. Regression (`pytest -q`): PASS
5. Truth docs technology neutrality: PASS
6. Backend startup smoke in this environment: FAIL (`disk I/O error`)


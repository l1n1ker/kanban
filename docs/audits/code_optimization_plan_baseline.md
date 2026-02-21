# Code Optimization Baseline (No Logic Change)

Date: 2026-02-21
Branch: `refactoring/alpha-hardening`

## Scope
- Backend services decomposition
- Repository normalization with field whitelists
- DB module split (package form)
- Test helper deduplication + UI import smoke
- Quality gate tooling (`ruff`, `mypy`, `radon`)

## Baseline (Before)
- `backend/services.py`: 604 lines
- `backend/repositories.py`: 319 lines
- `backend/db.py`: 317 lines
- `ui_tk/main.py`: 5298 lines
- `pytest -q --durations=10`: green

## Result (After)
### Services decomposition
- `backend/services/common.py`: 203 lines
- `backend/services/tasks_service.py`: 267 lines
- `backend/services/users_service.py`: 65 lines
- `backend/services/pockets_service.py`: 65 lines
- `backend/services/projects_service.py`: 49 lines
- `backend/services/statuses_service.py`: 55 lines
- `backend/services/facade.py`: 24 lines

### Repository normalization
- `backend/repositories/core.py`: 346 lines
- `backend/repositories/common.py`: centralized `build_update_sql`, `fetch_one`, `fetch_all`
- Update operations now enforce explicit per-repo field whitelists.

### DB split
- `backend/db/__init__.py` exposes `get_connection`, `init_db` (compat import path preserved).
- Internal modules: `connection.py`, `schema.py`, `seed.py`, `migrations.py`, `validators.py`.

### Tests
- Added shared helpers in `tests/helpers/`.
- Added `tests/test_ui_import_smoke.py`.

## Guardrails status
- No runtime business-logic changes introduced intentionally.
- API routes/payload semantics preserved.
- `pytest -q --durations=10`: green after refactor.

## Open optimization debt
- `ui_tk/main.py` remains oversized and should be decomposed functionally in follow-up iterations.
- Complexity thresholds (`<= 12`) require next pass with `radon` enforcement in CI.

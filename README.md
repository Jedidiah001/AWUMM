# AWUM

AWUM is a Python-first wrestling management simulation backend with route handlers,
domain models, persistence layers, and regression tests.

## Repository layout

- `backend/routes/`: Flask API route modules grouped by feature.
- `backend/models/`: domain models and business entities.
- `backend/persistence/`: database and save-state read/write logic.
- `backend/economy/`: contract and rival-promotion engines.
- `backend/test_regressions.py`: focused regression coverage for critical bugs.
- `backend/data/`: runtime JSON/database assets used by local development.

## Running regression tests

From repository root:

```bash
python -m unittest backend.test_regressions
```

For the finance enterprise regression slice:

```bash
PYTHONUTF8=1 python -m unittest backend.test_regressions backend.test_finance_enterprise backend.test_phase_expansion
```

On Windows PowerShell:

```powershell
$env:PYTHONUTF8='1'
python -m unittest backend.test_regressions backend.test_finance_enterprise backend.test_phase_expansion
```

## Finance enterprise docs

- `docs/AUDIT_REPORT.md`: current architecture, database, security, performance, and remediation findings.
- `docs/FINANCE_ENTERPRISE_GUIDE.md`: sponsorship, venue/tour, settlement, and reporting workflows.
- `docs/BOOKING_STORY_MEDIA_EXPANSION.md`: booking timeline, story engine, ratings, media, and business simulation APIs, jobs, persistence, and frontend testing.

## Developer notes

- Follow repository-level `AGENTS.md` instructions when present.
- Use `rg` for fast file discovery in this codebase.
- Keep changes scoped and documented in commits.

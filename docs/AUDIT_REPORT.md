# AWUM Codebase Audit Report

Date: 2026-05-02

## Executive Summary

AWUM is a Flask + SQLite wrestling management simulator with server-rendered Bootstrap templates. The codebase already has strong domain breadth, but finance behavior was concentrated inside `backend/routes/finance_routes.py`, with limited separation between HTTP routing, schema creation, calculations, and persistence. This pass adds a dedicated finance enterprise service/schema layer for sponsorships, venues, tours, finance transactions, settlements, reports, and dashboard integration while preserving the existing Finance page and routes.

## Architecture Findings

- Backend: Flask blueprints under `backend/routes`, domain logic under `backend/models`, persistence helpers under `backend/persistence`, and economy/services under `backend/economy` and `backend/services`.
- Frontend: server-rendered templates in `frontend/templates` with inline JavaScript and Bootstrap UI patterns.
- Database: SQLite is initialized imperatively from Python. Existing schema creation is broad and centralized in `backend/persistence/database.py`, with additional feature tables created by helper modules.
- Finance: legacy finance deals, merchandise, capital, and P&L logic were route-local. New enterprise finance logic is now isolated in `backend/services/finance_enterprise.py` and `backend/services/finance_enterprise_schema.py`.

## Static Analysis And Dependency Review

- `python -m py_compile` passes for the changed backend modules.
- `python -m pip check` reports no broken installed requirements.
- Full SonarQube/SAST tooling is not configured in this repository yet. A CI workflow skeleton has been added to run compile checks and tests.
- Active Python dependency footprint is small: Flask and Werkzeug from `requirements.txt`.

## Database Findings

- Existing `show_history` has a useful `(year, week)` index but finance reporting previously mixed derived report data and route calculations.
- New indexed tables include `finance_transactions`, `finance_accounts`, `finance_budgets`, `finance_settlements`, `finance_reports`, sponsorship tables, venue upgrades, tours, routing, event financials, and logistics.
- The existing `venues` table is extended with compatibility columns rather than replaced, avoiding destructive migration risk.
- High-value indexes added:
  - `finance_transactions(posting_date, status)`
  - `finance_transactions(source_module, source_id)`
  - `sponsorship_contracts(sponsor_id, status, deleted_at)`
  - `tour_events(tour_id, event_date, status)`
  - `venues(latitude, longitude)`

## Security Findings

- SQL operations added in this pass use parameterized queries.
- New route handlers return 400 for validation errors and 500 for unexpected failures.
- Existing app-level API authentication/RBAC/rate limiting is still not present and remains a security gap for production deployment.
- Existing inline JavaScript should be migrated to external modules with a CSP before internet-facing deployment.

## Performance Findings

- The new service uses aggregate SQL for dashboard metrics and targeted indexes for transaction/source lookups.
- Route optimization uses a nearest-neighbor heuristic over the events in one tour; this is appropriate for the current small tour-planning scale.
- Current repository lacks automated query benchmark tooling. Recommended next step is a repeatable SQLite benchmark script with seeded 10k+ finance transactions.

## Test Coverage Findings

- Existing regression tests cover contracts, defense frequency, championship persistence, and incentive loading.
- Added `backend/test_finance_enterprise.py` covering:
  - Sponsorship payment posting to finance transactions.
  - Deliverable compliance tracking.
  - Controversy satisfaction/threat impact.
  - Venue upgrade capital expenditure posting.
  - Tour event settlement transaction consistency.
- Repository does not yet have coverage thresholds, browser automation, or load tests.

## Remediation Plan

1. Move remaining large route-local finance helpers into service modules.
2. Add auth/RBAC and permission checks for all finance mutation endpoints.
3. Add Alembic-style or custom versioned SQLite migrations instead of opportunistic table creation during requests.
4. Split `frontend/templates/finance.html` into smaller included partials and external JavaScript modules.
5. Add coverage tooling and thresholds once the environment standardizes on one Python version.
6. Add Playwright smoke tests for the Finance page tabs and settlement flow.
7. Add performance benchmarks for dashboard load, transaction reports, and large tour datasets.

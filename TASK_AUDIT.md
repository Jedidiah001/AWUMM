# Codebase task proposals

This audit proposes one concrete task in each requested category.

## 1) Typo fix task

**Task:** Rename `backend/models/rival_promotion_managerr.py` to `rival_promotion_manager.py` (single trailing `r`) and remove or update any references.

**Why:** The filename includes a clear typo (`managerr`) that makes search/discovery harder and risks accidental imports from the wrong path.

**Acceptance criteria:**
- File name is corrected.
- No imports reference the typo path.
- `rg -n "rival_promotion_managerr" backend` returns no hits.

## 2) Bug fix task

**Task:** Remove duplicate rival-promotion manager implementations by consolidating logic into one canonical module (currently duplicated in `backend/economy/rival_promotion_manager.py` and `backend/models/rival_promotion_managerr.py`).

**Why:** Duplicated business logic can drift and create inconsistent behavior depending on which module gets imported.

**Acceptance criteria:**
- Exactly one implementation file remains.
- App imports and tests resolve to the canonical module.
- A regression test fails if a second duplicate implementation is reintroduced.

## 3) Comment/documentation discrepancy task

**Task:** Update `README.md` to accurately describe the present repository layout and major runtime components.

**Why:** The README currently says the repo contains frontend templates/static assets, but the tracked project structure is overwhelmingly backend Python services/routes/models; this can mislead contributors.

**Acceptance criteria:**
- README includes an explicit top-level structure section (e.g., `backend/`, `data/`, tests).
- README startup instructions mention the actual backend entrypoint(s).
- Wording about frontend/templates is either clarified with exact paths or removed.

## 4) Test improvement task

**Task:** Strengthen `backend/test_regressions.py` by parameterizing contract-alert edge cases and asserting exact expected alert IDs/counts.

**Why:** Current assertions use broad `any` / `all` checks, which can pass even when extra incorrect alerts are generated.

**Acceptance criteria:**
- Add table-driven cases for `weeks_remaining` values (`None`, negative, boundary values).
- Assert exact alert set equality and expected counts.
- Test names explicitly describe each scenario.

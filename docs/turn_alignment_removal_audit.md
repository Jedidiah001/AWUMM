# Wrestler Turn And Alignment Removal Audit

Date: 2026-05-04

## Removed From Active Runtime

- Deleted the dedicated wrestler turn model module: `backend/models/alignment.py`.
- Deleted the dedicated wrestler turn booking simulator: `backend/simulation/turn_booking.py`.
- Stopped database startup from creating the deprecated `wrestler_turns` and `turn_segments` tables.
- Added startup cleanup that drops `wrestler_turns` and `turn_segments` from existing SQLite databases.
- Removed roster API filtering and roster-summary grouping by alignment.
- Removed the visible Create-A-Wrestler alignment selector from the frontend.
- Removed CAW validation that required Face, Heel, or Tweener.
- Removed alignment-themed CAW preset names and preset payload metadata.

## Compatibility Still Present

The legacy `wrestlers.alignment` persistence column and `Wrestler.alignment` constructor argument remain as compatibility shims for existing save files and older importer paths. New CAW records write `Neutral` and the field is no longer exposed as an active gameplay choice through the CAW or roster APIs.

The remaining compatibility field should be removed in a second migration pass once every importer, seed file, free-agent generator, and simulation heuristic has been moved to non-alignment inputs such as role, popularity, momentum, division, brand, and storyline context.

## New Replacement Direction

The gameplay replacement is the ROC Vanguard developmental pipeline:

- `brand_metadata`
- `wrestler_evaluations`
- `call_up_decisions`
- `trial_appearances`
- `call_ups`
- `failed_call_ups`
- `general_managers`
- `gm_evaluations`
- `gm_promotions`

These tables support readiness scoring, trial appearances, official call-ups, comeback tracking, and GM promotion paths without relying on face/heel alignment.

# Simulation Expansion Guide

This guide covers the enterprise simulation layer for features #149-160,
#171-182, and #243-250.

## Frontend

- Page: `/simulation-expansion`
- Template: `frontend/templates/simulation_expansion.html`
- Navigation label: `Enterprise Sim`

The page reads from persisted API data only. The buttons call backend jobs and
then reload the dashboard from SQLite.

## API

All endpoints return:

```json
{ "success": true, "data": {} }
```

Errors return:

```json
{ "success": false, "error": { "message": "..." } }
```

### Aggregate

- `GET /api/simulation-expansion/dashboard`
  Returns locker room, developmental, and advanced simulation dashboard data.

- `POST /api/simulation-expansion/weekly`
  Body: `{ "year": 1, "week": 3, "seed": 123 }`
  Runs locker room culture, developmental progression, industry evolution, and
  endgame progress jobs.

### Locker Room

- `GET /api/locker-room/enterprise`
  Optional query: `brand=ROC Alpha`

- `POST /api/locker-room/weekly`
  Runs the weekly morale, ego, professionalism, influence, clique, atmosphere,
  disagreement, bullying, substance-risk, and shoot-incident calculations.

- `GET /api/locker-room/wrestlers/<wrestler_id>`
  Returns state, morale trend, disagreements, discipline, and confidential
  substance-management summaries.

- `POST /api/locker-room/meetings`
  Body fields: `meeting_type`, `purpose`, optional `target_brand`,
  `attendee_ids`, `wrestler_id`, `communication_skill`, `credibility`.

- `POST /api/locker-room/discipline`
  Body fields: `wrestler_id`, `violation_type`, `action_type`,
  `justification`, optional severity/fine/suspension fields.

- `POST /api/locker-room/creative-disagreements/<id>/resolve`
  Body: `{ "resolution_choice": "negotiation" }`
  Choices: `accommodation`, `negotiation`, `assertion`,
  `compromise_timeline`.

### Performance Center

- `GET /api/performance-center/dashboard`
- `POST /api/performance-center/weekly`
- `POST /api/performance-center/trainers`
- `POST /api/performance-center/curricula`
- `POST /api/performance-center/trainees`
- `POST /api/performance-center/tryouts`
- `GET /api/performance-center/tryouts/<tryout_id>`
- `POST /api/performance-center/candidates/<candidate_id>/sign`
- `POST /api/performance-center/callups`
- `POST /api/performance-center/senddowns`
- `POST /api/performance-center/excursions`
- `POST /api/performance-center/veteran-trainers`

Curriculum allocation must total exactly `100` across:

- `in_ring_fundamentals`
- `athletic_conditioning`
- `character_promo`
- `match_psychology`
- `move_set`
- `tag_faction`
- `sports_entertainment`

### Advanced Simulation

- `GET /api/advanced-simulation/dashboard`
- `POST /api/advanced-simulation/match-scripts`
- `POST /api/advanced-simulation/match-scripts/<script_id>/evaluate`
- `POST /api/advanced-simulation/production`
- `POST /api/advanced-simulation/attendance`
- `POST /api/advanced-simulation/aging/run`
- `POST /api/advanced-simulation/industry/run`
- `POST /api/advanced-simulation/brands/assign`
- `POST /api/advanced-simulation/endgame/update`

## Background Jobs

Jobs are idempotent per `job_type/year/week` and are recorded in
`simulation_expansion_jobs`.

- `weekly_locker_room_culture`
  Reads wrestlers, match history, championships, locker state.
  Writes wrestler culture state, morale history, influence history,
  cliques, atmosphere, and risk incidents.

- `weekly_developmental_pipeline`
  Reads performance center, trainers, curricula, trainees, excursions.
  Writes trainee progression snapshots, readiness updates, and training
  injuries.

- `annual_aging_effects`
  Reads wrestlers and injury history.
  Writes physical/intangible aging snapshots.

Industry trend and endgame updates are persisted immediately by their endpoint
calls.

## Key Tables

Locker room:

- `locker_wrestler_state`
- `locker_morale_history`
- `locker_atmosphere_snapshots`
- `locker_creative_disagreements`
- `locker_cliques`
- `locker_clique_members`
- `locker_bullying_incidents`
- `locker_substance_issues`
- `locker_meetings`
- `locker_meeting_attendees`
- `locker_disciplinary_actions`
- `locker_shoot_incidents`

Developmental:

- `dev_performance_centers`
- `dev_trainers`
- `dev_curricula`
- `dev_trainees`
- `dev_progress_snapshots`
- `dev_tryouts`
- `dev_tryout_candidates`
- `dev_shows`
- `dev_show_performances`
- `dev_callups`
- `dev_senddowns`
- `dev_training_injuries`
- `dev_excursion_destinations`
- `dev_excursions`
- `dev_veteran_trainer_transitions`

Advanced simulation:

- `advanced_match_scripts`
- `advanced_match_script_beats`
- `production_profiles`
- `commentary_teams`
- `production_quality_history`
- `dynasty_events`
- `second_generation_prospects`
- `aging_snapshots`
- `industry_eras`
- `industry_trend_snapshots`
- `attendance_markets`
- `attendance_records`
- `brand_entities`
- `brand_assignment_history`
- `brand_drafts`
- `endgame_objectives`
- `endgame_recognition_events`

## Frontend Testing

1. Open `/simulation-expansion`.
2. Confirm all three tabs render without client-side errors.
3. Click `Run Weekly Systems`.
4. Refresh the browser and confirm the dashboard values persist.
5. Stop and restart the server, reopen `/simulation-expansion`, and confirm the
   same snapshots and records remain.
6. Open the Locker Room tab and click a wrestler row. The alert should show
   persisted morale factors.
7. Create a meeting through `POST /api/locker-room/meetings`; reload and verify
   morale changes are visible.
8. Create a trainer, curriculum, and trainee through the Performance Center API;
   run the weekly pipeline and confirm `dev_progress_snapshots` has a row.
9. Create and evaluate a match script; confirm `execution_score` and
   `match_quality_modifier` are stored after refresh.
10. Project attendance with `simulate_actual=true`; confirm projected and actual
    attendance survive restart.

## Verification

Targeted tests:

```bash
python -m unittest backend.test_simulation_expansion
```

The tests use isolated SQLite files, deterministic seeds, and restart checks.

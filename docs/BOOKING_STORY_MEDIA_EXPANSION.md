# Booking, Story, Media, and Business Expansion

This document covers features 64-72, 88-100, and 126-137 implemented by the phase expansion layer.

## Architecture

- Migration: `backend/persistence/phase_expansion_db.py`
- Repository: `backend/repositories/phase_expansion_repository.py`
- Service: `backend/services/booking_story_media_service.py`
- Routes: `backend/routes/phase_expansion_routes.py`
- Frontend entry points: `frontend/templates/booking.html`, `frontend/templates/feuds.html`, `frontend/templates/media_business.html`

All phase data is stored in SQLite. Database initialization applies the migration once through `schema_migrations`; `drop_phase_expansion_tables(database)` provides the down path for rollback tooling.

Controllers return a consistent envelope:

```json
{"success": true, "data": {}}
```

Validation and runtime errors return:

```json
{"success": false, "error": "message"}
```

The local Flask app currently has no authentication or API rate limiting layer. These endpoints inherit that behavior.

## API Endpoints

### Configuration

| Method | Endpoint | Purpose | Required parameters |
| --- | --- | --- | --- |
| GET | `/api/phase-expansion/config` | Lookup values, duration ranges, theme templates, network and social defaults | none |

### Booking Enhancements

| Method | Endpoint | Purpose | Required parameters |
| --- | --- | --- | --- |
| POST | `/api/booking-enhancements/show-plan` | Build and persist a full show timeline atomically | `show_draft.show_id`; optional `production_plan.total_runtime_minutes`, `commercial_breaks`, `accept_overrun` |
| GET | `/api/booking-enhancements/show-plan/<show_id>` | Retrieve persisted timeline, segments, and breaks | `show_id` path |
| POST | `/api/booking-enhancements/interference/project` | Preview interference impact and overuse warnings | `interfering_wrestler_id`, `show_id`, `match_id`, `purpose`; calendar defaults fill `year`, `week` |
| POST | `/api/booking-enhancements/interference` | Persist planned interference and apply feud heat changes | same as projection |
| POST | `/api/booking-enhancements/debut/vignette` | Persist a teased-debut vignette and anticipation delta | `wrestler_id`, calendar week |
| POST | `/api/booking-enhancements/debut` | Persist surprise or teased debut outcome | `wrestler_id`, `method`, calendar week |
| POST | `/api/booking-enhancements/return/anticipation` | Persist an announced-return build segment | `wrestler_id`, calendar week |
| POST | `/api/booking-enhancements/return` | Persist cold or announced return outcome | `wrestler_id`, `return_type`, `context`, calendar week |
| POST | `/api/booking-enhancements/commercial-break/project` | Calculate a commercial break quality score | `show_id`, `position_index`, `placement_type`, `strategy` |
| GET | `/api/booking-enhancements/themes` | List reusable show theme templates | none |
| POST | `/api/booking-enhancements/themes` | Create a reusable theme template | `name`, `theme_type` |
| POST | `/api/booking-enhancements/themes/apply` | Apply a theme to a show and calculate execution score | `show_id`, `theme_template_id` |

Example show-plan request:

```json
{
  "accept_overrun": true,
  "production_plan": {"total_runtime_minutes": 120},
  "show_draft": {
    "show_id": "show_001",
    "show_name": "ROC Alpha",
    "brand": "ROC Alpha",
    "show_type": "weekly_tv",
    "matches": [
      {"match_id": "m1", "match_type": "singles", "planned_duration_minutes": 12}
    ],
    "segments": [
      {"segment_id": "s1", "segment_type": "promo", "duration_minutes": 6}
    ]
  }
}
```

### Story Engine

| Method | Endpoint | Purpose | Required parameters |
| --- | --- | --- | --- |
| GET | `/api/story-engine/dashboard` | Active feud heat, trajectory, business metrics, recent actions | none |
| GET | `/api/story-engine/feuds` | List story-engine feuds | optional `active_only=false` |
| POST | `/api/story-engine/feuds` | Create a many-participant feud | `participants[]`, `basis`; optional conclusion and duration |
| POST | `/api/story-engine/feuds/<feud_id>/actions` | Record heat-building action and update heat | `action_type` |
| POST | `/api/story-engine/payoffs` | Persist feud/program payoff assessment | `feud_id`, `match_id` |
| POST | `/api/story-engine/swerves` | Persist twist/swerve result and credibility effect | `swerve_type`, `participants` |
| POST | `/api/story-engine/promos` | Persist scripted promo result and connected heat effect | `speaking_wrestler_id`, `tone`, `duration_minutes` |
| POST | `/api/story-engine/backstage-segments` | Persist backstage segment quality and location logic | `segment_type`, `location` |
| POST | `/api/story-engine/arcs` | Create long-term arc with chapters | `premise`, `planned_duration_weeks`, `chapters[]` |
| POST | `/api/story-engine/short-programs` | Create two-to-four-week program | `participants[]`, `planned_winner_id` |
| POST | `/api/story-engine/authority-figures` | Create on-screen authority character | `name`, `role` |
| POST | `/api/story-engine/authority-storylines` | Start authority power-angle storyline | `authority_figure_id`, `angle_type` |
| POST | `/api/story-engine/tournaments` | Create tournament, seed entries, generate opening matches | `name`, `prize_type`, `participants[]` |
| POST | `/api/story-engine/romantic-angles` | Create romantic angle and reception risk | `participants[]`, `relationship_type` |
| POST | `/api/story-engine/legacy-relationships` | Persist family/trainer/chosen-family relationship | `wrestler_id`, `related_wrestler_id`, `relationship_type` |
| POST | `/api/story-engine/torch-passes` | Persist torch-passing result and popularity transfer | `legend_id`, `rising_star_id` |

Example feud request:

```json
{
  "name": "Champion vs Challenger",
  "basis": "championship_dispute",
  "initial_heat": 55,
  "duration_target_weeks": 8,
  "participants": [
    {"participant_id": "w1", "participant_name": "Champion"},
    {"participant_id": "w2", "participant_name": "Challenger"}
  ]
}
```

### Media and Business

| Method | Endpoint | Purpose | Required parameters |
| --- | --- | --- | --- |
| GET | `/api/media-business/dashboard` | Ratings, network, social, and business snapshot dashboard | none |
| GET | `/api/media-business/ratings` | Recent TV ratings | optional `limit` |
| GET | `/api/media-business/ratings/<show_id>` | Full rating bundle with quarter-hours and demographics | `show_id` path |
| POST | `/api/media-business/jobs/weekly` | Run internal weekly jobs for game calendar week | optional `year`, `week` |
| POST | `/api/media-business/content` | Produce digital content and update social metrics | `title`, `content_type` |
| POST | `/api/media-business/media-appearances` | Record external media appearance and awareness effect | `wrestler_id`, `appearance_type` |
| POST | `/api/media-business/streaming-deals` | Create streaming deal and revenue model | `platform_type`, `revenue_model` |
| POST | `/api/media-business/documentaries` | Create documentary project and reception | `title`, `documentary_type` |
| POST | `/api/media-business/video-game-licenses` | Create video game license deal | `game_type`, `revenue_model` |
| POST | `/api/media-business/press-conferences` | Stage press conference and press coverage effect | `conference_type`, `announcement` |
| POST | `/api/media-business/controversies/respond` | Record response to wrestler controversy | `controversy_id` or controversy fields, `response` |

Example content request:

```json
{
  "title": "Road to the Title",
  "content_type": "highlight_reel",
  "associated_feud_id": "story_feud_abc",
  "quality_score": 72
}
```

## Background Jobs

`weekly_internal_simulation` is run from `/api/media-business/jobs/weekly` and automatically during show simulation. It uses in-game year/week only; real elapsed time is ignored.

| Calculation | Reads | Writes | Failure behavior |
| --- | --- | --- | --- |
| Heat decay | `story_feuds`, `storyline_actions` | `story_feuds` | The route returns a structured error and no completion job is logged if an exception escapes. |
| Organic social growth | `social_platform_metrics` | `social_metric_history`, `social_spike_events`, `social_platform_metrics` | Same transaction-safe route behavior. |
| Network ratings trend | `tv_ratings`, `network_relationships` | `network_relationships`, `network_relationship_history` | No trend is applied until enough ratings exist. |
| Business snapshot | `tv_ratings`, `social_platform_metrics`, `network_relationships`, content library | `business_metric_snapshots` | Snapshot is upserted by year/week. |

The job is idempotent per year/week. A completed job returns the stored previous result instead of applying decay or growth twice.

## Database Tables

Every table has `created_at`, `updated_at`, and nullable `deleted_at` where row lifecycle applies. Frequently queried foreign keys, show IDs, wrestler IDs, year/week fields, and status fields are indexed in the migration.

| Table | Purpose | Key relationships and columns |
| --- | --- | --- |
| `schema_migrations` | Tracks applied phase migration | `id`, `applied_at` |
| `phase_lookup_values` | Seeded enums and UI options | `category`, `value`, `label`, `metadata` |
| `booking_show_plans` | One persisted production plan per show | `show_id`, runtime, breaks, warnings, rating/credibility deltas |
| `booking_segments` | Match, promo, backstage, dark-match timeline rows | `show_id`, `source_item_id`, planned/actual minutes, status, opening/main flags, feud/title links |
| `commercial_breaks` | Break placement and viewer-return math | `show_id`, `after_segment_id`, `during_match_id`, quality and satisfaction modifiers |
| `interference_history` | Planned run-ins and overuse consequences | interfering wrestler, `match_id`, optional `feud_id`, impact and heat deltas |
| `debut_vignettes`, `debut_records` | Teased/surprise debut build and final outcome | wrestler, calendar week, anticipation, pop, momentum |
| `return_anticipation_segments`, `return_records` | Announced/cold return build and payoff | wrestler, return context, surprise/anticipation/pop metrics |
| `opening_segment_assessments`, `main_event_assessments` | High-impact show-position records | `show_id`, segment id, planned/actual scores, ratings/network effects |
| `dark_match_history`, `market_satisfaction_history`, `wrestler_development_progress` | Untelvised match satisfaction and talent development | wrestler/market/show links, experience and satisfaction deltas |
| `show_theme_templates`, `show_theme_applications` | Reusable and applied show themes | template requirements, show execution score, viewership/media modifiers |
| `story_feuds`, `story_feud_participants`, `storyline_actions` | Feud entity, participants, and full action history | heat, trajectory, fatigue, basis, action heat deltas |
| `story_arcs`, `story_arc_chapters`, `short_programs` | Long and short narrative program tracking | planned duration, chapter completion, payoff status |
| `storyline_payoffs`, `story_swerves` | Climax and twist assessment records | match/feud links, payoff score, unpredictability, narrative logic |
| `promo_segments`, `backstage_segments` | Scripted and behind-the-scenes content results | wrestler IDs, tone/location, quality, connected feud |
| `authority_figures`, `authority_storylines` | On-screen power characters and angles | role permissions, credibility, angle heat |
| `tournaments`, `tournament_entries`, `tournament_matches` | Bracket state and automatic advancement | tournament ID, seed, round, winner, upset/social score |
| `romantic_angles`, `legacy_relationships`, `torch_passes`, `historical_callbacks` | Romance, family, trainer, legacy, and callback history | wrestler relationships, reception risk, legacy transfer |
| `tv_ratings`, `tv_quarter_hour_ratings`, `tv_demographic_ratings`, `ratings_insights` | Show ratings, quarter-hours, demos, analytics | `show_id`, `rating_id`, ad revenue, viewer deltas |
| `network_relationships`, `network_relationship_history`, `network_contracts`, `network_demands` | Broadcaster relationship and contract pressure | score, demands, rights fees, reasons for changes |
| `competing_events`, `competing_impact_history` | External TV/sports competition and rating impact | event calendar, overlap, lost-viewer estimate |
| `social_platform_metrics`, `social_metric_history`, `social_spike_events` | Platform followers, engagement, and viral spikes | platform, follower deltas, source show/story |
| `wrestler_social_controversies` | Controversy event and response history | wrestler, type, severity, response, reputation/brand/network effects |
| `streaming_deals`, `digital_content_library`, `media_appearances`, `documentary_projects`, `video_game_licenses`, `press_conferences` | Media, licensing, and distribution business records | deal terms, content library, reach, awareness, revenue |
| `business_metric_snapshots` | Weekly combined business state | awareness, sponsor appeal, streaming appeal, credibility, valuation |
| `internal_simulation_jobs` | Auditable in-game scheduled job runs | job type, trigger week, reads/writes, result or error |

Example persisted segment:

```json
{
  "show_id": "show_001",
  "source_item_id": "m1",
  "item_type": "match",
  "planned_duration_minutes": 12,
  "actual_duration_minutes": 14,
  "allocation_status": "within_budget",
  "is_opening": 1,
  "is_main_event": 0
}
```

## Cross-System Data Flow

- Show simulation calls `BookingStoryMediaService.process_show_result`.
- Show plans persist planned and actual segment durations.
- Opening and main event assessments feed TV rating modifiers.
- Match quality and connected feuds update `story_feuds` and `storyline_actions`.
- Ratings persist complete show, quarter-hour, demographic, and insight rows.
- Ratings update network relationship history.
- Debuts, swerves, hot feud actions, content, press events, and controversies create social/media/business events.
- Weekly jobs apply only when the game calendar advances.

## Frontend Testing Guide

1. Start the Flask app and open `/booking`.
2. Add matches or segments, then inspect the Time Slot Allocation panel.
3. Change segment minutes. The remaining-time badge and segment color should update immediately.
4. Click Save Timeline. Stop and restart the server, reload the same show plan through `/api/booking-enhancements/show-plan/<show_id>`, and verify planned minutes remain unchanged.
5. Open `/feuds`. The Story Engine Heat Dashboard should show story-engine feuds, heat labels, trajectory, and booking credibility.
6. Use `/api/story-engine/feuds` to create a feud, then `/api/story-engine/feuds/<feud_id>/actions` to advance it. Refresh the page and confirm heat persists.
7. Simulate a show through the existing booking flow. Confirm the response includes `media_business`, then open `/media-business`.
8. Verify ratings, network relationship, social platform counts, and business metrics appear from the database.
9. Produce digital content and stage a press conference from `/media-business`; refresh and confirm social/business metrics update.
10. Restart the server again. `/media-business` and `/api/media-business/ratings` should still show the same persisted records.

Common mistakes to check:

- A show plan saved with overrun but no `accept_overrun=true` should return HTTP 400.
- Re-running weekly jobs for the same year/week should return `already_ran` and must not apply decay twice.
- Interference by the same wrestler more than twice in four weeks should show overuse warning and credibility penalty.
- Payoff or personal escalation actions should fail validation when the feud heat is too low.

## Regression Tests

Run the phase expansion tests from repository root:

```powershell
python -m unittest backend.test_phase_expansion
```

Run the broader current regression set:

```powershell
python -m unittest backend.test_phase_expansion backend.test_regressions backend.test_finance_enterprise
```

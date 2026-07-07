"""
Persistent schema for booking, storyline, media, ratings, and business systems.

The project does not use an external migration runner, so this module provides a
small idempotent migration with explicit up/down SQL. Startup applies the up
migration through ``create_phase_expansion_tables``.
"""

from __future__ import annotations

from datetime import datetime
import json
import sqlite3


MIGRATION_ID = "20260506_064_137_booking_story_media"


UP_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phase_lookup_values (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    value TEXT NOT NULL,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_phase_lookup_category_value
    ON phase_lookup_values(category, value);

CREATE TABLE IF NOT EXISTS booking_show_plans (
    show_id TEXT PRIMARY KEY,
    show_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    show_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    total_runtime_minutes INTEGER NOT NULL,
    network_break_count INTEGER NOT NULL DEFAULT 0,
    accept_overrun INTEGER NOT NULL DEFAULT 0,
    booking_credibility_delta REAL NOT NULL DEFAULT 0,
    planned_rating_impact REAL NOT NULL DEFAULT 0,
    actual_runtime_minutes INTEGER,
    dead_air_risk_minutes INTEGER NOT NULL DEFAULT 0,
    overrun_minutes INTEGER NOT NULL DEFAULT 0,
    warnings TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS booking_segments (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    segment_type TEXT NOT NULL,
    card_position INTEGER NOT NULL,
    planned_start_minute INTEGER NOT NULL DEFAULT 0,
    planned_duration_minutes INTEGER NOT NULL,
    actual_duration_minutes INTEGER,
    allocation_status TEXT NOT NULL,
    expected_min_minutes INTEGER NOT NULL DEFAULT 1,
    expected_max_minutes INTEGER NOT NULL DEFAULT 10,
    suspiciously_short INTEGER NOT NULL DEFAULT 0,
    overrun_minutes INTEGER NOT NULL DEFAULT 0,
    dead_air_minutes INTEGER NOT NULL DEFAULT 0,
    is_opening INTEGER NOT NULL DEFAULT 0,
    is_main_event INTEGER NOT NULL DEFAULT 0,
    is_dark_match INTEGER NOT NULL DEFAULT 0,
    dark_match_phase TEXT,
    feud_id TEXT,
    title_id TEXT,
    quality_score REAL NOT NULL DEFAULT 0,
    crowd_heat_score REAL NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (show_id) REFERENCES booking_show_plans(show_id)
);
CREATE INDEX IF NOT EXISTS idx_booking_segments_show
    ON booking_segments(show_id, card_position);
CREATE INDEX IF NOT EXISTS idx_booking_segments_feud
    ON booking_segments(feud_id);

CREATE TABLE IF NOT EXISTS commercial_breaks (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    position_index INTEGER NOT NULL,
    placement_type TEXT NOT NULL,
    after_segment_id TEXT,
    during_match_id TEXT,
    minute_marker INTEGER NOT NULL,
    strategy TEXT NOT NULL,
    quality_score REAL NOT NULL,
    viewer_return_modifier REAL NOT NULL,
    satisfaction_modifier REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (show_id) REFERENCES booking_show_plans(show_id)
);
CREATE INDEX IF NOT EXISTS idx_commercial_breaks_show
    ON commercial_breaks(show_id, position_index);

CREATE TABLE IF NOT EXISTS interference_history (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    feud_id TEXT,
    interfering_wrestler_id TEXT NOT NULL,
    interfering_wrestler_name TEXT NOT NULL,
    purpose TEXT NOT NULL,
    outcome TEXT NOT NULL,
    impact_score REAL NOT NULL,
    heat_delta REAL NOT NULL DEFAULT 0,
    recent_count_4_weeks INTEGER NOT NULL DEFAULT 0,
    feud_interference_count INTEGER NOT NULL DEFAULT 0,
    overuse_warning INTEGER NOT NULL DEFAULT 0,
    override_warning INTEGER NOT NULL DEFAULT 0,
    credibility_penalty REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_interference_wrestler_week
    ON interference_history(interfering_wrestler_id, year, week);
CREATE INDEX IF NOT EXISTS idx_interference_feud
    ON interference_history(feud_id);

CREATE TABLE IF NOT EXISTS debut_vignettes (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    show_id TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    quality_score REAL NOT NULL,
    anticipation_delta REAL NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_debut_vignettes_wrestler
    ON debut_vignettes(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS debut_records (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    show_id TEXT NOT NULL,
    method TEXT NOT NULL,
    weeks_hidden INTEGER NOT NULL DEFAULT 0,
    vignette_count INTEGER NOT NULL DEFAULT 0,
    anticipation_score REAL NOT NULL,
    debut_pop_rating REAL NOT NULL,
    post_debut_momentum REAL NOT NULL,
    performance_score REAL NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_debut_records_wrestler
    ON debut_records(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS return_anticipation_segments (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    show_id TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    quality_score REAL NOT NULL,
    anticipation_delta REAL NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_return_anticipation_wrestler
    ON return_anticipation_segments(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS return_records (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    show_id TEXT NOT NULL,
    return_type TEXT NOT NULL,
    context_type TEXT NOT NULL,
    absence_weeks INTEGER NOT NULL,
    anticipation_score REAL NOT NULL,
    return_pop_rating REAL NOT NULL,
    credibility_penalty REAL NOT NULL DEFAULT 0,
    momentum_delta REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_return_records_wrestler
    ON return_records(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS opening_segment_assessments (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    planned_quality_score REAL NOT NULL,
    actual_performance_score REAL,
    ratings_impact REAL NOT NULL DEFAULT 0,
    viewer_retention_effect REAL NOT NULL DEFAULT 0,
    inputs_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_opening_assessment_show
    ON opening_segment_assessments(show_id);

CREATE TABLE IF NOT EXISTS main_event_assessments (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    expected_quality_score REAL NOT NULL,
    actual_quality_score REAL,
    overall_rating_effect REAL NOT NULL DEFAULT 0,
    network_effect REAL NOT NULL DEFAULT 0,
    social_reaction_score REAL NOT NULL DEFAULT 0,
    failure_recorded INTEGER NOT NULL DEFAULT 0,
    inputs_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_main_event_assessment_show
    ON main_event_assessments(show_id);

CREATE TABLE IF NOT EXISTS dark_match_history (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    match_id TEXT,
    participants_json TEXT NOT NULL DEFAULT '[]',
    planned_duration_minutes INTEGER NOT NULL,
    actual_duration_minutes INTEGER,
    crowd_warmth_delta REAL NOT NULL DEFAULT 0,
    live_satisfaction_delta REAL NOT NULL DEFAULT 0,
    development_xp REAL NOT NULL DEFAULT 0,
    market_key TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_dark_matches_show
    ON dark_match_history(show_id, phase);

CREATE TABLE IF NOT EXISTS market_satisfaction_history (
    id TEXT PRIMARY KEY,
    market_key TEXT NOT NULL,
    show_id TEXT,
    satisfaction_score REAL NOT NULL,
    ticket_sales_modifier REAL NOT NULL DEFAULT 0,
    reason TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_market_satisfaction_market
    ON market_satisfaction_history(market_key, year, week);

CREATE TABLE IF NOT EXISTS wrestler_development_progress (
    wrestler_id TEXT PRIMARY KEY,
    wrestler_name TEXT NOT NULL,
    dark_match_count INTEGER NOT NULL DEFAULT 0,
    development_xp REAL NOT NULL DEFAULT 0,
    development_rating REAL NOT NULL DEFAULT 50,
    last_dark_match_show_id TEXT,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS show_theme_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    requirements_json TEXT NOT NULL DEFAULT '{}',
    marketing_bonus REAL NOT NULL DEFAULT 0,
    ratings_bonus REAL NOT NULL DEFAULT 0,
    press_bonus REAL NOT NULL DEFAULT 0,
    created_by_user INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_show_theme_templates_category
    ON show_theme_templates(category);

CREATE TABLE IF NOT EXISTS show_theme_applications (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    theme_id TEXT NOT NULL,
    execution_score REAL NOT NULL DEFAULT 0,
    honored_requirements INTEGER NOT NULL DEFAULT 0,
    viewership_effect REAL NOT NULL DEFAULT 0,
    social_effect REAL NOT NULL DEFAULT 0,
    press_effect REAL NOT NULL DEFAULT 0,
    assessment_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (theme_id) REFERENCES show_theme_templates(id)
);
CREATE INDEX IF NOT EXISTS idx_show_theme_applications_show
    ON show_theme_applications(show_id);

CREATE TABLE IF NOT EXISTS story_feuds (
    id TEXT PRIMARY KEY,
    legacy_feud_id TEXT,
    name TEXT NOT NULL,
    basis TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    heat_score REAL NOT NULL DEFAULT 20,
    heat_level TEXT NOT NULL DEFAULT 'lukewarm',
    trajectory TEXT NOT NULL DEFAULT 'stable',
    intended_conclusion_match_type TEXT NOT NULL,
    duration_target_weeks INTEGER NOT NULL,
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    planned_climax_year INTEGER,
    planned_climax_week INTEGER,
    last_action_year INTEGER,
    last_action_week INTEGER,
    weeks_at_nuclear INTEGER NOT NULL DEFAULT 0,
    fatigue_penalty REAL NOT NULL DEFAULT 0,
    payoff_score REAL,
    booking_credibility_delta REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_story_feuds_status_heat
    ON story_feuds(status, heat_score);
CREATE INDEX IF NOT EXISTS idx_story_feuds_legacy
    ON story_feuds(legacy_feud_id);

CREATE TABLE IF NOT EXISTS story_feud_participants (
    id TEXT PRIMARY KEY,
    feud_id TEXT NOT NULL,
    participant_type TEXT NOT NULL,
    participant_id TEXT NOT NULL,
    participant_name TEXT NOT NULL,
    side_label TEXT NOT NULL DEFAULT 'A',
    role TEXT NOT NULL DEFAULT 'primary',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (feud_id) REFERENCES story_feuds(id)
);
CREATE INDEX IF NOT EXISTS idx_story_feud_participants_feud
    ON story_feud_participants(feud_id);
CREATE INDEX IF NOT EXISTS idx_story_feud_participants_participant
    ON story_feud_participants(participant_id);

CREATE TABLE IF NOT EXISTS storyline_actions (
    id TEXT PRIMARY KEY,
    feud_id TEXT NOT NULL,
    action_category TEXT NOT NULL,
    action_type TEXT NOT NULL,
    participants_json TEXT NOT NULL DEFAULT '[]',
    description TEXT NOT NULL,
    heat_change REAL NOT NULL,
    heat_after REAL NOT NULL,
    credibility_effect REAL NOT NULL DEFAULT 0,
    quality_score REAL NOT NULL DEFAULT 0,
    show_id TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (feud_id) REFERENCES story_feuds(id)
);
CREATE INDEX IF NOT EXISTS idx_storyline_actions_feud
    ON storyline_actions(feud_id, year, week);

CREATE TABLE IF NOT EXISTS story_arcs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    premise TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    planned_duration_weeks INTEGER NOT NULL,
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    current_chapter_id TEXT,
    cast_json TEXT NOT NULL DEFAULT '[]',
    completion_score REAL,
    booking_reputation_effect REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS story_arc_chapters (
    id TEXT PRIMARY KEY,
    arc_id TEXT NOT NULL,
    chapter_name TEXT NOT NULL,
    phase TEXT NOT NULL,
    planned_start_week_offset INTEGER NOT NULL,
    planned_end_week_offset INTEGER NOT NULL,
    planned_actions_json TEXT NOT NULL DEFAULT '[]',
    completed_actions INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'planned',
    fidelity_score REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (arc_id) REFERENCES story_arcs(id)
);
CREATE INDEX IF NOT EXISTS idx_story_arc_chapters_arc
    ON story_arc_chapters(arc_id, planned_start_week_offset);

CREATE TABLE IF NOT EXISTS story_arc_templates (
    id TEXT PRIMARY KEY,
    template_name TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL,
    duration_min_weeks INTEGER NOT NULL,
    duration_max_weeks INTEGER NOT NULL,
    roster_min INTEGER NOT NULL DEFAULT 2,
    roster_max INTEGER NOT NULL DEFAULT 4,
    complexity TEXT NOT NULL DEFAULT 'medium',
    success_rate TEXT NOT NULL DEFAULT 'medium',
    milestone_schema_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS story_arc_planning_profiles (
    id TEXT PRIMARY KEY,
    arc_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    template_id TEXT,
    source_type TEXT NOT NULL DEFAULT 'ai',
    source_id TEXT,
    planning_mode TEXT NOT NULL DEFAULT 'campaign',
    priority_score REAL NOT NULL DEFAULT 50,
    investment_score REAL NOT NULL DEFAULT 40,
    fatigue_score REAL NOT NULL DEFAULT 0,
    continuity_risk_score REAL NOT NULL DEFAULT 0,
    retcon_risk_score REAL NOT NULL DEFAULT 0,
    payoff_window_start_year INTEGER,
    payoff_window_start_week INTEGER,
    payoff_window_end_year INTEGER,
    payoff_window_end_week INTEGER,
    ai_strategy_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (arc_id) REFERENCES story_arcs(id),
    FOREIGN KEY (template_id) REFERENCES story_arc_templates(id)
);
CREATE INDEX IF NOT EXISTS idx_story_arc_profiles_arc
    ON story_arc_planning_profiles(arc_id);
CREATE INDEX IF NOT EXISTS idx_story_arc_profiles_source
    ON story_arc_planning_profiles(source_type, source_id);

CREATE TABLE IF NOT EXISTS story_arc_milestones (
    id TEXT PRIMARY KEY,
    arc_id TEXT NOT NULL,
    feud_id TEXT,
    milestone_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    planned_year INTEGER NOT NULL,
    planned_week INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    health_status TEXT NOT NULL DEFAULT 'flexible',
    visibility TEXT NOT NULL DEFAULT 'medium',
    crowd_emotion_target TEXT,
    required_participants_json TEXT NOT NULL DEFAULT '[]',
    dependency_ids_json TEXT NOT NULL DEFAULT '[]',
    production_notes TEXT,
    impact_scores_json TEXT NOT NULL DEFAULT '{}',
    success_score REAL,
    ai_generated INTEGER NOT NULL DEFAULT 1,
    requires_approval INTEGER NOT NULL DEFAULT 1,
    approved_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (arc_id) REFERENCES story_arcs(id)
);
CREATE INDEX IF NOT EXISTS idx_story_arc_milestones_week
    ON story_arc_milestones(planned_year, planned_week, status);
CREATE INDEX IF NOT EXISTS idx_story_arc_milestones_arc
    ON story_arc_milestones(arc_id, planned_year, planned_week);

CREATE TABLE IF NOT EXISTS story_arc_reviews (
    id TEXT PRIMARY KEY,
    review_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    source_type TEXT NOT NULL,
    source_id TEXT,
    arc_id TEXT,
    milestone_id TEXT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    ai_recommendation TEXT NOT NULL,
    options_json TEXT NOT NULL DEFAULT '[]',
    selected_option TEXT,
    decision_notes TEXT,
    due_year INTEGER,
    due_week INTEGER,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    deleted_at TEXT,
    FOREIGN KEY (arc_id) REFERENCES story_arcs(id),
    FOREIGN KEY (milestone_id) REFERENCES story_arc_milestones(id)
);
CREATE INDEX IF NOT EXISTS idx_story_arc_reviews_status
    ON story_arc_reviews(status, severity, created_at);

CREATE TABLE IF NOT EXISTS story_calendar_events (
    id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    tier TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    brand TEXT,
    venue_market TEXT,
    venue_capacity INTEGER,
    strategic_purpose TEXT NOT NULL,
    competition_pressure_score REAL NOT NULL DEFAULT 0,
    seasonal_notes TEXT,
    booking_strategy_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'planned',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_story_calendar_unique_week
    ON story_calendar_events(event_name, year, week);
CREATE INDEX IF NOT EXISTS idx_story_calendar_week
    ON story_calendar_events(year, week, tier);

CREATE TABLE IF NOT EXISTS story_arc_health_snapshots (
    id TEXT PRIMARY KEY,
    arc_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    investment_score REAL NOT NULL,
    fatigue_score REAL NOT NULL,
    stagnation_weeks INTEGER NOT NULL DEFAULT 0,
    lifecycle_stage TEXT NOT NULL,
    payoff_window_status TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (arc_id) REFERENCES story_arcs(id)
);
CREATE INDEX IF NOT EXISTS idx_story_arc_health_arc_week
    ON story_arc_health_snapshots(arc_id, year, week);

CREATE TABLE IF NOT EXISTS story_vision_goals (
    id TEXT PRIMARY KEY,
    vision_year INTEGER NOT NULL,
    category TEXT NOT NULL,
    objective TEXT NOT NULL,
    target_json TEXT NOT NULL DEFAULT '{}',
    current_progress REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'planned',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_story_vision_year
    ON story_vision_goals(vision_year, category);

CREATE TABLE IF NOT EXISTS short_programs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    phase TEXT NOT NULL DEFAULT 'setup',
    participants_json TEXT NOT NULL DEFAULT '[]',
    designated_winner_id TEXT,
    payoff_match_id TEXT,
    success_score REAL,
    momentum_effect_json TEXT NOT NULL DEFAULT '{}',
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    target_end_year INTEGER,
    target_end_week INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_short_programs_status
    ON short_programs(status);

CREATE TABLE IF NOT EXISTS storyline_payoffs (
    id TEXT PRIMARY KEY,
    feud_id TEXT,
    program_id TEXT,
    show_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    heat_at_booking REAL NOT NULL,
    timing_quality TEXT NOT NULL,
    finish_decisiveness REAL NOT NULL,
    crowd_investment REAL NOT NULL,
    closure_score REAL NOT NULL,
    match_quality REAL NOT NULL,
    payoff_score REAL NOT NULL,
    booking_legacy_effect REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_storyline_payoffs_feud
    ON storyline_payoffs(feud_id);

CREATE TABLE IF NOT EXISTS story_swerves (
    id TEXT PRIMARY KEY,
    feud_id TEXT,
    show_id TEXT,
    swerve_type TEXT NOT NULL,
    actor_id TEXT,
    target_id TEXT,
    motivation TEXT NOT NULL,
    unpredictability_score REAL NOT NULL,
    narrative_logic_score REAL NOT NULL,
    impact_score REAL NOT NULL,
    credibility_effect REAL NOT NULL,
    social_buzz_score REAL NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_story_swerves_feud
    ON story_swerves(feud_id, year, week);

CREATE TABLE IF NOT EXISTS promo_segments (
    id TEXT PRIMARY KEY,
    show_id TEXT,
    segment_id TEXT,
    feud_id TEXT,
    speaker_id TEXT NOT NULL,
    target_id TEXT,
    tone TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    script_content TEXT,
    script_quality REAL NOT NULL,
    delivery_modifier REAL NOT NULL,
    promo_quality REAL NOT NULL,
    heat_change REAL NOT NULL DEFAULT 0,
    character_momentum_delta REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_promo_segments_feud
    ON promo_segments(feud_id);

CREATE TABLE IF NOT EXISTS backstage_segments (
    id TEXT PRIMARY KEY,
    show_id TEXT,
    segment_id TEXT,
    feud_id TEXT,
    segment_type TEXT NOT NULL,
    location TEXT NOT NULL,
    participants_json TEXT NOT NULL DEFAULT '[]',
    acting_quality REAL NOT NULL,
    charisma_quality REAL NOT NULL,
    segment_quality REAL NOT NULL,
    heat_change REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_backstage_segments_feud
    ON backstage_segments(feud_id);

CREATE TABLE IF NOT EXISTS authority_figures (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    brand TEXT,
    credibility_score REAL NOT NULL DEFAULT 70,
    narrative_permissions_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS authority_storylines (
    id TEXT PRIMARY KEY,
    authority_id TEXT NOT NULL,
    angle_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    participants_json TEXT NOT NULL DEFAULT '[]',
    credibility_effect REAL NOT NULL DEFAULT 0,
    heat_score REAL NOT NULL DEFAULT 20,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (authority_id) REFERENCES authority_figures(id)
);

CREATE TABLE IF NOT EXISTS tournaments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    prize_type TEXT NOT NULL,
    prize_description TEXT NOT NULL,
    format TEXT NOT NULL,
    participant_count INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    duration_shows INTEGER NOT NULL DEFAULT 1,
    seeding_logic TEXT NOT NULL DEFAULT 'ranking',
    narrative_arc_score REAL NOT NULL DEFAULT 0,
    bracket_json TEXT NOT NULL DEFAULT '{}',
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS tournament_entries (
    id TEXT PRIMARY KEY,
    tournament_id TEXT NOT NULL,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    seed INTEGER NOT NULL,
    eliminated INTEGER NOT NULL DEFAULT 0,
    current_round INTEGER NOT NULL DEFAULT 1,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);
CREATE INDEX IF NOT EXISTS idx_tournament_entries_tournament
    ON tournament_entries(tournament_id, seed);

CREATE TABLE IF NOT EXISTS tournament_matches (
    id TEXT PRIMARY KEY,
    tournament_id TEXT NOT NULL,
    show_id TEXT,
    match_id TEXT,
    round_number INTEGER NOT NULL,
    bracket_position INTEGER NOT NULL,
    wrestler_a_id TEXT,
    wrestler_b_id TEXT,
    winner_id TEXT,
    upset_score REAL NOT NULL DEFAULT 0,
    feud_bonus REAL NOT NULL DEFAULT 0,
    social_spike_score REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);
CREATE INDEX IF NOT EXISTS idx_tournament_matches_tournament
    ON tournament_matches(tournament_id, round_number);

CREATE TABLE IF NOT EXISTS romantic_angles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    participants_json TEXT NOT NULL DEFAULT '[]',
    linked_feud_id TEXT,
    reception_risk_score REAL NOT NULL,
    crowd_support_score REAL NOT NULL,
    backlash_score REAL NOT NULL,
    history_json TEXT NOT NULL DEFAULT '[]',
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_romantic_angles_status
    ON romantic_angles(status);

CREATE TABLE IF NOT EXISTS legacy_relationships (
    id TEXT PRIMARY KEY,
    wrestler_a_id TEXT NOT NULL,
    wrestler_a_name TEXT NOT NULL,
    wrestler_b_id TEXT NOT NULL,
    wrestler_b_name TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    relationship_strength REAL NOT NULL DEFAULT 50,
    biological INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_legacy_relationships_wrestler_a
    ON legacy_relationships(wrestler_a_id);
CREATE INDEX IF NOT EXISTS idx_legacy_relationships_wrestler_b
    ON legacy_relationships(wrestler_b_id);

CREATE TABLE IF NOT EXISTS torch_passes (
    id TEXT PRIMARY KEY,
    legend_id TEXT NOT NULL,
    legend_name TEXT NOT NULL,
    rising_star_id TEXT NOT NULL,
    rising_star_name TEXT NOT NULL,
    show_id TEXT,
    match_id TEXT,
    structure_score REAL NOT NULL,
    climax_quality REAL NOT NULL,
    overness_transfer REAL NOT NULL,
    legacy_impact_score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS historical_callbacks (
    id TEXT PRIMARY KEY,
    callback_type TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_id TEXT NOT NULL,
    current_feud_id TEXT,
    referenced_participants_json TEXT NOT NULL DEFAULT '[]',
    heat_bonus REAL NOT NULL,
    description TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_historical_callbacks_feud
    ON historical_callbacks(current_feud_id);

CREATE TABLE IF NOT EXISTS tv_ratings (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL UNIQUE,
    show_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    base_viewership INTEGER NOT NULL,
    total_viewership INTEGER NOT NULL,
    rating_score REAL NOT NULL,
    booking_quality_score REAL NOT NULL,
    momentum_modifier REAL NOT NULL,
    competition_modifier REAL NOT NULL,
    opening_modifier REAL NOT NULL DEFAULT 0,
    main_event_modifier REAL NOT NULL DEFAULT 0,
    commercial_modifier REAL NOT NULL DEFAULT 0,
    demographic_value_index REAL NOT NULL,
    advertising_revenue INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tv_ratings_year_week
    ON tv_ratings(year, week);

CREATE TABLE IF NOT EXISTS tv_quarter_hour_ratings (
    id TEXT PRIMARY KEY,
    rating_id TEXT NOT NULL,
    show_id TEXT NOT NULL,
    quarter_index INTEGER NOT NULL,
    start_minute INTEGER NOT NULL,
    end_minute INTEGER NOT NULL,
    segment_id TEXT,
    content_summary TEXT NOT NULL,
    rating_score REAL NOT NULL,
    viewership INTEGER NOT NULL,
    viewer_delta INTEGER NOT NULL,
    analysis_note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (rating_id) REFERENCES tv_ratings(id)
);
CREATE INDEX IF NOT EXISTS idx_qh_ratings_show
    ON tv_quarter_hour_ratings(show_id, quarter_index);

CREATE TABLE IF NOT EXISTS tv_demographic_ratings (
    id TEXT PRIMARY KEY,
    rating_id TEXT NOT NULL,
    demographic TEXT NOT NULL,
    viewership INTEGER NOT NULL,
    rating_score REAL NOT NULL,
    ad_rate_multiplier REAL NOT NULL,
    revenue_contribution INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (rating_id) REFERENCES tv_ratings(id)
);
CREATE INDEX IF NOT EXISTS idx_demo_ratings_rating
    ON tv_demographic_ratings(rating_id);

CREATE TABLE IF NOT EXISTS ratings_insights (
    id TEXT PRIMARY KEY,
    show_id TEXT,
    insight_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    metric_value REAL NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ratings_insights_type
    ON ratings_insights(insight_type, created_at);

CREATE TABLE IF NOT EXISTS network_relationships (
    id TEXT PRIMARY KEY,
    network_name TEXT NOT NULL UNIQUE,
    relationship_score REAL NOT NULL DEFAULT 60,
    relationship_level TEXT NOT NULL DEFAULT 'stable',
    current_contract_id TEXT,
    content_profile TEXT NOT NULL DEFAULT 'balanced',
    demands_json TEXT NOT NULL DEFAULT '[]',
    promotional_support_score REAL NOT NULL DEFAULT 50,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS network_relationship_history (
    id TEXT PRIMARY KEY,
    network_id TEXT NOT NULL,
    show_id TEXT,
    change_amount REAL NOT NULL,
    score_after REAL NOT NULL,
    reason TEXT NOT NULL,
    trend_window_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (network_id) REFERENCES network_relationships(id)
);
CREATE INDEX IF NOT EXISTS idx_network_history_network
    ON network_relationship_history(network_id, year, week);

CREATE TABLE IF NOT EXISTS network_contracts (
    id TEXT PRIMARY KEY,
    network_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    end_week INTEGER NOT NULL,
    rights_fee_per_show INTEGER NOT NULL,
    time_slot TEXT NOT NULL,
    terms_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (network_id) REFERENCES network_relationships(id)
);

CREATE TABLE IF NOT EXISTS network_demands (
    id TEXT PRIMARY KEY,
    network_id TEXT NOT NULL,
    demand_type TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    compliance_score REAL NOT NULL DEFAULT 0,
    deadline_year INTEGER,
    deadline_week INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (network_id) REFERENCES network_relationships(id)
);

CREATE TABLE IF NOT EXISTS competing_events (
    id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    recurrence TEXT NOT NULL,
    year INTEGER,
    week INTEGER,
    day_of_week TEXT,
    audience_overlap_score REAL NOT NULL,
    impact_modifier REAL NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_competing_events_week
    ON competing_events(year, week);

CREATE TABLE IF NOT EXISTS competing_impact_history (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    competing_event_id TEXT,
    impact_modifier REAL NOT NULL,
    lost_viewers_estimate INTEGER NOT NULL,
    analysis_note TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_competing_impact_show
    ON competing_impact_history(show_id);

CREATE TABLE IF NOT EXISTS social_platform_metrics (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL UNIQUE,
    follower_count INTEGER NOT NULL,
    engagement_rate REAL NOT NULL,
    content_consistency_score REAL NOT NULL DEFAULT 50,
    platform_value_score REAL NOT NULL DEFAULT 50,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS social_metric_history (
    id TEXT PRIMARY KEY,
    platform_id TEXT NOT NULL,
    follower_count INTEGER NOT NULL,
    engagement_rate REAL NOT NULL,
    follower_delta INTEGER NOT NULL DEFAULT 0,
    engagement_delta REAL NOT NULL DEFAULT 0,
    reason TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (platform_id) REFERENCES social_platform_metrics(id)
);
CREATE INDEX IF NOT EXISTS idx_social_history_platform
    ON social_metric_history(platform_id, year, week);

CREATE TABLE IF NOT EXISTS social_spike_events (
    id TEXT PRIMARY KEY,
    show_id TEXT,
    source_type TEXT NOT NULL,
    source_id TEXT,
    description TEXT NOT NULL,
    spike_score REAL NOT NULL,
    follower_gain INTEGER NOT NULL,
    engagement_delta REAL NOT NULL,
    platforms_json TEXT NOT NULL DEFAULT '[]',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS wrestler_social_controversies (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    controversy_type TEXT NOT NULL,
    description TEXT NOT NULL,
    severity_score REAL NOT NULL,
    response_type TEXT,
    response_effect_json TEXT NOT NULL DEFAULT '{}',
    wrestler_reputation_delta REAL NOT NULL DEFAULT 0,
    brand_image_delta REAL NOT NULL DEFAULT 0,
    network_delta REAL NOT NULL DEFAULT 0,
    sponsor_delta REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_social_controversies_wrestler
    ON wrestler_social_controversies(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS streaming_deals (
    id TEXT PRIMARY KEY,
    platform_type TEXT NOT NULL,
    partner_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    revenue_model TEXT NOT NULL,
    annual_value INTEGER NOT NULL,
    revenue_share_pct REAL NOT NULL DEFAULT 0,
    attractiveness_score REAL NOT NULL,
    terms_json TEXT NOT NULL DEFAULT '{}',
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    duration_months INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS digital_content_library (
    id TEXT PRIMARY KEY,
    content_type TEXT NOT NULL,
    title TEXT NOT NULL,
    production_cost INTEGER NOT NULL,
    time_investment_hours INTEGER NOT NULL,
    featured_wrestlers_json TEXT NOT NULL DEFAULT '[]',
    associated_storylines_json TEXT NOT NULL DEFAULT '[]',
    engagement_score REAL NOT NULL,
    follower_gain INTEGER NOT NULL DEFAULT 0,
    ip_asset_value INTEGER NOT NULL DEFAULT 0,
    produced_year INTEGER NOT NULL,
    produced_week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_digital_content_type
    ON digital_content_library(content_type, produced_year, produced_week);

CREATE TABLE IF NOT EXISTS media_appearances (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    outlet_type TEXT NOT NULL,
    outlet_name TEXT NOT NULL,
    talking_points TEXT NOT NULL,
    restrictions TEXT,
    reach_score REAL NOT NULL,
    performance_score REAL NOT NULL,
    coverage_score REAL NOT NULL,
    mainstream_awareness_delta REAL NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_media_appearances_wrestler
    ON media_appearances(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS documentary_projects (
    id TEXT PRIMARY KEY,
    documentary_type TEXT NOT NULL,
    title TEXT NOT NULL,
    subject_id TEXT,
    subject_name TEXT,
    status TEXT NOT NULL DEFAULT 'in_production',
    budget INTEGER NOT NULL,
    timeline_weeks INTEGER NOT NULL,
    production_quality REAL NOT NULL,
    emotional_resonance REAL NOT NULL DEFAULT 50,
    current_storyline_relevance REAL NOT NULL DEFAULT 0,
    reception_score REAL,
    distribution_plan TEXT NOT NULL,
    release_year INTEGER,
    release_week INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS video_game_licenses (
    id TEXT PRIMARY KEY,
    developer_name TEXT NOT NULL,
    game_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    duration_months INTEGER NOT NULL,
    upfront_fee INTEGER NOT NULL,
    royalty_pct REAL NOT NULL DEFAULT 0,
    exclusivity TEXT NOT NULL DEFAULT 'none',
    roster_requirement INTEGER NOT NULL DEFAULT 0,
    belts_included_json TEXT NOT NULL DEFAULT '[]',
    game_quality_score REAL NOT NULL DEFAULT 50,
    brand_awareness_delta REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS press_conferences (
    id TEXT PRIMARY KEY,
    conference_type TEXT NOT NULL,
    announcement TEXT NOT NULL,
    spokesperson_id TEXT,
    spokesperson_name TEXT,
    participants_json TEXT NOT NULL DEFAULT '[]',
    significance_score REAL NOT NULL,
    execution_quality REAL NOT NULL,
    media_coverage_score REAL NOT NULL,
    downstream_impact_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_press_conferences_week
    ON press_conferences(year, week);

CREATE TABLE IF NOT EXISTS business_metric_snapshots (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    mainstream_awareness REAL NOT NULL DEFAULT 0,
    sponsorship_attractiveness REAL NOT NULL DEFAULT 0,
    streaming_attractiveness REAL NOT NULL DEFAULT 0,
    booking_credibility REAL NOT NULL DEFAULT 70,
    promotion_momentum REAL NOT NULL DEFAULT 50,
    valuation_estimate INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_business_snapshots_week
    ON business_metric_snapshots(year, week);

CREATE TABLE IF NOT EXISTS ai_showrunner_runs (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    show_id TEXT NOT NULL,
    show_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    autonomy_level TEXT NOT NULL DEFAULT 'balanced',
    risk_tolerance REAL NOT NULL DEFAULT 0.55,
    opportunity_rotation_json TEXT NOT NULL DEFAULT '[]',
    generated_card_json TEXT NOT NULL DEFAULT '{}',
    decisions_json TEXT NOT NULL DEFAULT '[]',
    auto_executed_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'drafted',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_showrunner_runs_week
    ON ai_showrunner_runs(year, week, show_id);

CREATE TABLE IF NOT EXISTS ple_roadmap_plans (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    target_year INTEGER NOT NULL,
    target_week INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    headline_plan TEXT NOT NULL,
    main_event_json TEXT NOT NULL DEFAULT '{}',
    title_plans_json TEXT NOT NULL DEFAULT '[]',
    risk_bets_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ple_roadmap_event
    ON ple_roadmap_plans(event_name, target_year, target_week);

CREATE TABLE IF NOT EXISTS booker_approval_queue (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT,
    category TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    recommendation_json TEXT NOT NULL DEFAULT '{}',
    deadline_year INTEGER,
    deadline_week INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    autonomy_policy TEXT NOT NULL DEFAULT 'ask',
    auto_execute_after_week INTEGER,
    executed_at TEXT,
    player_response_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_booker_approval_status
    ON booker_approval_queue(status, priority, created_at);

CREATE TABLE IF NOT EXISTS angle_library_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    segment_type TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'medium',
    cooldown_weeks INTEGER NOT NULL DEFAULT 4,
    min_participants INTEGER NOT NULL DEFAULT 1,
    max_participants INTEGER NOT NULL DEFAULT 6,
    eligibility_json TEXT NOT NULL DEFAULT '{}',
    mechanical_effects_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_angle_library_category
    ON angle_library_templates(category, risk_level);

CREATE TABLE IF NOT EXISTS angle_executions (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    template_name TEXT NOT NULL,
    show_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    participants_json TEXT NOT NULL DEFAULT '[]',
    autonomy_status TEXT NOT NULL DEFAULT 'drafted',
    impact_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_angle_executions_week
    ON angle_executions(year, week, template_id);

CREATE TABLE IF NOT EXISTS money_in_bank_briefcases (
    id TEXT PRIMARY KEY,
    division TEXT NOT NULL,
    holder_id TEXT NOT NULL,
    holder_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    won_year INTEGER NOT NULL,
    won_week INTEGER NOT NULL,
    target_title_id TEXT,
    target_title_name TEXT,
    cash_in_window_weeks INTEGER NOT NULL DEFAULT 52,
    cash_in_attempts_json TEXT NOT NULL DEFAULT '[]',
    next_ai_check_year INTEGER,
    next_ai_check_week INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_mitb_status
    ON money_in_bank_briefcases(status, division, won_year, won_week);

CREATE TABLE IF NOT EXISTS war_games_plans (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    target_event_name TEXT NOT NULL,
    target_year INTEGER NOT NULL,
    target_week INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'building',
    faction_a_json TEXT NOT NULL DEFAULT '[]',
    faction_b_json TEXT NOT NULL DEFAULT '[]',
    advantage_holder_json TEXT NOT NULL DEFAULT '{}',
    stakes_json TEXT NOT NULL DEFAULT '{}',
    escalation_beats_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_war_games_target
    ON war_games_plans(target_event_name, target_year, target_week);

CREATE TABLE IF NOT EXISTS crown_tournament_payoffs (
    id TEXT PRIMARY KEY,
    tournament_type TEXT NOT NULL,
    division TEXT NOT NULL,
    winner_id TEXT NOT NULL,
    winner_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    won_year INTEGER NOT NULL,
    won_week INTEGER NOT NULL,
    payoff_event_name TEXT NOT NULL,
    payoff_year INTEGER NOT NULL,
    payoff_week INTEGER NOT NULL,
    title_shot_json TEXT NOT NULL DEFAULT '{}',
    coronation_angle_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_crown_payoff_year_type
    ON crown_tournament_payoffs(tournament_type, division, won_year);

CREATE TABLE IF NOT EXISTS dark_house_show_runs (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    parent_show_id TEXT,
    show_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    show_mode TEXT NOT NULL,
    autonomy_level TEXT NOT NULL DEFAULT 'balanced',
    status TEXT NOT NULL DEFAULT 'completed',
    roster_focus_json TEXT NOT NULL DEFAULT '[]',
    card_json TEXT NOT NULL DEFAULT '{}',
    results_json TEXT NOT NULL DEFAULT '{}',
    opportunity_impacts_json TEXT NOT NULL DEFAULT '[]',
    attendance INTEGER NOT NULL DEFAULT 0,
    revenue INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_dark_house_show_runs_week
    ON dark_house_show_runs(year, week, brand, show_mode);

CREATE TABLE IF NOT EXISTS live_show_interruptions (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    show_id TEXT NOT NULL,
    show_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    trigger_context TEXT NOT NULL,
    interruption_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'inserted',
    participants_json TEXT NOT NULL DEFAULT '[]',
    segment_payload_json TEXT NOT NULL DEFAULT '{}',
    mechanical_effects_json TEXT NOT NULL DEFAULT '[]',
    inserted_card_position INTEGER NOT NULL DEFAULT 0,
    autonomy_policy TEXT NOT NULL DEFAULT 'auto',
    approval_id TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_live_interruptions_show
    ON live_show_interruptions(show_id, year, week, created_at);

CREATE TABLE IF NOT EXISTS promo_dialogue_beats (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    show_id TEXT,
    source_type TEXT NOT NULL,
    source_id TEXT,
    beat_type TEXT NOT NULL,
    tone TEXT NOT NULL DEFAULT 'intense',
    status TEXT NOT NULL DEFAULT 'drafted',
    participants_json TEXT NOT NULL DEFAULT '[]',
    hook_text TEXT NOT NULL,
    lines_json TEXT NOT NULL DEFAULT '[]',
    crowd_goal TEXT NOT NULL DEFAULT 'engagement',
    risk_level TEXT NOT NULL DEFAULT 'medium',
    mechanical_effects_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_promo_dialogue_beats_week
    ON promo_dialogue_beats(year, week, show_id, source_type);

CREATE TABLE IF NOT EXISTS post_show_fallout_reports (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    show_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    show_type TEXT NOT NULL DEFAULT 'weekly_tv',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    autonomy_level TEXT NOT NULL DEFAULT 'balanced',
    overall_rating REAL NOT NULL DEFAULT 0,
    urgency_score REAL NOT NULL DEFAULT 0,
    summary TEXT NOT NULL,
    headline_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_post_show_fallout_show
    ON post_show_fallout_reports(show_id, year, week);
CREATE INDEX IF NOT EXISTS idx_post_show_fallout_status
    ON post_show_fallout_reports(status, year DESC, week DESC);

CREATE TABLE IF NOT EXISTS post_show_fallout_items (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    urgency TEXT NOT NULL DEFAULT 'medium',
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    suggested_actions_json TEXT NOT NULL DEFAULT '[]',
    mechanical_effects_json TEXT NOT NULL DEFAULT '[]',
    requires_response INTEGER NOT NULL DEFAULT 0,
    auto_execute_allowed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open',
    approval_id TEXT,
    player_response_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    deleted_at TEXT,
    FOREIGN KEY (report_id) REFERENCES post_show_fallout_reports(id)
);
CREATE INDEX IF NOT EXISTS idx_post_show_fallout_items_report
    ON post_show_fallout_items(report_id, urgency, status);
CREATE INDEX IF NOT EXISTS idx_post_show_fallout_items_approval
    ON post_show_fallout_items(approval_id);

CREATE TABLE IF NOT EXISTS internal_simulation_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    trigger_year INTEGER NOT NULL,
    trigger_week INTEGER NOT NULL,
    status TEXT NOT NULL,
    reads_json TEXT NOT NULL DEFAULT '[]',
    writes_json TEXT NOT NULL DEFAULT '[]',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_internal_jobs_type_week
    ON internal_simulation_jobs(job_type, trigger_year, trigger_week);
"""


DOWN_SQL = """
DROP TABLE IF EXISTS internal_simulation_jobs;
DROP TABLE IF EXISTS post_show_fallout_items;
DROP TABLE IF EXISTS post_show_fallout_reports;
DROP TABLE IF EXISTS promo_dialogue_beats;
DROP TABLE IF EXISTS live_show_interruptions;
DROP TABLE IF EXISTS dark_house_show_runs;
DROP TABLE IF EXISTS crown_tournament_payoffs;
DROP TABLE IF EXISTS war_games_plans;
DROP TABLE IF EXISTS money_in_bank_briefcases;
DROP TABLE IF EXISTS angle_executions;
DROP TABLE IF EXISTS angle_library_templates;
DROP TABLE IF EXISTS booker_approval_queue;
DROP TABLE IF EXISTS ple_roadmap_plans;
DROP TABLE IF EXISTS ai_showrunner_runs;
DROP TABLE IF EXISTS business_metric_snapshots;
DROP TABLE IF EXISTS press_conferences;
DROP TABLE IF EXISTS video_game_licenses;
DROP TABLE IF EXISTS documentary_projects;
DROP TABLE IF EXISTS media_appearances;
DROP TABLE IF EXISTS digital_content_library;
DROP TABLE IF EXISTS streaming_deals;
DROP TABLE IF EXISTS wrestler_social_controversies;
DROP TABLE IF EXISTS social_spike_events;
DROP TABLE IF EXISTS social_metric_history;
DROP TABLE IF EXISTS social_platform_metrics;
DROP TABLE IF EXISTS competing_impact_history;
DROP TABLE IF EXISTS competing_events;
DROP TABLE IF EXISTS network_demands;
DROP TABLE IF EXISTS network_contracts;
DROP TABLE IF EXISTS network_relationship_history;
DROP TABLE IF EXISTS network_relationships;
DROP TABLE IF EXISTS ratings_insights;
DROP TABLE IF EXISTS tv_demographic_ratings;
DROP TABLE IF EXISTS tv_quarter_hour_ratings;
DROP TABLE IF EXISTS tv_ratings;
DROP TABLE IF EXISTS historical_callbacks;
DROP TABLE IF EXISTS torch_passes;
DROP TABLE IF EXISTS legacy_relationships;
DROP TABLE IF EXISTS romantic_angles;
DROP TABLE IF EXISTS tournament_matches;
DROP TABLE IF EXISTS tournament_entries;
DROP TABLE IF EXISTS tournaments;
DROP TABLE IF EXISTS authority_storylines;
DROP TABLE IF EXISTS authority_figures;
DROP TABLE IF EXISTS backstage_segments;
DROP TABLE IF EXISTS promo_segments;
DROP TABLE IF EXISTS story_swerves;
DROP TABLE IF EXISTS storyline_payoffs;
DROP TABLE IF EXISTS short_programs;
DROP TABLE IF EXISTS story_vision_goals;
DROP TABLE IF EXISTS story_arc_health_snapshots;
DROP TABLE IF EXISTS story_calendar_events;
DROP TABLE IF EXISTS story_arc_reviews;
DROP TABLE IF EXISTS story_arc_milestones;
DROP TABLE IF EXISTS story_arc_planning_profiles;
DROP TABLE IF EXISTS story_arc_templates;
DROP TABLE IF EXISTS story_arc_chapters;
DROP TABLE IF EXISTS story_arcs;
DROP TABLE IF EXISTS storyline_actions;
DROP TABLE IF EXISTS story_feud_participants;
DROP TABLE IF EXISTS story_feuds;
DROP TABLE IF EXISTS show_theme_applications;
DROP TABLE IF EXISTS show_theme_templates;
DROP TABLE IF EXISTS wrestler_development_progress;
DROP TABLE IF EXISTS market_satisfaction_history;
DROP TABLE IF EXISTS dark_match_history;
DROP TABLE IF EXISTS main_event_assessments;
DROP TABLE IF EXISTS opening_segment_assessments;
DROP TABLE IF EXISTS return_records;
DROP TABLE IF EXISTS return_anticipation_segments;
DROP TABLE IF EXISTS debut_records;
DROP TABLE IF EXISTS debut_vignettes;
DROP TABLE IF EXISTS interference_history;
DROP TABLE IF EXISTS commercial_breaks;
DROP TABLE IF EXISTS booking_segments;
DROP TABLE IF EXISTS booking_show_plans;
DROP TABLE IF EXISTS phase_lookup_values;
DELETE FROM schema_migrations WHERE migration_id = '20260506_064_137_booking_story_media';
"""


LOOKUP_SEEDS = {
    "interference_purpose": [
        ("attack_competitor", "Attack the active competitor"),
        ("distract_loss", "Distract to cause a loss"),
        ("assist_win", "Assist in a win"),
        ("brawl_both", "Brawl with both competitors"),
        ("post_match_statement", "Post-match statement"),
    ],
    "debut_method": [("surprise", "Surprise"), ("teased", "Teased")],
    "return_type": [("cold", "Cold"), ("announced", "Announced")],
    "return_context": [
        ("babyface_comeback", "Babyface comeback"),
        ("heel_return", "Surprising heel return"),
        ("betrayal_return", "Shocking betrayal return"),
        ("authority_sanctioned", "Authority-sanctioned return"),
        ("underground", "Underground return"),
    ],
    "commercial_strategy": [
        ("neutral_reset", "Neutral reset"),
        ("cliffhanger", "Cliffhanger"),
        ("bad_cut", "Bad cut"),
        ("match_midpoint", "Match midpoint"),
    ],
    "theme_category": [
        ("anniversary", "Anniversary show"),
        ("tribute", "Tribute show"),
        ("tournament", "Tournament episode"),
        ("championship_showcase", "Championship showcase"),
        ("nostalgia", "Nostalgia show"),
        ("grudge_special", "Grudge match special"),
        ("stipulation_special", "Stipulation special"),
    ],
    "feud_basis": [
        ("championship_dispute", "Championship dispute"),
        ("personal_grudge", "Personal grudge"),
        ("betrayal", "Betrayal"),
        ("respect_issue", "Respect issue"),
        ("faction_warfare", "Faction warfare"),
        ("family_drama", "Family drama"),
        ("authority_conflict", "Authority conflict"),
        ("philosophical_difference", "Philosophical difference"),
        ("territory_dispute", "Territory dispute"),
    ],
    "heat_action_type": [
        ("in_ring_brawl", "In-ring brawl"),
        ("locker_room_attack", "Locker room attack"),
        ("parking_lot_ambush", "Parking lot ambush"),
        ("post_match_beatdown", "Post-match beatdown"),
        ("promo_challenge", "Promo challenge"),
        ("response_promo", "Response promo"),
        ("contract_signing", "Contract signing"),
        ("video_package", "Video package"),
        ("rival_match_interference", "Rival match interference"),
        ("title_sabotage", "Title opportunity sabotage"),
        ("ally_attack", "Attack a rival's ally"),
        ("personal_property", "Personal property destruction"),
        ("family_involvement", "Family involvement"),
        ("public_humiliation", "Public humiliation"),
        ("secret_revelation", "Secret revelation"),
        ("career_threat", "Career threat"),
    ],
    "promo_tone": [
        ("aggressive_confrontation", "Aggressive confrontation"),
        ("emotional_babyface", "Emotional babyface appeal"),
        ("arrogant_heel", "Arrogant heel boasting"),
        ("comedic", "Comedic character work"),
        ("mysterious", "Mysterious and cryptic"),
        ("authoritative", "Authoritative announcement"),
        ("manifesto", "Passionate manifesto"),
    ],
    "backstage_type": [
        ("interview", "Interview"),
        ("confrontation", "Confrontation"),
        ("attack", "Attack"),
        ("authority_interaction", "Authority figure interaction"),
        ("comedy_bit", "Comedy bit"),
        ("mysterious_vignette", "Mysterious vignette"),
        ("pre_match_ritual", "Pre-match ritual"),
        ("celebration", "Celebration"),
    ],
    "backstage_location": [
        ("locker_room_hallway", "Locker room hallway"),
        ("trainers_room", "Trainer's room"),
        ("parking_garage", "Parking garage"),
        ("catering", "Catering area"),
        ("gorilla_position", "Gorilla position"),
        ("authority_office", "Authority figure office"),
        ("production_area", "Production area"),
        ("external_location", "External location"),
    ],
    "authority_role": [
        ("owner", "Owner"),
        ("general_manager", "General manager"),
        ("commissioner", "Commissioner"),
        ("investor", "On-screen investor"),
        ("corrupt_official", "Corrupt official"),
    ],
    "swerve_type": [
        ("betrayal", "Betrayal"),
        ("revelation", "Revelation"),
        ("allegiance_switch", "Allegiance switch"),
        ("return_subversion", "Return subversion"),
        ("outcome_subversion", "Outcome subversion"),
    ],
    "tournament_format": [
        ("single_elimination", "Single elimination"),
        ("double_elimination", "Double elimination"),
        ("round_robin", "Round robin"),
        ("swiss", "Swiss-style progression"),
    ],
    "romantic_relationship_type": [
        ("genuine_partnership", "Genuine partnership"),
        ("one_sided_infatuation", "One-sided infatuation"),
        ("managerial_romance", "Managerial romance"),
        ("jealousy_triangle", "Jealousy triangle"),
        ("betrayal_romance", "Betrayal romance"),
        ("forbidden_romance", "Forbidden romance"),
    ],
    "legacy_relationship_type": [
        ("father_son", "Father and son"),
        ("siblings", "Siblings"),
        ("cousins", "Cousins"),
        ("trainer_student", "Trainer and student"),
        ("chosen_family", "Chosen family"),
        ("historic_rivals", "Historic rivals"),
    ],
    "social_platform": [
        ("short_form_video", "Short-form video"),
        ("microblogging", "Microblogging"),
        ("photo_video", "Photo and video"),
        ("long_form_video", "Long-form video"),
        ("community_discussion", "Community discussion"),
    ],
    "controversy_type": [
        ("rival_promotion_comments", "Inflammatory rival promotion comments"),
        ("divisive_personal_opinion", "Divisive personal opinion"),
        ("backstage_complaint", "Behind-the-scenes complaint"),
        ("fan_boundary_issue", "Fan boundary issue"),
        ("financial_legal_disclosure", "Financial or legal disclosure"),
        ("positive_viral_moment", "Positive viral moment"),
    ],
    "streaming_platform_type": [
        ("general_entertainment", "General entertainment streamer"),
        ("sports_focused", "Sports-focused streamer"),
        ("wrestling_dedicated", "Wrestling-specific service"),
        ("international_partner", "International partner"),
    ],
    "content_type": [
        ("highlight_reel", "Highlight reel"),
        ("classic_full_match", "Classic full match"),
        ("exclusive_interview", "Exclusive digital content"),
        ("documentary_short", "Documentary-style content"),
        ("countdown_ranking", "Countdown and ranking"),
        ("direct_to_camera", "Direct-to-camera content"),
    ],
    "media_outlet_type": [
        ("wrestling_podcast", "Wrestling podcast"),
        ("sports_show", "Mainstream sports show"),
        ("entertainment_tv", "Entertainment television"),
        ("press_interview", "Press interview"),
        ("influencer_collaboration", "Influencer collaboration"),
    ],
    "documentary_type": [
        ("career_retrospective", "Career retrospective"),
        ("event_retrospective", "Event retrospective"),
        ("inside_look", "Inside-look production"),
        ("storyline_deconstruction", "Storyline deconstruction"),
        ("promotion_history", "Promotion history"),
    ],
    "press_conference_type": [
        ("major_match_announcement", "Major match announcement"),
        ("contract_signing", "Contract signing"),
        ("milestone_announcement", "Milestone announcement"),
        ("crisis_management", "Crisis management"),
    ],
}


DEFAULT_THEMES = [
    (
        "theme_anniversary",
        "Anniversary Special",
        "anniversary",
        "A milestone celebration of the promotion's history.",
        {"recommended_segments": ["legacy_video", "major_return"], "minimum_special_matches_pct": 0.25},
        8.0,
        0.08,
        6.0,
    ),
    (
        "theme_tribute",
        "Tribute Night",
        "tribute",
        "A show honoring a legendary figure or historical wrestling moment.",
        {"requires_tribute_subject": True, "minimum_video_packages": 1},
        5.0,
        0.04,
        12.0,
    ),
    (
        "theme_tournament",
        "Tournament Episode",
        "tournament",
        "A bracket-driven show where progression carries the card.",
        {"minimum_tournament_matches_pct": 0.50, "requires_bracket_segment": True},
        6.0,
        0.06,
        4.0,
    ),
    (
        "theme_championship",
        "Championship Showcase",
        "championship_showcase",
        "A title-heavy episode built around championship stakes.",
        {"minimum_title_matches_pct": 0.50},
        7.0,
        0.07,
        5.0,
    ),
    (
        "theme_grudge",
        "Grudge Match Special",
        "grudge_special",
        "A feud-focused card where every major match has conflict context.",
        {"minimum_feud_matches_pct": 0.60},
        6.5,
        0.05,
        4.0,
    ),
    (
        "theme_stipulation",
        "Stipulation Special",
        "stipulation_special",
        "A show where unique match rules are the attraction.",
        {"minimum_stipulation_matches_pct": 0.60},
        5.0,
        0.05,
        3.0,
    ),
]


DEFAULT_COMPETING_EVENTS = [
    ("comp_super_bowl", "Major Football Championship", "sports", "annual_week", 6, 0.85, -0.18),
    ("comp_basketball_finals", "Basketball Finals Game", "sports", "annual_week", 24, 0.55, -0.10),
    ("comp_awards", "Major Awards Ceremony", "awards", "annual_week", 10, 0.35, -0.06),
    ("comp_election", "Election Night Coverage", "politics", "annual_week", 45, 0.70, -0.15),
    ("comp_wrestling_ppv", "Competing Wrestling Premium Event", "wrestling", "annual_week", 31, 0.65, -0.12),
]


def create_phase_expansion_tables(database) -> None:
    """Apply the feature #64-72, #88-100, #126-137 schema migration."""

    conn = database.conn
    cursor = conn.cursor()
    cursor.executescript(UP_SQL)
    _repair_existing_phase_tables(cursor)
    _seed_lookup_values(cursor)
    _seed_theme_templates(cursor)
    _seed_network_and_social(cursor)
    _seed_competing_events(cursor)
    cursor.execute(
        "INSERT OR REPLACE INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
        (MIGRATION_ID, datetime.now().isoformat()),
    )
    conn.commit()


def _repair_existing_phase_tables(cursor) -> None:
    """Bring older live databases up to the current idempotent schema."""

    existing = {
        row[1] for row in cursor.execute("PRAGMA table_info(commercial_breaks)").fetchall()
    }
    additions = {
        "position_index": "INTEGER NOT NULL DEFAULT 0",
        "placement_type": "TEXT NOT NULL DEFAULT 'between_segments'",
        "after_segment_id": "TEXT",
        "during_match_id": "TEXT",
        "minute_marker": "INTEGER NOT NULL DEFAULT 0",
        "strategy": "TEXT NOT NULL DEFAULT 'neutral_reset'",
        "quality_score": "REAL NOT NULL DEFAULT 50",
        "viewer_return_modifier": "REAL NOT NULL DEFAULT 0",
        "satisfaction_modifier": "REAL NOT NULL DEFAULT 0",
        "updated_at": "TEXT",
        "deleted_at": "TEXT",
    }
    for column, ddl in additions.items():
        if column not in existing:
            try:
                cursor.execute(f"ALTER TABLE commercial_breaks ADD COLUMN {column} {ddl}")
                existing.add(column)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
                existing.add(column)


def drop_phase_expansion_tables(database) -> None:
    """Rollback helper for development and tests."""

    database.conn.executescript(DOWN_SQL)
    database.conn.commit()


def _seed_lookup_values(cursor) -> None:
    now = datetime.now().isoformat()
    for category, values in LOOKUP_SEEDS.items():
        for order, (value, label) in enumerate(values, start=1):
            cursor.execute(
                """
                INSERT OR IGNORE INTO phase_lookup_values (
                    id, category, value, label, sort_order, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{category}_{value}",
                    category,
                    value,
                    label,
                    order,
                    "{}",
                    now,
                    now,
                ),
            )


def _seed_theme_templates(cursor) -> None:
    now = datetime.now().isoformat()
    for theme_id, name, category, description, requirements, marketing, ratings, press in DEFAULT_THEMES:
        cursor.execute(
            """
            INSERT OR IGNORE INTO show_theme_templates (
                id, name, category, description, requirements_json,
                marketing_bonus, ratings_bonus, press_bonus,
                created_by_user, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                theme_id,
                name,
                category,
                description,
                json.dumps(requirements),
                marketing,
                ratings,
                press,
                now,
                now,
            ),
        )


def _seed_network_and_social(cursor) -> None:
    now = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT OR IGNORE INTO network_relationships (
            id, network_name, relationship_score, relationship_level,
            content_profile, demands_json, promotional_support_score, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "network_primary",
            "Prime Sports Network",
            65.0,
            "stable",
            "balanced",
            json.dumps(
                [
                    {
                        "demand_type": "runtime",
                        "description": "Deliver the contracted runtime without excessive overruns.",
                        "severity": "medium",
                    }
                ]
            ),
            55.0,
            now,
        ),
    )

    platform_defaults = {
        "short_form_video": (250000, 0.075, 62),
        "microblogging": (400000, 0.045, 58),
        "photo_video": (325000, 0.052, 55),
        "long_form_video": (180000, 0.038, 50),
        "community_discussion": (90000, 0.095, 60),
    }
    for platform, (followers, engagement, value) in platform_defaults.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO social_platform_metrics (
                id, platform, follower_count, engagement_rate,
                content_consistency_score, platform_value_score, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"social_{platform}",
                platform,
                followers,
                engagement,
                50.0,
                value,
                now,
            ),
        )


def _seed_competing_events(cursor) -> None:
    now = datetime.now().isoformat()
    for event_id, name, event_type, recurrence, week, overlap, modifier in DEFAULT_COMPETING_EVENTS:
        cursor.execute(
            """
            INSERT OR IGNORE INTO competing_events (
                id, event_name, event_type, recurrence, week,
                audience_overlap_score, impact_modifier, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                name,
                event_type,
                recurrence,
                week,
                overlap,
                modifier,
                "Seeded annual competition calendar entry.",
                now,
                now,
            ),
        )

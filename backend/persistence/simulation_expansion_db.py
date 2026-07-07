"""
Persistent schema for locker room culture, developmental pipeline, and advanced
simulation features.

The project uses idempotent SQLite migrations instead of an external migration
runner. This module keeps explicit up/down SQL so the feature set can be
created in application startup and rolled back in tests or local maintenance.
"""

from __future__ import annotations

from datetime import datetime


MIGRATION_ID = "20260506_149_182_243_250_simulation_expansion"


UP_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_expansion_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    status TEXT NOT NULL,
    seed INTEGER,
    reads_json TEXT NOT NULL DEFAULT '[]',
    writes_json TEXT NOT NULL DEFAULT '[]',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sim_jobs_type_week
    ON simulation_expansion_jobs(job_type, year, week);

CREATE TABLE IF NOT EXISTS locker_wrestler_state (
    wrestler_id TEXT PRIMARY KEY,
    wrestler_name TEXT NOT NULL,
    brand TEXT NOT NULL DEFAULT 'ROC Alpha',
    roster_designation TEXT NOT NULL DEFAULT 'main_roster',
    morale_score REAL NOT NULL DEFAULT 50,
    morale_level TEXT NOT NULL DEFAULT 'neutral',
    ego_level REAL NOT NULL DEFAULT 30,
    professionalism REAL NOT NULL DEFAULT 60,
    backstage_influence REAL NOT NULL DEFAULT 25,
    management_relationship REAL NOT NULL DEFAULT 50,
    creative_preferences_json TEXT NOT NULL DEFAULT '{}',
    last_primary_factors_json TEXT NOT NULL DEFAULT '{}',
    performance_modifier REAL NOT NULL DEFAULT 0,
    release_request_risk REAL NOT NULL DEFAULT 0,
    refusal_risk REAL NOT NULL DEFAULT 0,
    incident_risk REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_locker_state_brand_designation
    ON locker_wrestler_state(brand, roster_designation);
CREATE INDEX IF NOT EXISTS idx_locker_state_morale
    ON locker_wrestler_state(morale_score);

CREATE TABLE IF NOT EXISTS locker_morale_history (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    morale_score REAL NOT NULL,
    morale_level TEXT NOT NULL,
    factors_json TEXT NOT NULL DEFAULT '{}',
    performance_modifier REAL NOT NULL DEFAULT 0,
    event_risks_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_morale_history_wrestler_week
    ON locker_morale_history(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS locker_atmosphere_snapshots (
    id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    atmosphere_score REAL NOT NULL,
    atmosphere_level TEXT NOT NULL,
    average_morale REAL NOT NULL,
    match_quality_modifier REAL NOT NULL DEFAULT 0,
    developmental_modifier REAL NOT NULL DEFAULT 0,
    media_risk_modifier REAL NOT NULL DEFAULT 0,
    recruitment_modifier REAL NOT NULL DEFAULT 0,
    inputs_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_atmosphere_brand_week
    ON locker_atmosphere_snapshots(brand, year, week);

CREATE TABLE IF NOT EXISTS locker_creative_disagreements (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    show_id TEXT,
    booking_object_ref TEXT NOT NULL,
    direction_summary TEXT NOT NULL,
    preference_conflict_score REAL NOT NULL,
    escalation_level TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    resolution_choice TEXT,
    morale_impact REAL NOT NULL DEFAULT 0,
    ego_impact REAL NOT NULL DEFAULT 0,
    atmosphere_impact REAL NOT NULL DEFAULT 0,
    aftermath_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_creative_disagreements_wrestler_status
    ON locker_creative_disagreements(wrestler_id, status);

CREATE TABLE IF NOT EXISTS locker_backstage_influence_history (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    influence_score REAL NOT NULL,
    factors_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS locker_cliques (
    id TEXT PRIMARY KEY,
    clique_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    leader_wrestler_id TEXT,
    leader_wrestler_name TEXT,
    solidarity REAL NOT NULL DEFAULT 50,
    behavior_classification TEXT NOT NULL DEFAULT 'neutral',
    political_power REAL NOT NULL DEFAULT 0,
    health_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_cliques_brand_behavior
    ON locker_cliques(brand, behavior_classification);

CREATE TABLE IF NOT EXISTS locker_clique_members (
    id TEXT PRIMARY KEY,
    clique_id TEXT NOT NULL,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    affinity_score REAL NOT NULL DEFAULT 50,
    role TEXT NOT NULL DEFAULT 'member',
    joined_year INTEGER NOT NULL,
    joined_week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (clique_id) REFERENCES locker_cliques(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_clique_members_unique
    ON locker_clique_members(clique_id, wrestler_id);

CREATE TABLE IF NOT EXISTS locker_bullying_incidents (
    id TEXT PRIMARY KEY,
    perpetrator_ids_json TEXT NOT NULL DEFAULT '[]',
    perpetrator_names_json TEXT NOT NULL DEFAULT '[]',
    target_wrestler_id TEXT NOT NULL,
    target_wrestler_name TEXT NOT NULL,
    incident_type TEXT NOT NULL,
    severity REAL NOT NULL,
    witness_count INTEGER NOT NULL DEFAULT 0,
    reported_to_management INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open',
    response_choice TEXT,
    morale_impact REAL NOT NULL DEFAULT 0,
    atmosphere_impact REAL NOT NULL DEFAULT 0,
    media_scandal_risk REAL NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS locker_substance_issues (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'hidden',
    severity REAL NOT NULL,
    discovered_year INTEGER,
    discovered_week INTEGER,
    visible_signs_json TEXT NOT NULL DEFAULT '[]',
    response_path TEXT,
    recovery_progress REAL NOT NULL DEFAULT 0,
    relapse_risk REAL NOT NULL DEFAULT 0,
    confidentiality_level TEXT NOT NULL DEFAULT 'management',
    history_json TEXT NOT NULL DEFAULT '[]',
    created_year INTEGER NOT NULL,
    created_week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_substance_wrestler_status
    ON locker_substance_issues(wrestler_id, status);

CREATE TABLE IF NOT EXISTS locker_meetings (
    id TEXT PRIMARY KEY,
    meeting_type TEXT NOT NULL,
    purpose TEXT NOT NULL,
    conductor_name TEXT NOT NULL,
    communication_skill REAL NOT NULL DEFAULT 65,
    target_brand TEXT,
    crisis_ref TEXT,
    effectiveness_score REAL NOT NULL,
    outcome_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS locker_meeting_attendees (
    id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    morale_delta REAL NOT NULL DEFAULT 0,
    ego_delta REAL NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (meeting_id) REFERENCES locker_meetings(id)
);

CREATE TABLE IF NOT EXISTS locker_disciplinary_actions (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    violation_type TEXT NOT NULL,
    action_type TEXT NOT NULL,
    fine_amount INTEGER NOT NULL DEFAULT 0,
    suspension_weeks INTEGER NOT NULL DEFAULT 0,
    justification TEXT NOT NULL,
    proportionality_score REAL NOT NULL,
    perceived_fairness REAL NOT NULL,
    morale_impact REAL NOT NULL,
    atmosphere_impact REAL NOT NULL,
    legal_challenge_probability REAL NOT NULL DEFAULT 0,
    related_incident_id TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS locker_shoot_incidents (
    id TEXT PRIMARY KEY,
    participant_ids_json TEXT NOT NULL DEFAULT '[]',
    participant_names_json TEXT NOT NULL DEFAULT '[]',
    trigger_context TEXT NOT NULL,
    severity REAL NOT NULL,
    witness_count INTEGER NOT NULL DEFAULT 0,
    captured_on_recording INTEGER NOT NULL DEFAULT 0,
    immediate_response TEXT,
    public_response TEXT,
    personnel_response TEXT,
    crisis_management_score REAL NOT NULL DEFAULT 0,
    credibility_impact REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'urgent',
    payload_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_performance_centers (
    id TEXT PRIMARY KEY,
    center_name TEXT NOT NULL,
    brand TEXT NOT NULL DEFAULT 'ROC Vanguard',
    facility_level INTEGER NOT NULL DEFAULT 1,
    capacity INTEGER NOT NULL DEFAULT 12,
    trainee_count INTEGER NOT NULL DEFAULT 0,
    weekly_operational_cost INTEGER NOT NULL DEFAULT 0,
    training_quality_modifier REAL NOT NULL DEFAULT 0,
    medical_quality REAL NOT NULL DEFAULT 50,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_trainers (
    id TEXT PRIMARY KEY,
    trainer_name TEXT NOT NULL,
    background TEXT NOT NULL DEFAULT 'wrestling_veteran',
    coaching_skill REAL NOT NULL DEFAULT 60,
    specialization TEXT NOT NULL,
    preferred_methods_json TEXT NOT NULL DEFAULT '{}',
    reputation REAL NOT NULL DEFAULT 50,
    professionalism REAL NOT NULL DEFAULT 70,
    salary INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    performance_metrics_json TEXT NOT NULL DEFAULT '{}',
    relationship_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_curricula (
    id TEXT PRIMARY KEY,
    curriculum_name TEXT NOT NULL,
    template_type TEXT NOT NULL DEFAULT 'custom',
    allocation_json TEXT NOT NULL DEFAULT '{}',
    intensity REAL NOT NULL DEFAULT 1,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_trainees (
    wrestler_id TEXT PRIMARY KEY,
    wrestler_name TEXT NOT NULL,
    center_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    developmental_overness REAL NOT NULL DEFAULT 20,
    readiness_score REAL NOT NULL DEFAULT 0,
    readiness_breakdown_json TEXT NOT NULL DEFAULT '{}',
    assigned_trainer_id TEXT,
    curriculum_id TEXT,
    learning_rate REAL NOT NULL DEFAULT 1,
    physical_conditioning REAL NOT NULL DEFAULT 50,
    character_definition REAL NOT NULL DEFAULT 50,
    crowd_response REAL NOT NULL DEFAULT 50,
    initial_attributes_json TEXT NOT NULL DEFAULT '{}',
    current_attributes_json TEXT NOT NULL DEFAULT '{}',
    plateau_weeks INTEGER NOT NULL DEFAULT 0,
    created_year INTEGER NOT NULL,
    created_week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (center_id) REFERENCES dev_performance_centers(id)
);

CREATE TABLE IF NOT EXISTS dev_progress_snapshots (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    readiness_score REAL NOT NULL,
    readiness_breakdown_json TEXT NOT NULL DEFAULT '{}',
    curriculum_effectiveness REAL NOT NULL DEFAULT 0,
    trainer_effectiveness REAL NOT NULL DEFAULT 0,
    facility_modifier REAL NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL DEFAULT 'weekly_progress',
    notes TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dev_progress_wrestler_week
    ON dev_progress_snapshots(wrestler_id, year, week);

CREATE TABLE IF NOT EXISTS dev_tryouts (
    id TEXT PRIMARY KEY,
    location TEXT NOT NULL,
    candidate_count INTEGER NOT NULL,
    scout_trainer_id TEXT,
    duration_days INTEGER NOT NULL DEFAULT 2,
    target_profile TEXT NOT NULL DEFAULT 'general',
    cost INTEGER NOT NULL DEFAULT 0,
    reputation_modifier REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'scheduled',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_tryout_candidates (
    id TEXT PRIMARY KEY,
    tryout_id TEXT NOT NULL,
    candidate_name TEXT NOT NULL,
    background TEXT NOT NULL,
    revealed_attributes_json TEXT NOT NULL DEFAULT '{}',
    potential_ceiling_json TEXT NOT NULL DEFAULT '{}',
    current_assessment REAL NOT NULL DEFAULT 0,
    potential_assessment REAL NOT NULL DEFAULT 0,
    decision_status TEXT NOT NULL DEFAULT 'undecided',
    signed_wrestler_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (tryout_id) REFERENCES dev_tryouts(id)
);

CREATE TABLE IF NOT EXISTS dev_shows (
    id TEXT PRIMARY KEY,
    show_name TEXT NOT NULL,
    center_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    production_quality REAL NOT NULL DEFAULT 50,
    crowd_size INTEGER NOT NULL DEFAULT 0,
    crowd_reaction REAL NOT NULL DEFAULT 50,
    developmental_value REAL NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_show_performances (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    opponent_quality REAL NOT NULL DEFAULT 50,
    performance_score REAL NOT NULL DEFAULT 50,
    crowd_learning_delta REAL NOT NULL DEFAULT 0,
    character_delta REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (show_id) REFERENCES dev_shows(id)
);

CREATE TABLE IF NOT EXISTS dev_callups (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    source_brand TEXT NOT NULL DEFAULT 'ROC Vanguard',
    destination_brand TEXT NOT NULL,
    readiness_score REAL NOT NULL,
    readiness_override INTEGER NOT NULL DEFAULT 0,
    debut_plan TEXT NOT NULL DEFAULT 'announced_promotion',
    mentor_wrestler_id TEXT,
    transition_status TEXT NOT NULL DEFAULT 'first_90_days',
    transition_score REAL NOT NULL DEFAULT 50,
    unreadiness_penalty REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_senddowns (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    source_brand TEXT NOT NULL,
    reason TEXT NOT NULL,
    communicated_via_meeting INTEGER NOT NULL DEFAULT 0,
    morale_impact REAL NOT NULL DEFAULT 0,
    improvement_plan_json TEXT NOT NULL DEFAULT '{}',
    objective_status TEXT NOT NULL DEFAULT 'active',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_training_injuries (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    injury_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    weeks_remaining INTEGER NOT NULL,
    permanent_attribute_risk REAL NOT NULL DEFAULT 0,
    cause_json TEXT NOT NULL DEFAULT '{}',
    treatment_choice TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_excursion_destinations (
    id TEXT PRIMARY KEY,
    destination_name TEXT NOT NULL,
    region TEXT NOT NULL,
    wrestling_style TEXT NOT NULL,
    specialty_json TEXT NOT NULL DEFAULT '{}',
    cultural_challenge REAL NOT NULL DEFAULT 50,
    relationship_status TEXT NOT NULL DEFAULT 'available',
    weekly_cost INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dev_excursions (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    destination_id TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    planned_duration_weeks INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    adaptation_score REAL NOT NULL DEFAULT 50,
    development_bonus_json TEXT NOT NULL DEFAULT '{}',
    progress_reports_json TEXT NOT NULL DEFAULT '[]',
    return_plan TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (destination_id) REFERENCES dev_excursion_destinations(id)
);

CREATE TABLE IF NOT EXISTS dev_veteran_trainer_transitions (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    transition_reason TEXT NOT NULL,
    coaching_potential_json TEXT NOT NULL DEFAULT '{}',
    legend_factor REAL NOT NULL DEFAULT 0,
    compensation INTEGER NOT NULL DEFAULT 0,
    bridge_influence REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'offered',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS advanced_match_scripts (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    feud_id TEXT,
    script_quality REAL NOT NULL DEFAULT 50,
    intended_reaction TEXT NOT NULL DEFAULT 'engagement',
    execution_score REAL,
    crowd_connection_score REAL,
    match_quality_modifier REAL NOT NULL DEFAULT 0,
    feud_heat_delta REAL NOT NULL DEFAULT 0,
    post_show_analysis_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_match_scripts_show_match
    ON advanced_match_scripts(show_id, match_id);

CREATE TABLE IF NOT EXISTS advanced_match_script_beats (
    id TEXT PRIMARY KEY,
    script_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    sequence_order INTEGER NOT NULL,
    description TEXT NOT NULL,
    required_skill TEXT NOT NULL DEFAULT 'psychology',
    difficulty REAL NOT NULL DEFAULT 50,
    intended_reaction TEXT NOT NULL DEFAULT 'engagement',
    execution_score REAL,
    crowd_response_score REAL,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (script_id) REFERENCES advanced_match_scripts(id)
);

CREATE TABLE IF NOT EXISTS production_profiles (
    id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    camera_direction_quality REAL NOT NULL DEFAULT 60,
    audio_mixing_quality REAL NOT NULL DEFAULT 60,
    production_budget INTEGER NOT NULL DEFAULT 0,
    crew_experience REAL NOT NULL DEFAULT 60,
    presentation_consistency REAL NOT NULL DEFAULT 60,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS commentary_teams (
    id TEXT PRIMARY KEY,
    team_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    play_by_play_accuracy REAL NOT NULL DEFAULT 60,
    color_insight REAL NOT NULL DEFAULT 60,
    chemistry REAL NOT NULL DEFAULT 60,
    storyline_knowledge REAL NOT NULL DEFAULT 60,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS production_quality_history (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    brand TEXT NOT NULL,
    camera_score REAL NOT NULL,
    commentary_score REAL NOT NULL,
    audio_score REAL NOT NULL,
    broadcast_score REAL NOT NULL,
    network_relationship_delta REAL NOT NULL DEFAULT 0,
    inputs_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS dynasty_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    significance REAL NOT NULL DEFAULT 50,
    subject_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS second_generation_prospects (
    id TEXT PRIMARY KEY,
    parent_wrestler_id TEXT NOT NULL,
    parent_wrestler_name TEXT NOT NULL,
    prospect_name TEXT NOT NULL,
    emergence_year INTEGER NOT NULL,
    emergence_week INTEGER NOT NULL,
    inherited_traits_json TEXT NOT NULL DEFAULT '{}',
    narrative_weight REAL NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'eligible_tryout',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS aging_snapshots (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    style_profile TEXT NOT NULL,
    physical_delta_json TEXT NOT NULL DEFAULT '{}',
    intangible_delta_json TEXT NOT NULL DEFAULT '{}',
    injury_legacy_modifier REAL NOT NULL DEFAULT 0,
    career_wear_score REAL NOT NULL DEFAULT 0,
    graceful_aging_score REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS industry_eras (
    id TEXT PRIMARY KEY,
    era_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'future',
    start_year INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    end_year INTEGER,
    end_week INTEGER,
    audience_preferences_json TEXT NOT NULL DEFAULT '{}',
    technology_json TEXT NOT NULL DEFAULT '{}',
    booking_expectation_modifier REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS industry_trend_snapshots (
    id TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    active_era_id TEXT,
    audience_taste_json TEXT NOT NULL DEFAULT '{}',
    competitor_pressure REAL NOT NULL DEFAULT 50,
    technology_options_json TEXT NOT NULL DEFAULT '{}',
    cultural_sensitivity REAL NOT NULL DEFAULT 50,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_industry_trend_week
    ON industry_trend_snapshots(year, week);

CREATE TABLE IF NOT EXISTS attendance_markets (
    id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    market_size INTEGER NOT NULL DEFAULT 100000,
    wrestling_enthusiasm REAL NOT NULL DEFAULT 50,
    economic_health REAL NOT NULL DEFAULT 50,
    competition_density REAL NOT NULL DEFAULT 50,
    local_reputation REAL NOT NULL DEFAULT 50,
    weather_risk REAL NOT NULL DEFAULT 10,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id TEXT PRIMARY KEY,
    show_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    show_name TEXT NOT NULL,
    projected_low INTEGER NOT NULL,
    projected_high INTEGER NOT NULL,
    actual_attendance INTEGER,
    ticket_revenue INTEGER NOT NULL DEFAULT 0,
    card_quality REAL NOT NULL DEFAULT 50,
    marketing_spend INTEGER NOT NULL DEFAULT 0,
    special_event_status TEXT NOT NULL DEFAULT 'standard',
    factors_json TEXT NOT NULL DEFAULT '{}',
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (market_id) REFERENCES attendance_markets(id)
);

CREATE TABLE IF NOT EXISTS brand_entities (
    id TEXT PRIMARY KEY,
    brand_name TEXT NOT NULL UNIQUE,
    creative_identity TEXT NOT NULL DEFAULT 'balanced',
    audience_target TEXT NOT NULL DEFAULT 'general',
    budget_allocation INTEGER NOT NULL DEFAULT 0,
    atmosphere_score REAL NOT NULL DEFAULT 50,
    ratings_performance REAL NOT NULL DEFAULT 50,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS brand_assignment_history (
    id TEXT PRIMARY KEY,
    wrestler_id TEXT NOT NULL,
    wrestler_name TEXT NOT NULL,
    from_brand TEXT,
    to_brand TEXT NOT NULL,
    transfer_reason TEXT NOT NULL,
    on_screen_justification TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS brand_drafts (
    id TEXT PRIMARY KEY,
    draft_name TEXT NOT NULL,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    rules_json TEXT NOT NULL DEFAULT '{}',
    selections_json TEXT NOT NULL DEFAULT '[]',
    media_engagement_boost REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS endgame_objectives (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    objective_name TEXT NOT NULL,
    target_metric TEXT NOT NULL,
    target_value REAL NOT NULL,
    current_value REAL NOT NULL DEFAULT 0,
    progress_pct REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    achieved_year INTEGER,
    achieved_week INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS endgame_recognition_events (
    id TEXT PRIMARY KEY,
    objective_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    legacy_score_delta REAL NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (objective_id) REFERENCES endgame_objectives(id)
);

CREATE TABLE IF NOT EXISTS dynamic_event_feature_audit (
    id TEXT PRIMARY KEY,
    feature_key TEXT NOT NULL UNIQUE,
    feature_name TEXT NOT NULL,
    overlap_status TEXT NOT NULL,
    existing_systems_json TEXT NOT NULL DEFAULT '[]',
    implemented_in_dynamic_events INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dynamic_event_records (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    severity_level TEXT NOT NULL,
    severity_score REAL NOT NULL DEFAULT 50,
    urgency TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'open',
    brand TEXT,
    show_id TEXT,
    show_name TEXT,
    primary_wrestler_id TEXT,
    primary_wrestler_name TEXT,
    secondary_wrestler_id TEXT,
    secondary_wrestler_name TEXT,
    source_system TEXT NOT NULL DEFAULT 'dynamic_events',
    trigger_conditions_json TEXT NOT NULL DEFAULT '{}',
    payload_json TEXT NOT NULL DEFAULT '{}',
    response_options_json TEXT NOT NULL DEFAULT '[]',
    mechanical_effects_json TEXT NOT NULL DEFAULT '{}',
    selected_response TEXT,
    resolution_summary TEXT,
    year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_dynamic_events_week_status
    ON dynamic_event_records(year DESC, week DESC, status);
CREATE INDEX IF NOT EXISTS idx_dynamic_events_type
    ON dynamic_event_records(event_type, year DESC, week DESC);
CREATE INDEX IF NOT EXISTS idx_dynamic_events_wrestler
    ON dynamic_event_records(primary_wrestler_id, secondary_wrestler_id, status);

CREATE TABLE IF NOT EXISTS dynamic_event_impacts (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    target_name TEXT,
    impact_type TEXT NOT NULL,
    value_delta REAL NOT NULL DEFAULT 0,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES dynamic_event_records(id)
);
CREATE INDEX IF NOT EXISTS idx_dynamic_event_impacts_event
    ON dynamic_event_impacts(event_id);
"""


DOWN_SQL = """
DROP TABLE IF EXISTS dynamic_event_impacts;
DROP TABLE IF EXISTS dynamic_event_records;
DROP TABLE IF EXISTS dynamic_event_feature_audit;
DROP TABLE IF EXISTS endgame_recognition_events;
DROP TABLE IF EXISTS endgame_objectives;
DROP TABLE IF EXISTS brand_drafts;
DROP TABLE IF EXISTS brand_assignment_history;
DROP TABLE IF EXISTS brand_entities;
DROP TABLE IF EXISTS attendance_records;
DROP TABLE IF EXISTS attendance_markets;
DROP TABLE IF EXISTS industry_trend_snapshots;
DROP TABLE IF EXISTS industry_eras;
DROP TABLE IF EXISTS aging_snapshots;
DROP TABLE IF EXISTS second_generation_prospects;
DROP TABLE IF EXISTS dynasty_events;
DROP TABLE IF EXISTS production_quality_history;
DROP TABLE IF EXISTS commentary_teams;
DROP TABLE IF EXISTS production_profiles;
DROP TABLE IF EXISTS advanced_match_script_beats;
DROP TABLE IF EXISTS advanced_match_scripts;
DROP TABLE IF EXISTS dev_veteran_trainer_transitions;
DROP TABLE IF EXISTS dev_excursions;
DROP TABLE IF EXISTS dev_excursion_destinations;
DROP TABLE IF EXISTS dev_training_injuries;
DROP TABLE IF EXISTS dev_senddowns;
DROP TABLE IF EXISTS dev_callups;
DROP TABLE IF EXISTS dev_show_performances;
DROP TABLE IF EXISTS dev_shows;
DROP TABLE IF EXISTS dev_tryout_candidates;
DROP TABLE IF EXISTS dev_tryouts;
DROP TABLE IF EXISTS dev_progress_snapshots;
DROP TABLE IF EXISTS dev_trainees;
DROP TABLE IF EXISTS dev_curricula;
DROP TABLE IF EXISTS dev_trainers;
DROP TABLE IF EXISTS dev_performance_centers;
DROP TABLE IF EXISTS locker_shoot_incidents;
DROP TABLE IF EXISTS locker_disciplinary_actions;
DROP TABLE IF EXISTS locker_meeting_attendees;
DROP TABLE IF EXISTS locker_meetings;
DROP TABLE IF EXISTS locker_substance_issues;
DROP TABLE IF EXISTS locker_bullying_incidents;
DROP TABLE IF EXISTS locker_clique_members;
DROP TABLE IF EXISTS locker_cliques;
DROP TABLE IF EXISTS locker_backstage_influence_history;
DROP TABLE IF EXISTS locker_creative_disagreements;
DROP TABLE IF EXISTS locker_atmosphere_snapshots;
DROP TABLE IF EXISTS locker_morale_history;
DROP TABLE IF EXISTS locker_wrestler_state;
DROP TABLE IF EXISTS simulation_expansion_jobs;
DELETE FROM schema_migrations WHERE migration_id = '20260506_149_182_243_250_simulation_expansion';
"""


def create_simulation_expansion_tables(database) -> None:
    """Apply the locker room, developmental, and advanced simulation schema."""

    cursor = database.conn.cursor()
    cursor.executescript(UP_SQL)
    _seed_defaults(cursor)
    cursor.execute(
        "INSERT OR REPLACE INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
        (MIGRATION_ID, datetime.now().isoformat()),
    )
    database.conn.commit()


def drop_simulation_expansion_tables(database) -> None:
    """Rollback helper for development and tests."""

    database.conn.executescript(DOWN_SQL)
    database.conn.commit()


def _seed_defaults(cursor) -> None:
    now = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT OR IGNORE INTO dev_performance_centers (
            id, center_name, brand, facility_level, capacity,
            weekly_operational_cost, training_quality_modifier,
            medical_quality, updated_at
        ) VALUES ('pc_roc_vanguard', 'ROC Vanguard Performance Center',
            'ROC Vanguard', 5, 24, 45000, 0.08, 65, ?)
        """,
        (now,),
    )
    destinations = [
        (
            "exc_japan_strong_style",
            "Kanto Strong Style Dojo",
            "Japan",
            "strong_style",
            '{"technical": 1.25, "psychology": 1.20, "stamina": 1.15}',
            72,
            7000,
        ),
        (
            "exc_mexico_lucha",
            "Consejo Lucha Academy",
            "Mexico",
            "lucha_libre",
            '{"speed": 1.30, "character": 1.10, "crowd_response": 1.20}',
            65,
            5500,
        ),
        (
            "exc_europe_catch",
            "European Catch Circuit",
            "Europe",
            "catch_wrestling",
            '{"technical": 1.30, "brawling": 1.05, "psychology": 1.15}',
            55,
            5200,
        ),
        (
            "exc_hardcore_regional",
            "Frontier Brawling Circuit",
            "North America",
            "hardcore_brawling",
            '{"brawling": 1.25, "stamina": 1.10, "resilience": 1.20}',
            45,
            4500,
        ),
        (
            "exc_global_touring",
            "Global Touring Alliance",
            "International",
            "touring",
            '{"crowd_response": 1.25, "mic": 1.10, "adaptability": 1.20}',
            60,
            6500,
        ),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO dev_excursion_destinations (
            id, destination_name, region, wrestling_style, specialty_json,
            cultural_challenge, weekly_cost, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], now, now) for row in destinations],
    )
    brands = [
        ("brand_alpha", "ROC Alpha", "premium_spectacle", "mainstream", 55),
        ("brand_velocity", "ROC Velocity", "workrate_rising_stars", "core_wrestling", 52),
        ("brand_vanguard", "ROC Vanguard", "developmental", "prospect_watchers", 58),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO brand_entities (
            id, brand_name, creative_identity, audience_target,
            atmosphere_score, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(row[0], row[1], row[2], row[3], row[4], now, now) for row in brands],
    )
    markets = [
        ("market_new_york", "New York", "Northeast", 8400000, 82, 70, 85, 65, 20),
        ("market_chicago", "Chicago", "Midwest", 2700000, 78, 63, 70, 62, 24),
        ("market_atlanta", "Atlanta", "Southeast", 500000, 74, 68, 58, 58, 18),
        ("market_dallas", "Dallas", "Southwest", 1300000, 72, 73, 66, 57, 16),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO attendance_markets (
            id, city, region, market_size, wrestling_enthusiasm,
            economic_health, competition_density, local_reputation,
            weather_risk, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], now, now) for row in markets],
    )
    eras = [
        (
            "era_territorial",
            "Territorial Identity Era",
            "active",
            1,
            '{"regional_identity": 1.25, "technical": 1.05, "spectacle": 0.90}',
            '{"broadcast_tv": true, "streaming": false, "social_media": false}',
            0,
        ),
        (
            "era_spectacle",
            "Spectacle Entertainment Era",
            "future",
            5,
            '{"characters": 1.25, "spectacle": 1.25, "technical": 0.95}',
            '{"broadcast_tv": true, "streaming": false, "social_media": true}',
            0.05,
        ),
        (
            "era_digital_workrate",
            "Digital Workrate Era",
            "future",
            10,
            '{"in_ring_quality": 1.25, "digital": 1.25, "shock": 0.85}',
            '{"broadcast_tv": true, "streaming": true, "social_media": true}',
            0.12,
        ),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO industry_eras (
            id, era_name, status, start_year, start_week,
            audience_preferences_json, technology_json,
            booking_expectation_modifier, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """,
        [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], now, now) for row in eras],
    )
    objectives = [
        ("end_dom_ratings", "industry_dominance", "Sustained Ratings Leader", "avg_viewership", 1500000),
        ("end_fin_revenue", "financial", "Eight-Figure Annual Revenue", "annual_revenue", 10000000),
        ("end_legacy_hof", "legacy", "Build Ten Hall of Fame Careers", "hall_of_fame_count", 10),
        ("end_legacy_story", "legacy", "Create Legendary Storyline Heat", "legendary_heat_count", 5),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO endgame_objectives (
            id, category, objective_name, target_metric, target_value,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(row[0], row[1], row[2], row[3], row[4], now, now) for row in objectives],
    )

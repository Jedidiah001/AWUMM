"""
Legacy expansion persistence (Steps 126-212 broad foundation).

This module provides schema-first support for:
- TV/media, marketing, staff/personnel
- Venue strategy extensions
- Industry competition ecosystem
- ROC Evolve development/training
- Historical & legacy archives
"""

from __future__ import annotations


def create_legacy_expansion_tables(database) -> None:
    cursor = database.conn.cursor()

    cursor.executescript(
        """
        -- ------------------------------------------------------------------
        -- 126-137: TV / MEDIA
        -- ------------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS tv_ratings_weekly (
            rating_id TEXT PRIMARY KEY,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            household_rating REAL DEFAULT 0.0,
            total_viewers INTEGER DEFAULT 0,
            demo_breakdown_json TEXT NOT NULL DEFAULT '{}',
            ad_revenue INTEGER DEFAULT 0,
            network_confidence REAL DEFAULT 50.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tv_ratings_quarter_hours (
            quarter_id TEXT PRIMARY KEY,
            rating_id TEXT NOT NULL,
            quarter_index INTEGER NOT NULL,
            segment_ref TEXT DEFAULT '',
            viewers INTEGER DEFAULT 0,
            delta_vs_prev INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (rating_id) REFERENCES tv_ratings_weekly(rating_id)
        );

        CREATE TABLE IF NOT EXISTS network_relationship_log (
            log_id TEXT PRIMARY KEY,
            partner_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            relationship_score REAL DEFAULT 50.0,
            content_demands_json TEXT NOT NULL DEFAULT '[]',
            time_slot TEXT DEFAULT '',
            renewal_status TEXT DEFAULT 'active',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS media_ecosystem_log (
            item_id TEXT PRIMARY KEY,
            item_type TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            title TEXT NOT NULL,
            subject_ref TEXT DEFAULT '',
            impact_score REAL DEFAULT 0.0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- ------------------------------------------------------------------
        -- 183-192: MARKETING / PROMOTION
        -- ------------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS marketing_campaigns (
            campaign_id TEXT PRIMARY KEY,
            campaign_type TEXT NOT NULL,
            name TEXT NOT NULL,
            target_segment TEXT DEFAULT 'general',
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            spend INTEGER DEFAULT 0,
            projected_reach INTEGER DEFAULT 0,
            realized_reach INTEGER DEFAULT 0,
            effectiveness REAL DEFAULT 0.0,
            status TEXT DEFAULT 'planned',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS event_promotion_log (
            promo_id TEXT PRIMARY KEY,
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            promotion_score REAL DEFAULT 0.0,
            hype_drivers_json TEXT NOT NULL DEFAULT '[]',
            nostalgia_hooks_json TEXT NOT NULL DEFAULT '[]',
            controversy_risk REAL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- ------------------------------------------------------------------
        -- 193-202: STAFF / PERSONNEL
        -- ------------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS staff_roles (
            staff_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role_type TEXT NOT NULL,
            specialty TEXT DEFAULT '',
            skill_rating REAL DEFAULT 50.0,
            chemistry_rating REAL DEFAULT 50.0,
            salary INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS talent_relations_log (
            relations_id TEXT PRIMARY KEY,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            concern_type TEXT NOT NULL,
            severity REAL DEFAULT 0.0,
            resolution TEXT DEFAULT '',
            morale_impact REAL DEFAULT 0.0,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- ------------------------------------------------------------------
        -- 138-148: VENUE STRATEGY EXTENSIONS
        -- ------------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS venue_strategy_profiles (
            profile_id TEXT PRIMARY KEY,
            profile_name TEXT NOT NULL,
            min_fill_pct REAL DEFAULT 0.65,
            max_fill_pct REAL DEFAULT 1.10,
            oversell_bonus_factor REAL DEFAULT 1.05,
            undersell_penalty_factor REAL DEFAULT 0.90,
            travel_cost_weight REAL DEFAULT 1.0,
            fatigue_cost_weight REAL DEFAULT 1.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS regional_popularity (
            region_id TEXT PRIMARY KEY,
            region_name TEXT NOT NULL,
            country TEXT DEFAULT '',
            popularity_score REAL DEFAULT 50.0,
            fan_loyalty REAL DEFAULT 50.0,
            growth_rate REAL DEFAULT 0.0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tour_routing_plans (
            route_id TEXT PRIMARY KEY,
            route_name TEXT NOT NULL,
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            total_distance_km REAL DEFAULT 0.0,
            projected_travel_cost INTEGER DEFAULT 0,
            projected_fatigue REAL DEFAULT 0.0,
            market_coverage_score REAL DEFAULT 0.0,
            route_stops_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS venue_relationships (
            venue_id TEXT PRIMARY KEY,
            relationship_score REAL DEFAULT 50.0,
            pricing_tier TEXT DEFAULT 'standard',
            booking_priority REAL DEFAULT 50.0,
            residency_status TEXT DEFAULT 'none',
            exclusivity_notes TEXT DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS venue_external_factors (
            factor_id TEXT PRIMARY KEY,
            show_id TEXT DEFAULT '',
            venue_id TEXT DEFAULT '',
            factor_type TEXT NOT NULL,
            severity REAL DEFAULT 0.0,
            attendance_impact REAL DEFAULT 0.0,
            revenue_impact INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS venue_sellout_streaks (
            streak_id TEXT PRIMARY KEY,
            brand TEXT NOT NULL,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            pressure_score REAL DEFAULT 0.0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- ------------------------------------------------------------------
        -- 161-170: INDUSTRY / COMPETITION
        -- ------------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS industry_promotions (
            promotion_id TEXT PRIMARY KEY,
            promotion_name TEXT NOT NULL,
            home_region TEXT DEFAULT '',
            reputation_score REAL DEFAULT 50.0,
            market_share REAL DEFAULT 0.0,
            active_roster_size INTEGER DEFAULT 0,
            cash_reserve INTEGER DEFAULT 0,
            relationship_with_player REAL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS industry_talent_movement (
            movement_id TEXT PRIMARY KEY,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            from_promotion_id TEXT DEFAULT '',
            to_promotion_id TEXT DEFAULT '',
            movement_type TEXT NOT NULL,
            offer_value INTEGER DEFAULT 0,
            accepted INTEGER DEFAULT 0,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS industry_partnerships (
            partnership_id TEXT PRIMARY KEY,
            promotion_a_id TEXT NOT NULL,
            promotion_b_id TEXT NOT NULL,
            partnership_type TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            talent_exchange_rules_json TEXT NOT NULL DEFAULT '{}',
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            end_year INTEGER,
            end_week INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invasion_storylines (
            invasion_id TEXT PRIMARY KEY,
            show_id TEXT NOT NULL,
            aggressor_promotion_id TEXT NOT NULL,
            defender_promotion_id TEXT NOT NULL,
            status TEXT DEFAULT 'planned',
            heat_score REAL DEFAULT 0.0,
            storyline_notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS industry_sentiment_log (
            sentiment_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            headline TEXT NOT NULL,
            sentiment_score REAL DEFAULT 0.0,
            credibility REAL DEFAULT 50.0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS market_share_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            promotion_id TEXT NOT NULL,
            ratings_share REAL DEFAULT 0.0,
            attendance_share REAL DEFAULT 0.0,
            revenue_share REAL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- ------------------------------------------------------------------
        -- 171-182: DEVELOPMENT / TRAINING (ROC Evolve)
        -- ------------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS evolve_performance_center (
            center_id TEXT PRIMARY KEY,
            brand_name TEXT NOT NULL DEFAULT 'ROC Evolve',
            facility_level INTEGER DEFAULT 1,
            monthly_cost INTEGER DEFAULT 0,
            training_quality REAL DEFAULT 50.0,
            medical_quality REAL DEFAULT 50.0,
            scouting_quality REAL DEFAULT 50.0,
            active_curriculum_id TEXT DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evolve_trainers (
            trainer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            coaching_rating REAL DEFAULT 50.0,
            veteran_status INTEGER DEFAULT 0,
            salary INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evolve_curricula (
            curriculum_id TEXT PRIMARY KEY,
            curriculum_name TEXT NOT NULL,
            focus_json TEXT NOT NULL DEFAULT '{}',
            intensity REAL DEFAULT 1.0,
            injury_risk_modifier REAL DEFAULT 1.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evolve_roster (
            prospect_id TEXT PRIMARY KEY,
            wrestler_id TEXT DEFAULT '',
            wrestler_name TEXT NOT NULL,
            status TEXT DEFAULT 'trainee',
            readiness_score REAL DEFAULT 0.0,
            progression_json TEXT NOT NULL DEFAULT '{}',
            assigned_trainer_id TEXT DEFAULT '',
            contract_notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evolve_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            prospect_id TEXT DEFAULT '',
            wrestler_id TEXT DEFAULT '',
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- ------------------------------------------------------------------
        -- 203-212: HISTORICAL / LEGACY
        -- ------------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS history_matches (
            history_match_id TEXT PRIMARY KEY,
            match_id TEXT DEFAULT '',
            show_id TEXT NOT NULL,
            show_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            participants_json TEXT NOT NULL DEFAULT '[]',
            winner_ids_json TEXT NOT NULL DEFAULT '[]',
            finish_type TEXT DEFAULT 'pinfall',
            duration_minutes INTEGER DEFAULT 0,
            match_rating REAL DEFAULT 0.0,
            significance REAL DEFAULT 0.0,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS history_storylines (
            storyline_id TEXT PRIMARY KEY,
            feud_id TEXT DEFAULT '',
            title TEXT NOT NULL,
            participants_json TEXT NOT NULL DEFAULT '[]',
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            end_year INTEGER,
            end_week INTEGER,
            climax_match_id TEXT DEFAULT '',
            outcome_summary TEXT DEFAULT '',
            continuity_tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS history_championships (
            lineage_id TEXT PRIMARY KEY,
            championship_id TEXT NOT NULL,
            championship_name TEXT NOT NULL,
            champion_id TEXT NOT NULL,
            champion_name TEXT NOT NULL,
            reign_number INTEGER DEFAULT 1,
            reign_start_year INTEGER NOT NULL,
            reign_start_week INTEGER NOT NULL,
            reign_end_year INTEGER,
            reign_end_week INTEGER,
            defenses INTEGER DEFAULT 0,
            memorable_moments_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS hall_of_fame (
            induction_id TEXT PRIMARY KEY,
            wrestler_id TEXT NOT NULL,
            wrestler_name TEXT NOT NULL,
            induction_year INTEGER NOT NULL,
            induction_week INTEGER NOT NULL,
            induction_tier TEXT DEFAULT 'standard',
            speech_notes TEXT DEFAULT '',
            legacy_score REAL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS rivalry_history (
            rivalry_id TEXT PRIMARY KEY,
            wrestler_a_id TEXT NOT NULL,
            wrestler_b_id TEXT NOT NULL,
            total_matches INTEGER DEFAULT 0,
            a_wins INTEGER DEFAULT 0,
            b_wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            intensity_peak REAL DEFAULT 0.0,
            latest_update_year INTEGER DEFAULT 1,
            latest_update_week INTEGER DEFAULT 1,
            timeline_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS history_anniversaries (
            anniversary_id TEXT PRIMARY KEY,
            subject_type TEXT NOT NULL,
            subject_ref TEXT NOT NULL,
            original_date TEXT NOT NULL,
            reminder_window_weeks INTEGER DEFAULT 4,
            callback_suggestions_json TEXT NOT NULL DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS history_records (
            record_id TEXT PRIMARY KEY,
            record_type TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            holder_ref TEXT NOT NULL,
            value_numeric REAL DEFAULT 0.0,
            value_text TEXT DEFAULT '',
            context_json TEXT NOT NULL DEFAULT '{}',
            set_year INTEGER DEFAULT 1,
            set_week INTEGER DEFAULT 1,
            broken_year INTEGER,
            broken_week INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS historical_moments (
            moment_id TEXT PRIMARY KEY,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            show_id TEXT DEFAULT '',
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            significance_level INTEGER DEFAULT 1,
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS named_eras (
            era_id TEXT PRIMARY KEY,
            era_name TEXT NOT NULL,
            start_year INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            end_year INTEGER,
            end_week INTEGER,
            defining_stars_json TEXT NOT NULL DEFAULT '[]',
            style_markers_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wrestler_legacy_stats (
            wrestler_id TEXT PRIMARY KEY,
            wrestler_name TEXT NOT NULL,
            total_matches INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            win_pct REAL DEFAULT 0.0,
            titles_won INTEGER DEFAULT 0,
            title_defenses INTEGER DEFAULT 0,
            hall_of_fame_inducted INTEGER DEFAULT 0,
            accolades_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS world_feed (
            feed_id TEXT PRIMARY KEY,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            source_event_id TEXT,
            headline TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            impact_json TEXT NOT NULL DEFAULT '{}',
            significance INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS world_modifiers (
            modifier_id TEXT PRIMARY KEY,
            effect_key TEXT NOT NULL,
            effect_value REAL NOT NULL DEFAULT 0.0,
            source_feed_id TEXT NOT NULL,
            source_headline TEXT NOT NULL,
            starts_year INTEGER NOT NULL,
            starts_week INTEGER NOT NULL,
            expires_year INTEGER NOT NULL,
            expires_week INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_tv_ratings_year_week ON tv_ratings_weekly(year, week);
        CREATE INDEX IF NOT EXISTS idx_market_share_year_week ON market_share_snapshots(year, week);
        CREATE INDEX IF NOT EXISTS idx_evolve_events_year_week ON evolve_events(year, week);
        CREATE INDEX IF NOT EXISTS idx_history_matches_year_week ON history_matches(year, week);
        CREATE INDEX IF NOT EXISTS idx_history_moments_significance ON historical_moments(significance_level);
        CREATE INDEX IF NOT EXISTS idx_world_feed_created_at ON world_feed(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_world_feed_year_week ON world_feed(year, week);
        CREATE INDEX IF NOT EXISTS idx_world_modifiers_active ON world_modifiers(is_active, expires_year, expires_week);
        """
    )

    database.conn.commit()
    print("✅ Legacy expansion tables created (Steps 126-212 foundation)")
